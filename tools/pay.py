"""Stated pay, normalised to a monthly USD range.

Only pay the ad itself states counts: the source's salary fields first, then the
first pay figure written in the ad text. Nothing is estimated.

Conversion: annual / 12; monthly as is; weekly x 52/12; daily x 21.7;
hourly x 173 (40 h x 52 / 12). Exchange rates: ECB euro reference rates,
cached in .tmp/fx.json for a week, with a fallback snapshot in the code.
"""
from __future__ import annotations

import json
import re
from datetime import date

import requests

from tools.common import TMP, UA

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
FX_CACHE = TMP / "fx.json"
# ECB reference rates of 24 Sep 2026 (units per EUR), used only if the ECB is unreachable.
FALLBACK = {"USD": 1.1367, "GBP": 0.85986, "CHF": 0.9409, "CAD": 1.6047, "AUD": 1.6177,
            "SEK": 11.2645, "NOK": 10.7895, "DKK": 7.4756, "PLN": 4.3823, "CZK": 24.399,
            "HUF": 366.15, "RON": 5.2779, "INR": 109.0775, "BRL": 5.889, "MXN": 19.9878,
            "SGD": 1.4549, "NZD": 2.0049, "ZAR": 18.6836, "JPY": 180.57, "PHP": 71.328,
            "ILS": 3.4649, "TRY": 55.5332, "EUR": 1.0}
PER_MONTH = {"annual": 1 / 12, "year": 1 / 12, "yearly": 1 / 12, "monthly": 1, "month": 1,
             "weekly": 52 / 12, "week": 52 / 12, "hourly": 173, "hour": 173, "daily": 21.7, "day": 21.7}


def fx_rates(max_age_days: int = 7) -> dict[str, float]:
    """Units of each currency per 1 EUR."""
    if FX_CACHE.exists():
        c = json.loads(FX_CACHE.read_text(encoding="utf-8"))
        if (date.today() - date.fromisoformat(c["fetched"])).days <= max_age_days:
            return c["eur"]
    try:
        xml = requests.get(ECB_URL, headers={"User-Agent": UA}, timeout=30).text
        rates = {m[0]: float(m[1]) for m in re.findall(r"currency='([A-Z]{3})' rate='([\d.]+)'", xml)}
        if "USD" not in rates:
            raise ValueError("no USD rate")
        rates["EUR"] = 1.0
        FX_CACHE.parent.mkdir(parents=True, exist_ok=True)
        FX_CACHE.write_text(json.dumps({"fetched": date.today().isoformat(), "eur": rates}), encoding="utf-8")
        return rates
    except Exception:
        return dict(FALLBACK)


_CUR = r"(?P<c1>US\$|USD\s?\$?|\$|€|EUR\s?|£|GBP\s?)"
_NUM = r"\d{1,3}(?:[,.]\d{3})*(?:\.\d{1,2})?\s?[kK]?|\d+(?:\.\d{1,2})?\s?[kK]?"
_TEXT_PAY = re.compile(
    r"(?<![A-Za-z])" + _CUR + r"\s?(?P<lo>" + _NUM + r")"
    r"(?:\s?(?:-|–|—|to|a|hasta)\s?(?:US\$|USD\s?|\$|€|EUR\s?|£|GBP\s?)?\s?(?P<hi>" + _NUM + r"))?"
    r"(?P<tail>[^\n]{0,28})", re.I)
