#!/usr/bin/env python3
"""
check_public_safe.py -- the public-safety guard.

Fails (exit 1) if anything about to become public carries private data or
full ad text. Runs from the pre-commit hook, in CI, before every push and
before every state upload.

Modes
  (default)          every tracked and staged file in the git index
  --paths F [F...]   only these files (e.g. files about to be uploaded)
  --history          every file in every commit, plus commit author emails
  --upload           with --paths: a state upload (the 5 MB commit limit does not apply)

Rules
  - JSON / JSONL / CSV / XML: no string longer than 400 characters, and no
    private field names used as keys.
  - Any file: no email address except the public contact address.
  - Code and docs: none of the private words below.
  - Any file: not the owner's phone number (read at run time from a private
    file next door; skipped when that file is absent, as in CI).
  - No committed file over 5 MB, no .env file.

The private words are stored rot13-encoded so this file does not itself
contain them.
"""
from __future__ import annotations

import argparse
import codecs
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_EMAIL = "naksnack.world@gmail.com"
MAX_STR = 400
MAX_BYTES = 5 * 1024 * 1024

DATA_EXT = {".json", ".jsonl", ".csv", ".xml", ".uids"}
BINARY_EXT = {".bin", ".npz", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
              ".ttf", ".otf", ".pdf", ".docx", ".onnx", ".wasm", ".gz", ".zip"}


def _r(s: str) -> str:
    return codecs.decode(s, "rot13")


# Substrings (case-insensitive) banned in code and docs.
WORDS = [_r(w) for w in ["qrysgwq", "89.wqio@", "p:\\hfref", "pbafhygnag-ynhapu", "wbozngpu",
                         "crefbany wbo-znexrg fghql", "wq_erpbeq", "srnfvo", "artbgvng", "qernz"]]
# Standalone, case-sensitive.
WORD_STANDALONE = re.compile(r"(?<![A-Za-z0-9_])" + _r("WQ") + r"(?![A-Za-z0-9_])")
# Keys banned in data files.
KEYS = {_r(k) for k in ["cnl_2x", "cnl_4x", "rphnqbe_bcra", "bcra_gb_rphnqbe", "sybbe", "ernfbavat"]}

EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PROFILE = ROOT.parent / _r("wbo-frnepu-nhgbzngvba") / "application_profile.yaml"


def _phone_patterns() -> list[re.Pattern]:
    """Owner's phone numbers as separator-tolerant regexes, held in memory only."""
    if not PROFILE.exists():
        return []
    pats = []
    for line in PROFILE.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*phone_(primary|secondary)\s*:\s*\"?([^\"#]+)", line)
        if not m:
            continue
        digits = re.sub(r"\D", "", m.group(2))
        if len(digits) < 7:
            continue
        local = digits[-9:]
        pats.append(re.compile(r"[\s().-]?".join(re.escape(d) for d in local)))
    return pats


def _long_strings(obj, path="$"):
    if isinstance(obj, str):
        if len(obj) > MAX_STR:
            yield f"{path}: string of {len(obj)} chars"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in KEYS:
                yield f"{path}: private key '{k}'"
            yield from _long_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _long_strings(v, f"{path}[{i}]")


def check_blob(name: str, data: bytes, phones: list[re.Pattern], size_limit: bool = True) -> list[str]:
    """Return a list of problems for one file's content."""
    problems = []
    p = Path(name.split("@")[0] if "@" in Path(name).name else name)  # history names are "path@commit"
    ext = p.suffix.lower()
    if p.name == ".env" or p.name.startswith(".env."):
        problems.append(".env file")
    if size_limit and len(data) > MAX_BYTES:
        problems.append(f"file is {len(data) / 1e6:.1f} MB (limit 5 MB)")
    if ext in BINARY_EXT:
        return problems
    text = data.decode("utf-8", errors="replace")

    for m in EMAIL_RX.finditer(text):
        if m.group(0).lower() != PUBLIC_EMAIL:
            problems.append(f"email address '{m.group(0)}'")
    for rx in phones:
        if rx.search(text):
            problems.append("owner's phone number")

    if ext in DATA_EXT:
        if ext == ".json":
            try:
                problems += list(_long_strings(json.loads(text)))
            except ValueError:
                problems.append("invalid JSON")
        elif ext == ".jsonl":
            for i, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    try:
                        problems += [f"line {i} {x}" for x in _long_strings(json.loads(line))]
                    except ValueError:
                        problems.append(f"line {i}: invalid JSON")
        else:  # csv / xml: any run of text between separators
            for i, line in enumerate(text.splitlines(), 1):
                for cell in re.split(r"[,<>]", line):
                    if len(cell) > MAX_STR:
                        problems.append(f"line {i}: value of {len(cell)} chars")
                for k in KEYS:
                    if re.search(rf"(^|[,<\"]){re.escape(k)}([,>\" ]|$)", line):
                        problems.append(f"line {i}: private key '{k}'")
    else:
        low = text.lower()
        for w in WORDS:
            if w in low:
                problems.append(f"private word '{_r(w)}' (rot13)")
        if WORD_STANDALONE.search(text):
            problems.append("private initials (standalone)")
    return problems


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def index_files() -> list[tuple[str, bytes]]:
    names = [n for n in _git("ls-files", "-z", "--cached").decode("utf-8").split("\0") if n]
    out = []
    for n in names:
        try:
            out.append((n, _git("show", f":{n}")))  # staged content
        except subprocess.CalledProcessError:
            pass  # deleted in the index
    return out


def history_files() -> list[tuple[str, bytes]]:
    try:
        revs = _git("rev-list", "--all").decode().split()
    except subprocess.CalledProcessError:
        return []
    seen, out = set(), []
    for rev in revs:
        for line in _git("ls-tree", "-r", rev).decode("utf-8").splitlines():
            meta, name = line.split("\t", 1)
            sha = meta.split()[2]
            if sha not in seen:
                seen.add(sha)
                out.append((f"{name}@{rev[:7]}", _git("cat-file", "-p", sha)))
    return out


ALLOWED_COMMIT_EMAILS = {"noreply" + "@" + "anthropic.com", "noreply" + "@" + "github.com"}


def history_emails() -> list[str]:
    try:
        log = _git("log", "--all", "--format=%ae%n%ce").decode()
    except subprocess.CalledProcessError:
        return []
    bad = []
    for e in set(log.split()):
        if not (e.endswith("@users.noreply.github.com") or e in ALLOWED_COMMIT_EMAILS):
            bad.append(f"commit email '{e}'")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--paths", nargs="+", help="check only these files")
    ap.add_argument("--upload", action="store_true",
                    help="files are a state upload, not a commit: no 5 MB limit (every other rule applies)")
    ap.add_argument("--history", action="store_true", help="check every commit")
    a = ap.parse_args(argv)

    phones = _phone_patterns()
    if a.paths:
        files = []
        for f in a.paths:
            fp = Path(f)
            if fp.is_dir():
                files += [(str(x), x.read_bytes()) for x in fp.rglob("*") if x.is_file()]
            else:
                files.append((f, fp.read_bytes()))
    elif a.history:
        files = history_files() + index_files()
    else:
        files = index_files()

    failed = 0
    for name, data in files:
        for prob in check_blob(name, data, phones, size_limit=not a.upload):
            print(f"FAIL {name}: {prob}")
            failed += 1
    if a.history:
        for prob in history_emails():
            print(f"FAIL {prob}")
            failed += 1
    note = "" if phones else " (phone check skipped: private profile not present)"
    print(f"check_public_safe: {len(files)} files, {failed} problems{note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
