#!/usr/bin/env python3
"""
skills_vocab.py -- the skill list, and which skills each job asks for.

tools/skills_vocab.json holds concrete skills (tools, methods, standards, languages)
with English and Spanish patterns. With --mine, each skill is counted in the seed's
requirement lists and full ad text; skills named too rarely in both are dropped, and the kept
list is written to tools/skills_kept.json (ids and counts only).

Default: tag every job in .tmp/jobs.jsonl that has no skills yet, from its ad text
(requirements first when the ad has such a section), into .tmp/skills.jsonl.

Usage:  python tools/skills_vocab.py [--mine]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import SEED, TMP, iter_jsonl, write_jsonl  # noqa: E402

HERE = Path(__file__).resolve().parent
VOCAB = HERE / "skills_vocab.json"
KEPT = HERE / "skills_kept.json"
MIN_SEED = 10   # times named in the seed's requirement lists, or
MIN_ADS = 30    # times named in the seed's full ad text


def compiled(only: set[str] | None = None) -> list[tuple[str, re.Pattern]]:
    out = []
    for s in json.loads(VOCAB.read_text(encoding="utf-8")):
        if only is None or s["id"] in only:
            flags = 0 if s["id"] == "r" else re.I  # a capital R only
            out.append((s["id"], re.compile(s["rx"], flags)))
    return out


def kept_ids() -> set[str] | None:
    if not KEPT.exists():
        return None
    return {k for k in json.loads(KEPT.read_text(encoding="utf-8"))}


def mine() -> int:
    counts = {sid: 0 for sid, _ in compiled()}
    rx = compiled()
    for r in iter_jsonl(SEED / "req.jsonl"):
        text = "\n".join(r["items"])
        for sid, p in rx:
            if p.search(text):
                counts[sid] += 1
    ads = {sid: 0 for sid, _ in rx}
    for d in iter_jsonl(SEED / "desc.jsonl"):
        for sid, p in rx:
            if p.search(d["text"]):
                ads[sid] += 1
    kept = {k: {"req": counts[k], "ads": ads[k]} for k in sorted(counts, key=lambda k: -ads[k])
            if counts[k] >= MIN_SEED or ads[k] >= MIN_ADS}
    KEPT.write_text(json.dumps(kept, indent=0), encoding="utf-8")
    dropped = [k for k in counts if k not in kept]
    print(f"kept {len(kept)} skills; dropped {dropped}")
    return 0


def tag(text: str, rx: list[tuple[str, re.Pattern]]) -> list[str]:
    return [sid for sid, p in rx if p.search(text or "")]


def main() -> int:
    rx = compiled(kept_ids())
    out = [{"uid": p["uid"], "skills": tag(f"{p['title']}\n{p.get('description') or ''}", rx)}
           for p in iter_jsonl(TMP / "jobs.jsonl") if p.get("skills") is None and p.get("description")]
    write_jsonl(TMP / "skills.jsonl", out)
    print(f"tagged {len(out)} jobs with skills")
    return 0


if __name__ == "__main__":
    sys.exit(mine() if "--mine" in sys.argv else main())
