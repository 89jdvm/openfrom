#!/usr/bin/env python3
"""
state.py -- keep the nightly state in a GitHub Release asset.

The state is what one night passes to the next: job summaries with their labels and
skills (never ad text), their vectors, the label model and the employer lookup.
It lives in the release tagged "state" as state.tar.gz, overwritten each night.

    python tools/state.py download   # -> .tmp/state/, .tmp/emb/jobs.{bin,uids}
    python tools/state.py upload     # guard, pack, gh release upload --clobber

Upload runs the public-safety guard over every file first and refuses on failure.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import ROOT, STATE, TMP  # noqa: E402

TAG = "state"
ASSET = TMP / "state.tar.gz"
FILES = {  # name in the archive -> local path
    "jobs.jsonl": STATE / "jobs.jsonl",
    "model.npz": STATE / "model.npz",
    "employers.json": STATE / "employers.json",
    "quality.json": STATE / "quality.json",
    "vectors.bin": TMP / "emb" / "jobs.bin",
    "vectors.uids": TMP / "emb" / "jobs.uids",
}


def gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True, check=check)


def download() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    (TMP / "emb").mkdir(parents=True, exist_ok=True)
    r = gh("release", "download", TAG, "-p", ASSET.name, "-D", str(TMP), "--clobber", check=False)
    if r.returncode != 0:
        print(f"no state yet ({r.stderr.strip()[:120]}); starting empty")
        return 0
    with tarfile.open(ASSET) as t:
        for m in t.getmembers():
            if m.name in FILES and m.isfile():
                dest = FILES[m.name]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile(m) as src, dest.open("wb") as out:
                    shutil.copyfileobj(src, out)
    print("state restored: " + ", ".join(n for n, p in FILES.items() if p.exists()))
    return 0


def upload() -> int:
    present = {n: p for n, p in FILES.items() if p.exists()}
    guard = subprocess.run([sys.executable, str(ROOT / "tools" / "check_public_safe.py"), "--upload",
                            "--paths", *[str(p) for p in present.values()]], cwd=ROOT)
    if guard.returncode != 0:
        print("state upload refused: the public-safety guard failed")
        return 1
    with tarfile.open(ASSET, "w:gz") as t:
        for n, p in present.items():
            t.add(p, arcname=n)
    if gh("release", "view", TAG, check=False).returncode != 0:
        gh("release", "create", TAG, "--title", "Nightly state",
           "--notes", "Job summaries, labels and vectors passed from one nightly build to the next. No ad text.",
           "--latest=false")
    gh("release", "upload", TAG, str(ASSET), "--clobber")
    print(f"state uploaded: {ASSET.stat().st_size / 1e6:.1f} MB ({', '.join(present)})")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(download() if cmd == "download" else upload() if cmd == "upload" else print(__doc__) or 2)
