"""Jobicy: remote jobs by region. Terms: keep Jobicy as the source and keep the
canonical Jobicy job URL; poll at most hourly."""
from __future__ import annotations

from tools.common import make_posting
from tools.geo import countries_in
from tools.sources._http import get

NAME = "jobicy"
CREDIT = ("Jobicy", "https://jobicy.com")
TERMS = "https://jobicy.com/jobs-rss-feed"
GEOS = ("anywhere", "latam", "emea", "europe", "apac", "usa", "canada", "uk")


def fetch() -> list[dict]:
    rows = []
    for g in GEOS:
        try:
            j = get("https://jobicy.com/api/v2/remote-jobs", params={"geo": g, "count": 100}, delay=2).json()
        except Exception as e:
            print(f"  jobicy geo {g}: {e}")
            continue
        for x in j.get("jobs") or []:
            geo = x.get("jobGeo") or ""
            lo = x.get("salaryMin") or x.get("annualSalaryMin")
            hi = x.get("salaryMax") or x.get("annualSalaryMax")
            rows.append(make_posting(
                source=NAME, external_id=x.get("id"), title=x.get("jobTitle"),
                organization=x.get("companyName"), location=geo, countries=countries_in(geo), remote=True,
                remote_scope="worldwide" if geo.lower() in ("anywhere", "worldwide") else None,
                posted=x.get("pubDate"), url=x.get("url"), salary_min=lo, salary_max=hi,
                salary_currency=x.get("salaryCurrency"),
                salary_period=(x.get("salaryPeriod") or "year") if (lo or hi) else None,
                description=x.get("jobDescription"),
                tags=(x.get("jobIndustry") or []) + (x.get("jobType") or []) + [x.get("jobLevel") or ""]))
    return rows
