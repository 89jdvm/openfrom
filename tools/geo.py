"""Countries, regions and a location-text parser.

Regions are sets of ISO-2 codes. UN M49 continents and subregions, plus the
shorthand job ads use: LATAM, EMEA, APAC, Americas, North America, EU, Europe.
"""
from __future__ import annotations

import re

from tools.geo_data import ALIASES, CITIES, RAW

COUNTRIES: dict[str, dict] = {}
for line in RAW.strip().splitlines():
    code, en, es, sub, lo, hi = line.split("|")
    COUNTRIES[code] = {"en": en, "es": es, "sub": sub, "utc": (float(lo), float(hi))}


def _sub(*subs: str) -> set[str]:
    return {c for c, v in COUNTRIES.items() if v["sub"] in subs}


AFRICA = _sub("NAF", "EAF", "MAF", "SAF", "WAF")
LATAM = _sub("CAR", "CAM", "SAM")
NORTH_AMERICA = {"US", "CA"}
AMERICAS = LATAM | _sub("NAM")
ASIA = _sub("CAS", "EAS", "SEA", "SAS", "WAS")
EUROPE_M49 = _sub("EEU", "NEU", "SEU", "WEU")
OCEANIA = _sub("ANZ", "MEL", "MIC", "POL")
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV",
      "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
EEA = EU | {"IS", "LI", "NO"}
# "Europe" in a remote ad: M49 Europe plus Cyprus, without Russia and Belarus.
EUROPE = (EUROPE_M49 | {"CY"}) - {"RU", "BY"}
MIDDLE_EAST = {"AE", "BH", "CY", "EG", "IL", "IQ", "IR", "JO", "KW", "LB", "OM", "PS", "QA", "SA", "SY",
               "TR", "YE"}
EMEA = EUROPE | MIDDLE_EAST | AFRICA | {"GE", "AM", "AZ"}
APAC = _sub("EAS", "SEA", "SAS") | OCEANIA

REGIONS: dict[str, set[str]] = {
    "AFRICA": AFRICA, "LATAM": LATAM, "NORTH_AMERICA": NORTH_AMERICA, "AMERICAS": AMERICAS,
    "ASIA": ASIA, "EUROPE": EUROPE, "EU": EU, "EEA": EEA, "OCEANIA": OCEANIA, "EMEA": EMEA,
    "APAC": APAC, "MIDDLE_EAST": MIDDLE_EAST,
}

# Region words -> region key. Longest phrases first so "north america" beats "america".
REGION_WORDS: list[tuple[str, str]] = [
    (r"latin\s?america|latam|lat\.?\s?am|latinoam[eé]rica|am[eé]rica latina|south america|sudam[eé]rica|central america|centroam[eé]rica|caribbean", "LATAM"),
    (r"north america|norteam[eé]rica|am[eé]rica del norte|\bnam\b|\bnoram\b", "NORTH_AMERICA"),
    (r"\bthe americas\b|\bamericas\b|\bamer\b|\bam[eé]ricas\b", "AMERICAS"),
    (r"\bemea\b", "EMEA"),
    (r"\bapac\b|asia[- ]pacific|asia pac[ií]fico", "APAC"),
    (r"\beurope\b|\beuropean\b|\beuropa\b|\beu\b|european union|uni[oó]n europea|\beea\b|\bcet\b|\bcest\b", "EUROPE"),
    (r"\bafrica\b|\b[aá]frica\b", "AFRICA"),
    (r"middle east|oriente medio|\bmena\b", "MIDDLE_EAST"),
    (r"\basia\b", "ASIA"),
    (r"\boceania\b|\banz\b", "OCEANIA"),
]
REGION_RX = [(re.compile(rx, re.I), key) for rx, key in REGION_WORDS]

US_STATES = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
             "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
             "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
             "WI", "WY", "DC"}
US_STATE_NAMES = ["alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
                  "delaware", "florida", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
                  "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota",
                  "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
                  "new mexico", "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
                  "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas",
                  "utah", "vermont", "virginia", "west virginia", "wisconsin", "wyoming"]

_NAMES: dict[str, str] = {}
for _c, _v in COUNTRIES.items():
    _NAMES[_v["en"].lower()] = _c
    _NAMES[_v["es"].lower()] = _c
_NAMES.update(ALIASES)
_NAME_RX = re.compile(
    r"(?<![a-zà-ÿ])(" + "|".join(re.escape(n) for n in sorted(_NAMES, key=len, reverse=True)) + r")(?![a-zà-ÿ])")
_CITY_RX = re.compile(
    r"(?<![a-zà-ÿ])(" + "|".join(re.escape(n) for n in sorted(CITIES, key=len, reverse=True)) + r")(?![a-zà-ÿ])")
_STATE_NAME_RX = re.compile(r"(?<![a-z])(" + "|".join(US_STATE_NAMES) + r")(?![a-z])")
_STATE_CODE_RX = re.compile(r"(?:,\s*|\b[A-Z][a-z]+\s)(" + "|".join(sorted(US_STATES)) + r")\b(?!\.)")
_ISO_TOKEN_RX = re.compile(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])")


def countries_in(text: str | None, iso_tokens: bool = False) -> list[str]:
    """ISO codes named in a location string, in order of appearance (countries, big cities,
    US states). With iso_tokens, bare two-letter capitals like "DE" also count."""
    if not text:
        return []
    low = text.lower()
    hits: list[tuple[int, str]] = []
    # "Georgia" alone is the country; with a US context it is the state.
    for m in _NAME_RX.finditer(low):
        hits.append((m.start(), _NAMES[m.group(1)]))
    for m in _CITY_RX.finditer(low):
        hits.append((m.start(), CITIES[m.group(1)]))
    for m in _STATE_NAME_RX.finditer(low):
        hits.append((m.start(), "US"))
    if not hits:  # "Austin, TX"; but never "Germany, DE"
        for m in _STATE_CODE_RX.finditer(text):
            hits.append((m.start(1), "US"))
    if iso_tokens:
        for m in _ISO_TOKEN_RX.finditer(text):
            if m.group(1) in COUNTRIES:
                hits.append((m.start(), m.group(1)))
    out: list[str] = []
    for _, c in sorted(hits):
        if c not in out:
            out.append(c)
    if "US" in out and "GE" in out and re.search(r"georgia", low):
        out.remove("GE")
    return out


def regions_in(text: str | None) -> list[str]:
    if not text:
        return []
    found = []
    for rx, key in REGION_RX:
        if rx.search(text) and key not in found:
            found.append(key)
    # "North America" also matches the bare "america(s)" rule only if written so; drop the
    # wider Americas when only "North America" was said.
    if "NORTH_AMERICA" in found and "AMERICAS" in found and not re.search(r"\bamericas\b|\bamer\b", text, re.I):
        found.remove("AMERICAS")
    return found


def expand(regions: list[str], countries: list[str]) -> set[str]:
    out = set(countries)
    for r in regions:
        out |= REGIONS.get(r, set())
    return out


def utc_overlap(code: str, lo: float, hi: float) -> bool:
    """Does the country's standard-time offset range touch [lo, hi]?"""
    c = COUNTRIES.get(code)
    if not c:
        return False
    a, b = c["utc"]
    return b >= lo and a <= hi
