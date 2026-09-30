"""Working Nomads: every job of the last ~30 days from the site's own search index
(robots.txt allows all). Gentle: pages of 500, 3 s apart."""
from __future__ import annotations

from tools.common import make_posting
from tools.geo import countries_in
from tools.pay import pay_from_text
from tools.sources._http import get

NAME = "workingnomads"
CREDIT = ("Working Nomads", "https://www.workingnomads.com")
TERMS = "https://www.workingnomads.com/robots.txt"


def fetch(page_size: int = 500, max_pages: int = 20) -> list[dict]:
    rows, start = [], 0
    for _ in range(max_pages):
        j = get("https://www.workingnomads.com/jobsapi/_search", method="POST", delay=3, timeout=60,
                json={"from": start, "size": page_size, "sort": [{"pub_date": "desc"}]}).json()
        hits = j["hits"]
        total = hits["total"]["value"] if isinstance(hits["total"], dict) else hits["total"]
        for h in hits["hits"]:
            x = h["_source"]
            locs = x.get("locations") or []
            loc = ", ".join(locs) if isinstance(locs, list) else str(locs)
            pay = pay_from_text(x.get("salary_range") or "")
            page = f"https://www.workingnomads.com/jobs/{x.get('slug')}"
            rows.append(make_posting(
                source=NAME, external_id=page, title=x.get("title"), organization=x.get("company"),
                location=loc or "Anywhere", countries=countries_in(loc), remote=True,
                remote_scope="worldwide" if (not loc or "anywhere" in loc.lower()) else None,
                posted=x.get("pub_date"), url=page,
                salary_min=pay[0] if pay else None, salary_max=pay[1] if pay else None,
                salary_currency=pay[2] if pay else None, salary_period=pay[3] if pay else None,
                description=x.get("description"),
                tags=[x.get("category_name") or "", x.get("experience_level") or ""]))
        start += page_size
        if not hits["hits"] or start >= total:
            break
    return rows
