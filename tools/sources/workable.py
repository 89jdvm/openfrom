"""Workable's public job board (jobs.workable.com): remote jobs of the last 30 days,
newest first, capped per night. Employers clone one ad per country, so copies are
merged on company + title and their countries joined. robots.txt allows the API."""
from __future__ import annotations

import re

from tools.common import make_posting
from tools.geo import countries_in
from tools.sources._http import get

NAME = "workable_board"
CREDIT = ("Workable", "https://jobs.workable.com")
TERMS = "https://jobs.workable.com/terms"


def _key(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def fetch(max_pages: int = 300) -> list[dict]:
    roles: dict[tuple, dict] = {}
    token = None
    for _ in range(max_pages):
        params = {"workplace": "remote", "day_range": 30}
        if token:
            params["pageToken"] = token
        j = get("https://jobs.workable.com/api/v1/jobs", params=params, delay=1.0).json()
        for x in j.get("jobs") or []:
            company = (x.get("company") or {}).get("title") or ""
            key = (_key(company), _key(x.get("title")))
            r = roles.setdefault(key, {"x": x, "company": company, "places": []})
            loc = x.get("location") or {}
            place = ", ".join(p for p in (loc.get("city"), loc.get("countryName")) if p)
            if place and place not in r["places"]:
                r["places"].append(place)
        token = j.get("nextPageToken")
        if not token or not j.get("jobs"):
            break
    rows = []
    for r in roles.values():
        x = r["x"]
        text = "\n".join(filter(None, [x.get("description"), x.get("requirementsSection"), x.get("benefitsSection")]))
        loc = "; ".join(r["places"][:30])
        cs = []
        for p in r["places"]:
            cs += [c for c in countries_in(p) if c not in cs]
        rows.append(make_posting(
            source=NAME, external_id=x.get("id"), title=x.get("title"), organization=r["company"],
            location=loc or "Remote", countries=cs, remote=True, remote_scope="countries" if cs else None,
            posted=x.get("created"), url=x.get("url"), description=text, tags=[x.get("employmentType") or ""]))
    return rows
