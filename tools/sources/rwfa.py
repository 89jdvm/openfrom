"""Real Work From Anywhere: RSS feeds of work-from-anywhere roles. Its RSS page says the
feeds are free with no limits; no reuse terms are stated. Titles sometimes carry a
region tag (EMEA, APAC, US only...), which who_can_apply reads."""
from __future__ import annotations

from tools.common import make_posting
from tools.sources._http import get, rss_items

NAME = "rwfa"
CREDIT = ("Real Work From Anywhere", "https://www.realworkfromanywhere.com")
TERMS = "https://www.realworkfromanywhere.com/rss-feeds"
FEEDS = ("rss.xml", "remote-customer-support-jobs/rss.xml", "remote-design-jobs/rss.xml",
         "remote-management-and-finance-jobs/rss.xml", "remote-product-jobs/rss.xml",
         "remote-sales-and-marketing-jobs/rss.xml", "remote-software-developer-jobs/rss.xml",
         "remote-devops-and-sysadmin-jobs/rss.xml")


def fetch() -> list[dict]:
    rows = []
    for feed in FEEDS:
        try:
            items = rss_items(get(f"https://www.realworkfromanywhere.com/{feed}", delay=2).text)
        except Exception as e:
            print(f"  rwfa {feed}: {e}")
            continue
        for f in items:
            full = f.get("title", "")
            role, _, company = full.rpartition(" at ")
            rows.append(make_posting(
                source=NAME, external_id=f.get("guid") or f.get("link"), title=(role or full).strip(),
                organization=company.strip(), location=full, remote=True, remote_scope="worldwide",
                posted=f.get("pubDate"), url=f.get("link"), description=f.get("description", "")))
    return rows
