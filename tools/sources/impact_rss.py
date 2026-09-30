"""Impact-sector RSS feeds: NGO Job Board and PCDN (Jobboardly-hosted).
Both publish public RSS; neither's terms restrict reading or linking to it."""
from __future__ import annotations

import re

from tools.common import make_posting
from tools.geo import countries_in
from tools.sources._http import get, rss_items

NAME = "impact_rss"
CREDIT = ("NGO Job Board and PCDN", "")
TERMS = "https://ngojobboard.org/terms-and-conditions/"
_REMOTE = re.compile(r"\bremote\b|home[- ]based|work from home|anywhere|virtual|teletrabajo|remoto", re.I)


def ngojobboard() -> list[dict]:
    items = rss_items(get("https://ngojobboard.org/wpjobboard/xml/rss/?filter=active&type=3", delay=2).text)
    out = []
    for f in items:
        title = re.sub(r"^New opening at .*? — ", "", f.get("title", ""))
        loc = f.get("location", "")
        out.append(make_posting(
            source="ngojobboard", external_id=f.get("guid") or f.get("link"), title=title,
            organization=f.get("company") or f.get("author", ""), location=loc, countries=countries_in(loc),
            remote=True if _REMOTE.search(loc) else None, posted=f.get("pubDate"), url=f.get("link"),
            description=f.get("description", ""), tags=[f.get("category", "")]))
    return out


def pcdn() -> list[dict]:
    items = rss_items(get("https://jobs.pcdn.global/jobs.rss", delay=2, timeout=90).text)
    out = []
    for f in items:
        parts = [p.strip() for p in re.split(r"\s+-\s+", f.get("title", "")) if p.strip()]
        role, org, place = (" - ".join(parts[:-2]), parts[-2], parts[-1]) if len(parts) >= 3 else (
            parts[0] if parts else "", parts[1] if len(parts) > 1 else "", "")
        country = f.get("job:country", "")
        loc = ", ".join(x for x in (place, country) if x and x.lower() not in place.lower() or x == place)
        out.append(make_posting(
            source="pcdn", external_id=f.get("guid") or f.get("link"), title=role, organization=org,
            location=loc, countries=countries_in(f"{place}, {country}"),
            remote=True if _REMOTE.search(f"{role} {place}") else None,
            posted=f.get("pubDate"), url=f.get("link"), description=f.get("description", "")))
    return out


def fetch() -> list[dict]:
    rows = []
    for fn in (ngojobboard, pcdn):
        try:
            rows += fn()
        except Exception as e:
            print(f"  {fn.__name__}: {e}")
    return rows
