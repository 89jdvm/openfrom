"""Polite HTTP for the fetchers: one session, our user-agent, a delay after every
call, and backoff on 429 / 5xx."""
from __future__ import annotations

import time

import requests

from tools.common import UA

S = requests.Session()
S.headers["User-Agent"] = UA


def get(url, *, params=None, headers=None, tries=4, delay=1.0, timeout=45, method="GET", json=None):
    for i in range(tries):
        try:
            r = S.request(method, url, params=params, headers=headers, timeout=timeout, json=json)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code} for {url}")
            r.raise_for_status()
            time.sleep(delay)
            return r
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(2 ** (i + 2))


def rss_items(xml_text: str) -> list[dict]:
    """Items of an RSS feed as {tag: text} dicts. Tolerates feeds that are not
    well-formed XML (raw "&" in titles) by reading items with a regex."""
    import html
    import re
    items = []
    for item in re.findall(r"<item\b[^>]*>(.*?)</item>", xml_text, re.S):
        f = {}
        for m in re.finditer(r"<([A-Za-z][\w:.-]*)\b[^>]*>(.*?)</\1>", item, re.S):
            v = m.group(2).strip()
            v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S)
            f.setdefault(m.group(1), html.unescape(v))
        items.append(f)
    return items
