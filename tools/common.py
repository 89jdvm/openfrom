"""Shared paths, record format and text helpers for every openfrom tool.

Posting record (one per line in .tmp/*.jsonl)
  uid            "<source>:<external id>"
  source         e.g. "himalayas", "greenhouse", "reliefweb"
  title, organization, location (free text as published)
  countries      ISO-2 codes named by the source ([] = unknown, never "open")
  remote         True / False / None (unknown)
  remote_scope   "worldwide" | "europe" | "countries" | None
  posted, deadline  "YYYY-MM-DD" or None
  url            link a person can open (the board's page where its terms ask for that)
  salary_min, salary_max, salary_currency, salary_period ("year"|"month"|"hour"|None)
  description    plain text, kept in .tmp only, never published
  tags           list of strings from the source
  fetched        "YYYY-MM-DD"
"""
from __future__ import annotations

import html
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / ".tmp"
RAW = TMP / "raw"          # one file per source from tonight's fetch
SEED = TMP / "seed"        # training data copied from the earlier study
STATE = TMP / "state"      # restored from / uploaded to the Release asset
SITE_DATA = ROOT / "site" / "public" / "data"

NAME = "openfrom"
REPO_URL = "https://github.com/89jdvm/openfrom"
UA = f"{NAME} (+{REPO_URL})"
MAX_AGE_DAYS = 60


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def write_json(path: Path, obj, compact: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    kw = {"separators": (",", ":")} if compact else {"indent": 2}
    path.write_text(json.dumps(obj, ensure_ascii=False, **kw), encoding="utf-8", newline="\n")


def clean_text(s: str | None, limit: int = 6000) -> str:
    """HTML to plain text, whitespace squeezed, trimmed."""
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(html.unescape(s))
    s = s.replace("​", "").replace("‍", "").replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return s[:limit]


def to_date(v) -> str | None:
    """Epoch seconds/ms, ISO strings, RFC 822 dates or date objects -> 'YYYY-MM-DD'."""
    if v in (None, "", 0):
        return None
    try:
        if isinstance(v, (int, float)):
            if v > 1e12:
                v = v / 1000
            return datetime.fromtimestamp(v, tz=timezone.utc).date().isoformat()
        if isinstance(v, (date, datetime)):
            return v.isoformat()[:10]
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(v))
        if m:
            return f"{m[1]}-{m[2]}-{m[3]}"
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(str(v)).date().isoformat()
    except Exception:
        return None


def make_posting(*, source: str, external_id, title: str, organization: str = "",
                 location: str = "", countries=None, remote=None, remote_scope=None,
                 posted=None, deadline=None, url: str = "", salary_min=None, salary_max=None,
                 salary_currency=None, salary_period=None, description: str = "",
                 tags=None) -> dict:
    return {
        "uid": f"{source}:{external_id}",
        "source": source,
        "title": clean_text(title, 200),
        "organization": clean_text(organization, 120).strip(" -–—|·,"),
        "location": clean_text(location, 200),
        "countries": [c for c in (countries or []) if c],
        "remote": remote,
        "remote_scope": remote_scope,
        "posted": to_date(posted),
        "deadline": to_date(deadline),
        "url": url or "",
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_currency,
        "salary_period": salary_period,
        "description": clean_text(description),
        "tags": [str(t)[:60] for t in (tags or [])][:20],
        "fetched": date.today().isoformat(),
    }


def age_days(posted: str | None, today: date | None = None) -> int | None:
    if not posted:
        return None
    today = today or date.today()
    try:
        return (today - date.fromisoformat(posted)).days
    except ValueError:
        return None


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"(https?://|www\.)\S+", re.I)


def short_summary(text: str, limit: int = 200) -> str:
    """At most `limit` characters of plain text, emails and URLs removed, cut at a word."""
    t = _URL.sub("", _EMAIL.sub("", text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= limit:
        return t
    cut = t[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.-")
    return cut + "…"
