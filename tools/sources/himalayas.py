"""Himalayas: the main remote-jobs feed, newest first, cursor pages of 20.
Terms: link back to the Himalayas job page and name Himalayas as the source."""
from __future__ import annotations

from datetime import date, timedelta

from tools.common import MAX_AGE_DAYS, make_posting, to_date
from tools.geo import countries_in
from tools.sources._http import get

NAME = "himalayas"
CREDIT = ("Himalayas", "https://himalayas.app")
TERMS = "https://himalayas.app/api"


def row(x: dict) -> dict:
    lr = x.get("locationRestrictions") or []
    isos = []
    for c in lr:
        isos += [i for i in countries_in(c, iso_tokens=True)[:1] if i not in isos]
    return make_posting(
        source=NAME, external_id=x.get("guid"), title=x.get("title"), organization=x.get("companyName"),
        location=", ".join(lr) if lr else "Worldwide", countries=isos, remote=True,
        remote_scope="countries" if lr else "worldwide", posted=x.get("pubDate"),
        deadline=x.get("expiryDate"), url=x.get("guid") or x.get("applicationLink"),
        salary_min=x.get("minSalary"), salary_max=x.get("maxSalary"),
        salary_currency=x.get("currency"), salary_period=x.get("salaryPeriod"),
        description=x.get("description"),
        tags=(x.get("categories") or []) + (x.get("parentCategories") or []) + [x.get("seniority") or ""])


def fetch(max_pages: int = 600) -> list[dict]:
    cutoff = (date.today() - timedelta(days=MAX_AGE_DAYS)).isoformat()
    rows, cursor = [], None
    for page in range(max_pages):
        params = {"limit": 20}
        if cursor:
            params["cursor"] = cursor
        j = get("https://himalayas.app/jobs/api", params=params, delay=0.4).json()
        jobs = j.get("jobs") or []
        rows.extend(row(x) for x in jobs)
        cursor = j.get("nextCursor")
        oldest = min((to_date(x.get("pubDate")) or "9999" for x in jobs), default="0")
        if page % 100 == 0:
            print(f"  himalayas page {page}: {len(rows)} rows, oldest {oldest}", flush=True)
        if not jobs or not cursor or oldest < cutoff:
            break
    return rows
