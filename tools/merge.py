#!/usr/bin/env python3
"""
merge.py -- combine tonight's fetch with the jobs already known, and keep the listable ones.

Inputs:  .tmp/raw/*.jsonl (tonight's fetch, with full text)
         .tmp/state/jobs.jsonl (earlier nights, summaries only; may be absent)
Output:  .tmp/jobs.jsonl, one row per listable job:
         remote, posted within 60 days, deadline not passed, deduplicated.
         New rows keep their full text in "description" for the embedding, label and
         skill steps; it is dropped again before anything is published or uploaded.

Duplicates (same organisation + title) keep one copy, preferring the employer's own
board, then impact feeds, then the job boards; the kept copy remembers the others.

Usage:  python tools/merge.py
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import MAX_AGE_DAYS, RAW, STATE, TMP, iter_jsonl, short_summary, write_jsonl  # noqa: E402
from tools.jobtext import ad_window  # noqa: E402
from tools.pay import fx_rates, monthly_usd  # noqa: E402
from tools.who_can_apply import who_can_apply  # noqa: E402

RANK = {"greenhouse": 0, "lever": 0, "ashby": 0, "recruitee": 0, "ngojobboard": 1, "pcdn": 1}
OUT = TMP / "jobs.jsonl"
KEEP = ["uid", "source", "title", "organization", "location", "url", "posted", "deadline", "first_seen",
        "summary", "w", "pay", "also"]


def key(p: dict) -> str:
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()  # noqa: E731
    title = re.sub(r"\((remote|m/f/d|f/m/x|m/w/d|all genders)\)|\b(remote|remoto)\b", "", p.get("title") or "", flags=re.I)
    return f"{norm(p.get('organization'))}|{norm(title)}"


def enrich(p: dict, fx: dict, today: str) -> dict:
    w = who_can_apply(p)
    return {
        **p,
        "first_seen": p.get("first_seen") or today,
        "summary": short_summary(ad_window(p.get("description") or "", 600)),
        "w": {k: w[k] for k in ("scope", "countries", "regions", "utc")},
        "pay": monthly_usd(p, fx),
    }


def listable(p: dict, today: date) -> bool:
    if p["w"]["scope"] == "onsite":
        return False
    if p.get("deadline") and p["deadline"] < today.isoformat():
        return False
    posted = p.get("posted") or p.get("first_seen")
    if posted and posted < (today - timedelta(days=MAX_AGE_DAYS)).isoformat():
        return False
    if posted and posted > (today + timedelta(days=2)).isoformat():
        return False
    return bool(p.get("title") and p.get("url"))


def main() -> int:
    today = date.today()
    fx = fx_rates()
    old = {r["uid"]: r for r in iter_jsonl(STATE / "jobs.jsonl")}
    fresh: dict[str, dict] = {}
    for f in sorted(RAW.glob("*.jsonl")):
        for p in iter_jsonl(f):
            if p["uid"] in old:  # known job: keep its stored labels, refresh nothing but dates
                old[p["uid"]]["deadline"] = p.get("deadline") or old[p["uid"]].get("deadline")
                continue
            fresh[p["uid"]] = enrich(p, fx, today.isoformat())

    rows = list(old.values()) + list(fresh.values())
    best: dict[str, dict] = {}
    for p in rows:
        if not listable(p, today):
            continue
        k = key(p)
        cur = best.get(k)
        if cur is None:
            best[k] = p
            continue
        a, b = (RANK.get(p["source"], 2), p["uid"] in old), (RANK.get(cur["source"], 2), cur["uid"] in old)
        keep, drop = (p, cur) if (a[0], not a[1]) < (b[0], not b[1]) else (cur, p)
        keep.setdefault("also", [])
        if drop["source"] not in keep["also"] and drop["source"] != keep["source"]:
            keep["also"].append(drop["source"])
        best[k] = keep
    out = sorted(best.values(), key=lambda p: (p.get("posted") or p.get("first_seen") or ""), reverse=True)
    n = write_jsonl(OUT, out)
    new = sum(1 for p in out if p["uid"] in fresh)
    scopes: dict[str, int] = {}
    for p in out:
        scopes[p["w"]["scope"]] = scopes.get(p["w"]["scope"], 0) + 1
    print(f"merged: {n} listable jobs ({new} new tonight, {n - new} from earlier nights); {scopes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
