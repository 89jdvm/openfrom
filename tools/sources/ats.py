"""Employers' own public job boards on Greenhouse, Lever, Ashby and Recruitee.

These APIs exist so companies can show their openings anywhere; no key is needed
for reading. The boards come from ats_boards.csv (written by find_ats_boards.py).
Every open role is fetched; merge keeps the remote ones."""
from __future__ import annotations

import csv
import html
from pathlib import Path

from tools.common import make_posting
from tools.geo import countries_in
from tools.sources._http import get

NAME = "ats"
CREDIT = ("Employers' own career pages", "")
TERMS = "https://docs.greenhouse.io/job-board.html"
BOARDS = Path(__file__).resolve().parent / "ats_boards.csv"


def _remote(loc: str, flag=None, workplace: str | None = None):
    t = (loc or "").lower()
    if flag is True or (workplace or "").lower() == "remote":
        return True
    if "remote" in t or "home-based" in t or "home based" in t or "anywhere" in t:
        return True
    return False if (flag is False or workplace) else None


def greenhouse(name: str, slug: str) -> list[dict]:
    j = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", params={"content": "true"}, delay=1).json()
    out = []
    for x in j.get("jobs") or []:
        loc = (x.get("location") or {}).get("name") or ""
        offices = ", ".join(o.get("name", "") for o in x.get("offices") or [])
        out.append(make_posting(
            source="greenhouse", external_id=f"{slug}:{x.get('id')}", title=x.get("title"), organization=name,
            location=loc, countries=countries_in(f"{loc}, {offices}"), remote=_remote(loc),
            posted=x.get("first_published") or x.get("updated_at"), url=x.get("absolute_url"),
            description=html.unescape(x.get("content") or "")))
    return out


def lever(name: str, slug: str) -> list[dict]:
    j = get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"}, delay=1).json()
    out = []
    for x in j if isinstance(j, list) else []:
        cat = x.get("categories") or {}
        loc = cat.get("location") or ", ".join(cat.get("allLocations") or [])
        wt = x.get("workplaceType")
        sr = x.get("salaryRange") or {}
        out.append(make_posting(
            source="lever", external_id=f"{slug}:{x.get('id')}", title=x.get("text"), organization=name,
            location=loc, countries=countries_in(loc) or ([x["country"]] if x.get("country") else []),
            remote=_remote(loc, None, wt if wt in ("remote", "onsite", "hybrid") else None),
            posted=x.get("createdAt"), url=x.get("hostedUrl"),
            salary_min=sr.get("min"), salary_max=sr.get("max"), salary_currency=sr.get("currency"),
            salary_period={"per-year-salary": "year", "per-month-salary": "month",
                           "per-hour-wage": "hour"}.get(sr.get("interval") or ""),
            description=(x.get("descriptionPlain") or "") + "\n" + (x.get("additionalPlain") or "")))
    return out


def ashby(name: str, slug: str) -> list[dict]:
    j = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", params={"includeCompensation": "true"},
            delay=1).json()
    out = []
    for x in j.get("jobs") or []:
        locs = [x.get("location") or ""] + [a.get("location", "") for a in x.get("secondaryLocations") or []]
        loc = ", ".join(l for l in locs if l)
        addr = ((x.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or ""
        out.append(make_posting(
            source="ashby", external_id=f"{slug}:{x.get('id')}", title=x.get("title"), organization=name,
            location=loc, countries=countries_in(f"{loc}, {addr}"),
            remote=_remote(loc, x.get("isRemote"), x.get("workplaceType")),
            posted=x.get("publishedAt"), url=x.get("jobUrl"),
            description=x.get("descriptionPlain") or x.get("descriptionHtml") or ""))
    return out


def recruitee(name: str, slug: str) -> list[dict]:
    j = get(f"https://{slug}.recruitee.com/api/offers/", delay=1).json()
    out = []
    for x in j.get("offers") or []:
        loc = x.get("location") or ", ".join(filter(None, [x.get("city"), x.get("country")]))
        out.append(make_posting(
            source="recruitee", external_id=f"{slug}:{x.get('id')}", title=x.get("title"), organization=name,
            location=loc, countries=countries_in(f"{loc}, {x.get('country') or ''}"),
            remote=_remote(loc, x.get("remote")), posted=x.get("published_at") or x.get("created_at"),
            url=x.get("careers_url"),
            description=(x.get("description") or "") + "\n" + (x.get("requirements") or "")))
    return out


FETCH = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "recruitee": recruitee}


def fetch() -> list[dict]:
    rows = []
    if not BOARDS.exists():
        return rows
    for b in csv.DictReader(BOARDS.open(encoding="utf-8")):
        try:
            rows += FETCH[b["ats"]](b["name"], b["slug"])
        except Exception as e:
            print(f"  {b['ats']}/{b['slug']}: {e}")
    return rows
