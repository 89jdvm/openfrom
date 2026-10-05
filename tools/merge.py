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
from tools.common import MAX_AGE_DAYS, RAW, STATE, TMP, iter_jsonl, scrub_emails, short_summary, write_jsonl  # noqa: E402
from tools.jobtext import ad_window  # noqa: E402
from tools.pay import fx_rates, monthly_usd  # noqa: E402
from tools.who_can_apply import RULES, who_can_apply  # noqa: E402

RANK = {"greenhouse": 0, "lever": 0, "ashby": 0, "recruitee": 0, "ngojobboard": 1, "pcdn": 1}
OUT = TMP / "jobs.jsonl"
KEEP = ["uid", "source", "title", "organization", "location", "url", "posted", "deadline", "first_seen",
        "summary", "w", "wv", "pay", "also"]


EMAIL_IN_URL = re.compile(r"[A-Za-z0-9._%+-]+(@|%40)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_GENERIC = {"the", "global", "international", "group", "world", "united", "new", "first", "open", "remote"}


def key(p: dict) -> str:
    """Organisation + title. The organisation is cut to its first distinctive word, so
    "Planet" and "Planet Labs" posting the same title count as one job."""
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()  # noqa: E731
    title = re.sub(r"\((remote|m/f/d|f/m/x|m/w/d|all genders)\)|\b(remote|remoto)\b", "", p.get("title") or "", flags=re.I)
    words = norm(p.get("organization")).split()
    org = words[0] if words and len(words[0]) >= 4 and words[0] not in _GENERIC else " ".join(words)
    return f"{org}|{norm(title)}"


def who(p: dict) -> dict:
    w = who_can_apply(p)
    return {k: w[k] for k in ("scope", "countries", "regions", "utc")}


def enrich(p: dict, fx: dict, today: str) -> dict:
    return {
        **p,
        "first_seen": p.get("first_seen") or today,
        # List items and lines end with ". " so bullets never run into each other in the summary.
        "summary": short_summary(ad_window(re.sub(r"(?<![.!?:;,])[ \t]*\n+\s*", ". ", p.get("description") or ""), 600)),
        "w": who(p),
        "wv": RULES,
        "pay": monthly_usd(p, fx),
    }


def refresh(known: dict, p: dict) -> None:
    """A saved job seen again keeps its labels. Its deadline is refreshed, and so is who can apply
    when the stored answer came from an older version of the rules."""
    known["deadline"] = p.get("deadline") or known.get("deadline")
    if known.get("wv") != RULES:
        known["w"], known["wv"] = who(p), RULES


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
    # A link a person can open: never a mailto or a link carrying an address, which would publish it.
    url = p.get("url") or ""
    return bool(p.get("title") and re.match(r"https?://", url, re.I) and not EMAIL_IN_URL.search(url))


def dedupe(rows: list[dict], old: set[str], today: date) -> list[dict]:
    """Listable rows, one per organisation + title, newest first. The employer's own board
    wins over impact feeds, which win over job boards; ties keep the row seen earlier."""
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
        keep["also"] = keep.get("also") or []  # rows from the state carry None
        if drop["source"] not in keep["also"] and drop["source"] != keep["source"]:
            keep["also"].append(drop["source"])
        best[k] = keep
    return sorted(best.values(), key=lambda p: (p.get("posted") or p.get("first_seen") or ""), reverse=True)


def main() -> int:
    today = date.today()
    fx = fx_rates()
    old = {r["uid"]: r for r in iter_jsonl(STATE / "jobs.jsonl")}
    fresh: dict[str, dict] = {}
    for f in sorted(RAW.glob("*.jsonl")):
        for p in iter_jsonl(f):
            if p["uid"] in old:
                refresh(old[p["uid"]], p)
                continue
            fresh[p["uid"]] = enrich(p, fx, today.isoformat())

    out = [scrub_emails(p) for p in dedupe(list(old.values()) + list(fresh.values()), set(old), today)]
    n = write_jsonl(OUT, out)
    new = sum(1 for p in out if p["uid"] in fresh)
    scopes: dict[str, int] = {}
    for p in out:
        scopes[p["w"]["scope"]] = scopes.get(p["w"]["scope"], 0) + 1
    print(f"merged: {n} listable jobs ({new} new tonight, {n - new} from earlier nights); {scopes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