_PERIODS = [
    ("hourly", r"^\+?\s*(?:usd|eur|gbp)?\s*(?:/|per|an|a|each|por)\s*(?:hour|hr|h)\b|^\s*(?:usd|eur)?\s*hourly|por hora"),
    ("monthly", r"^\+?\s*(?:usd|eur|gbp)?\s*(?:/|per|a|each|al|por)\s*(?:month|mo|mes)\b|^\s*(?:usd|eur)?\s*(?:monthly|mensual)"),
    ("annual", r"^\+?\s*(?:usd|eur|gbp)?\s*(?:/|per|a|each|al|por)\s*(?:year|yr|annum|año)\b|^\s*(?:usd|eur)?\s*(?:annually|annual|yearly|anual|base\b|ote\b)"),
]
_PAY_WORD = re.compile(r"(salary|compensation|pay range|base pay|base salary|pay:|rate:|salario|sueldo|remuneraci|package)[^.\n]{0,40}$", re.I)
_NOT_PAY = re.compile(r"\bfund|raise|revenue|budget|reimburs|stipend|allowance|bonus|wellness|learning|per child|"
                      r"return|valuation|assets|arr\b|mrr\b|gmv|sales of|in sales|spend|portfolio|client|deal|"
                      r"benefit|lessons|courses|equipment|home ?office|coworking|membership|economics|cumulative|project total|"
                      r"set aside|sav(?:e|ed|ings)\b|"
                      r"million|billion|\bm\b|\bbn\b|\bmm\b|per sale|per lead|per appointment|referral", re.I)
_CUR_ISO = {"USD": "USD", "€": "EUR", "EUR": "EUR", "£": "GBP", "GBP": "GBP"}


def _num(s: str | None) -> float:
    if not s:
        return 0.0
    s = s.strip()
    k = s[-1:] in "kK"
    s = s.rstrip("kK ").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d{1,2})?", s):  # 1.144,00 / 45.000
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s) * (1000 if k else 1)
    except ValueError:
        return 0.0


def pay_from_text(text: str):
    """(lo, hi, currency, period) for the first pay figure stated in the text, else None."""
    for m in _TEXT_PAY.finditer(text or ""):
        before = text[max(0, m.start() - 60):m.start()]
        tail = m.group("tail")
        if re.search(r"[A-Za-z]\$?$", text[max(0, m.start() - 3):m.start()]):  # R$, MX$, COP$
            continue
        if _NOT_PAY.search(tail[:18]) or _NOT_PAY.search(before[-55:]):
            continue
        lo, hi = _num(m.group("lo")), _num(m.group("hi"))
        hi = hi or lo
        period = next((name for name, rx in _PERIODS if re.search(rx, tail, re.I)), None)
        if (not period or period == "hourly") and hi >= 20_000 and (period or _PAY_WORD.search(before)):
            period = "annual"
        if not period or lo <= 0 or (period == "annual" and hi < 5_000):
            continue
        cur = _CUR_ISO.get(re.sub(r"[\s$]", "", m.group("c1").upper()), "USD")
        code = re.match(r"\s?\+?\s?([A-Z]{3})\b", tail)  # "$127,500 - $159,500 CAD"
        if code and code[1] not in ("PER", "USD"):
            cur = code[1]
        return lo, hi, cur, period
    return None


def monthly_usd(p: dict, fx: dict[str, float]) -> list[int] | None:
    """[low, high] monthly pay in USD from stated pay, or None."""
    lo, hi = p.get("salary_min"), p.get("salary_max")
    try:
        lo, hi = float(lo or hi or 0), float(hi or lo or 0)
    except (TypeError, ValueError):
        lo = hi = 0.0
    if hi > 0:
        cur, period = (p.get("salary_currency") or "USD").upper(), (p.get("salary_period") or "").lower()
        if not period:
            period = "hourly" if hi < 500 else ("monthly" if hi < 15_000 else "annual")
    else:
        got = pay_from_text(p.get("description") or "")
        if not got:
            return None
        lo, hi, cur, period = got
    rate, factor = fx.get(cur), PER_MONTH.get(period)
    if not rate or not factor:
        return None
    lo, hi = min(lo, hi) or hi, max(lo, hi)
    if hi > 10 * lo:
        return None
    usd = fx["USD"]
    m_lo, m_hi = lo * factor / rate * usd, hi * factor / rate * usd
    if not (100 <= m_hi <= 120_000):
        return None
    return [int(round(m_lo, -1)), int(round(m_hi, -1))]
