#!/usr/bin/env python3
"""prep_embed.py -- write .tmp/emb/jobs_in.jsonl: the passage text of every listed job
that has no vector yet, for embed.mjs. Also drops vectors of jobs no longer listed.

Usage:  python tools/prep_embed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import TMP, iter_jsonl, write_jsonl  # noqa: E402
from tools.jobtext import passage  # noqa: E402
from tools.vectors import load_raw, save_raw  # noqa: E402

PREFIX = TMP / "emb" / "jobs"


def main() -> int:
    jobs = list(iter_jsonl(TMP / "jobs.jsonl"))
    want = {p["uid"] for p in jobs}
    have: set[str] = set()
    if Path(f"{PREFIX}.uids").exists():
        uids, rows = load_raw(PREFIX)
        keep = [i for i, u in enumerate(uids) if u in want]
        save_raw(PREFIX, [uids[i] for i in keep], rows[keep] if keep else np.zeros((0, rows.shape[1]), np.uint8))
        have = {uids[i] for i in keep}
    todo = [{"uid": p["uid"], "text": passage(p["title"], p.get("organization", ""), p.get("description", ""))}
            for p in jobs if p["uid"] not in have]
    write_jsonl(TMP / "emb" / "jobs_in.jsonl", todo)
    print(f"vectors kept: {len(have)}; to embed: {len(todo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
