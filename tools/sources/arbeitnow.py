"""Arbeitnow: free job-board API (Europe, mostly Germany). Only remote jobs are kept."""
from __future__ import annotations

from datetime import date, timedelta

from tools.common import MAX_AGE_DAYS, make_posting, to_date
from tools.geo import countries_in
from tools.sources._http import get

NAME = "arbeitnow"
CREDIT = ("Arbeitnow", "https://www.arbeitnow.com")
TERMS = "https://www.arbeitnow.com/blog/job-board-api"


def fetch(max_pages: int = 40) -> list[dict]:
    cutoff = (date.today() - timedelta(days=MAX_AGE_DAYS)).isoformat()
    rows = []
    for page in range(1, max_pages + 1):
        j = get("https://www.arbeitnow.com/api/job-board-api", params={"page": page}, delay=1.5, timeout=90).json()
        data = j.get("data") or []
        for x in data:
            if not x.get("remote"):
                continue
            loc = x.get("location") or ""
            rows.append(make_posting(
                source=NAME, external_id=x.get("slug"), title=x.get("title"), organization=x.get("company_name"),
                location=loc, countries=countries_in(loc) or ["DE"], remote=True, remote_scope="countries",
                posted=x.get("created_at"), url=x.get("url"), description=x.get("description"), tags=x.get("tags")))
        oldest = min((to_date(x.get("created_at")) or "9999" for x in data), default="0")
        if not data or not (j.get("links") or {}).get("next") or oldest < cutoff:
            break
    return rows
