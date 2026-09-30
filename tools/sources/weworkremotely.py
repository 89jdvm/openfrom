"""We Work Remotely: RSS feeds. Terms: anyone can use the feed, as long as the
links are attributed back to We Work Remotely."""
from __future__ import annotations

from tools.common import clean_text, make_posting
from tools.geo import countries_in
from tools.sources._http import get, rss_items

NAME = "weworkremotely"
CREDIT = ("We Work Remotely", "https://weworkremotely.com")
TERMS = "https://weworkremotely.com/remote-job-rss-feed"
FEEDS = ("remote-jobs.rss", "categories/all-other-remote-jobs.rss", "categories/remote-customer-support-jobs.rss",
         "categories/remote-design-jobs.rss", "categories/remote-management-and-finance-jobs.rss",
         "categories/remote-product-jobs.rss", "categories/remote-sales-and-marketing-jobs.rss",
         "categories/remote-programming-jobs.rss", "categories/remote-devops-sysadmin-jobs.rss")


def fetch() -> list[dict]:
    rows = []
    for feed in FEEDS:
        try:
            items = rss_items(get(f"https://weworkremotely.com/{feed}", delay=2).text)
        except Exception as e:
            print(f"  wwr {feed}: {e}")
            continue
        for f in items:
            title = f.get("title", "")
            company, _, role = title.partition(":")
            region = f.get("region", "")
            country = clean_text(f.get("country", ""))
            rows.append(make_posting(
                source=NAME, external_id=f.get("guid") or f.get("link"), title=role.strip() or title,
                organization=company.strip() if role else "", location=f"{region} {country}".strip(),
                countries=countries_in(country), remote=True,
                remote_scope="countries" if country else ("worldwide" if "anywhere" in region.lower() else None),
                posted=f.get("pubDate"), url=f.get("link"), description=f.get("description"),
                tags=[f.get("category", "")]))
    return rows
