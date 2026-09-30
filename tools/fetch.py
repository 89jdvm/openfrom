#!/usr/bin/env python3
"""
fetch.py -- run the source fetchers and write .tmp/raw/<source>.jsonl.

Each source runs in its own thread (they are different hosts; each is polite on
its own). A source that fails is logged as down and the others carry on.
.tmp/raw/_status.json records rows and errors per source.

Usage:
    python tools/fetch.py              # every source
    python tools/fetch.py himalayas ats
"""
from __future__ import annotations

import importlib
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import RAW, write_jsonl  # noqa: E402

SOURCES = ["himalayas", "remoteok", "jobicy", "weworkremotely", "rwfa", "arbeitnow", "workingnomads",
           "workable", "ats", "impact_rss"]


def run(name: str) -> dict:
    t0 = time.time()
    try:
        mod = importlib.import_module(f"tools.sources.{name}")
        rows = mod.fetch()
        n = write_jsonl(RAW / f"{name}.jsonl", rows)
        return {"source": name, "rows": n, "seconds": round(time.time() - t0), "error": None}
    except Exception as e:
        traceback.print_exc()
        return {"source": name, "rows": 0, "seconds": round(time.time() - t0), "error": f"{type(e).__name__}: {e}"[:300]}


def main(argv: list[str]) -> int:
    names = argv or SOURCES
    RAW.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        results = list(ex.map(run, names))
    status_path = RAW / "_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in results:
        status[r["source"]] = {**r, "at": now}
        state = "DOWN " + r["error"] if r["error"] else f"{r['rows']} rows"
        print(f"{r['source']:16s} {state}  ({r['seconds']}s)")
    status_path.write_text(json.dumps(status, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
