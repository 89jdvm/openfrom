"""Remote OK: the latest ~100 jobs plus tag slices. Terms (first item of the API reply):
link back to the Remote OK job page, followed, and mention Remote OK as the source."""
from __future__ import annotations

from tools.common import make_posting
from tools.geo import countries_in
from tools.sources._http import get

NAME = "remoteok"
CREDIT = ("Remote OK", "https://remoteok.com")
TERMS = "https://remoteok.com/api"
TAGS = ("marketing", "sales", "non tech", "hr", "writing", "design", "customer support", "operations",
        "finance", "data", "product", "education", "legal", "management")


def _fix(s: str) -> str:
    try:
        return s.encode("latin-1").decode("utf-8")
    except Exception:
        return s


def fetch() -> list[dict]:
    data = get("https://remoteok.com/api", delay=2).json()[1:]
    for t in TAGS:
        try:
            data += get("https://remoteok.com/api", params={"tag": t}, delay=2).json()[1:]
        except Exception as e:  # one tag failing should not lose the rest
            print(f"  remoteok tag {t}: {e}")
    rows = []
    for x in data:
        if not isinstance(x, dict) or not x.get("position"):
            continue
        loc = _fix(x.get("location") or "")
        rows.append(make_posting(
            source=NAME, external_id=x.get("id"), title=_fix(x.get("position") or ""),
            organization=_fix(x.get("company") or ""), location=loc or "Worldwide",
            countries=countries_in(loc), remote=True, remote_scope=None if loc else "worldwide",
            posted=x.get("date"), url=x.get("url"),
            salary_min=x.get("salary_min") or None, salary_max=x.get("salary_max") or None,
            salary_currency="USD" if x.get("salary_min") else None, salary_period="year",
            description=_fix(x.get("description") or ""), tags=x.get("tags")))
    return rows
