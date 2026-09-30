#!/usr/bin/env python3
"""
who_can_apply.py -- for a remote job, who can take it from where they live.

Result (a dict):
  scope      "worldwide" | "limited" | "unclear" | "unknown" | "onsite"
  countries  ISO codes the job is open to (scope "limited")
  regions    region keys (LATAM, EMEA, EUROPE, ...) the job is open to
  utc        [lo, hi]: working hours band; a country is open if its offset is within 3 h
  why        a few words saying what decided it (for tests and review, never shipped)

Reading order:
  1. Not remote -> "onsite".
  2. Restriction phrases in the ad text ("must reside in", "authorized to work in",
     "US only", "debes residir en"...). These win over a board's "worldwide" tag,
     because the ad's own words are the employer's rule.
  3. The source's structured countries and the location field.
  4. A time-zone requirement narrows worldwide or regional jobs to a band.
  5. "Worldwide" from the source or the text, unless US-only hiring signals (US tax
     forms) contradict it -> "unclear".
  6. Nothing said -> "unknown". An empty country list is never read as open.

Usage:
    python tools/who_can_apply.py --eval    # agreement with the seed's place labels
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.geo import COUNTRIES, REGIONS, countries_in, regions_in, utc_overlap  # noqa: E402

TZ_SLACK = 3.0   # a named zone ("EST hours") accepts people up to 3 h away
UTC_SLACK = 1.0  # an explicit range ("UTC-3 to UTC+3") accepts 1 h either side

REMOTE_RX = re.compile(r"\bremote\b|\bremotely\b|home[- ]based|work from home|\bwfh\b|telecommut|"
                       r"\banywhere\b|distributed team|\bremoto\b|teletrabajo|en remoto|a distancia|"
                       r"\bvirtual\b|fully[- ]remote|worldwide", re.I)
ONSITE_RX = re.compile(r"\b(on[- ]?site only|in[- ]office|hybrid|híbrido|hibrido|presencial)\b", re.I)

WORLD_RX = re.compile(
    r"work from anywhere|from anywhere in the world|anywhere in the world|\banywhere\b(?! in)|any country|"
    r"any location|location[- ]independent|no matter where you (live|are)|wherever you (live|are)|worldwide|"
    r"\bglobal(ly)? remote|remote[- ]global|fully distributed|all time ?zones|any time ?zone|"
    r"desde cualquier (lugar|parte|país)|cualquier país|todo el mundo|en cualquier lugar", re.I)

# The same, for ad text, without the bare word "anywhere" ("anywhere you go...").
TEXT_WORLD_RX = re.compile(
    r"work (from|remotely from) anywhere(?! in (?!the world))|from anywhere in the world|anywhere in the world|"
    r"from any country|any location in the world|location[- ]independent|no matter where you (live|are|are based)|"
    r"wherever you (live|are based)|work remotely from any|globally remote|fully distributed across|"
    r"desde cualquier (lugar|parte|país) del mundo|desde cualquier país|trabaja desde cualquier lugar", re.I)

# Phrases that introduce the places a candidate must live or be allowed to work in.
TRIGGER_RX = re.compile(
    r"(must|should|need to|needs to|have to|required to|will need to)\s+(currently\s+)?(be\s+)?"
    r"(based|located|residing|reside|live|living|domiciled|situated)\s+(in|within|out of)"
    r"|(candidates|applicants|you)\s+(must\s+|should\s+)?(be\s+)?(based|located|residing|living)\s+(in|within)"
    r"|(legally\s+)?(authori[sz]ed|eligible|permitted|entitled)\s+to\s+work\s+(in|within|for|from)"
    r"|(right|authori[sz]ation|permission)\s+to\s+work\s+(in|within)"
    r"|work(ing)?\s+(authori[sz]ation|permit|visa)\s+(in|for)"
    r"|(open|available|limited|restricted)\s+(only\s+)?to\s+(candidates|applicants|residents|people|individuals|those|talent)"
    r"(\s+(who are|currently))?(\s+(based|located|living|residing))?\s+(in|within|from)"
    r"|(only|currently|exclusively)\s+(hiring|accepting|considering|recruiting)\s+(candidates\s+|applicants\s+|people\s+)?(in|from|within)"
    r"|(we|this role)\s+(can|are able to)\s+only\s+(hire|employ|consider|accept)\s+(\w+\s+){0,3}(in|from|based in|located in)"
    r"|residents?\s+of|resident\s+in|citizens?\s+(of|or permanent residents of)"
    r"|remote\s+(position\s+|role\s+|job\s+)?(within|in|across|throughout)\s+(the\s+)?"
    r"|(anywhere|remote)\s+(in|within|across)\s+"
    r"|(debes|deberás|debe|deberá|necesitas)\s+(residir|vivir|estar\s+(ubicad[oa]|radicad[oa]|basad[oa]))\s+en"
    r"|(residir|residencia|residente|radicad[oa]s?|ubicad[oa]s?|domiciliad[oa]s?)\s+en"
    r"|(permiso|autorización|autorizacion)\s+(de|para)\s+trabaj(ar|o)\s+(en|para)"
    r"|(solo|sólo|únicamente|unicamente)\s+(para\s+)?(candidatos|personas|profesionales|residentes)\s+(de|en|residentes en)",
    re.I)
# "US only", "US-based", "(USA)" style tags.
TAG_RX = re.compile(
    r"\b(US|U\.S\.|USA|UK|EU|EMEA|LATAM|APAC|Canada|Europe|India|Brazil|Mexico|Germany|Spain|Philippines|"
    r"Australia|Canadian|American|European)\s*[- ]?\s*(only|based|residents?\s+only)\b"
    r"(?!\s+(company|companies|team|startup|firm|organi[sz]ation|clients?|business|agency|employer|"
    r"customers?|brand|office|headquarters|hq|non-?profit|leader|provider|platform|bank|fund))", re.I)
US_TAX_RX = re.compile(r"\b(1099|w-?2)\s+(contractor|position|role|basis|employee|only)|\bw-?2\s+only|"
                       r"corp[- ]?to[- ]?corp|\bc2c\b|\bssn\b|social security number|us person|u\.s\. person|"
                       r"security clearance|\bitar\b|green card|us citizen", re.I)

_TZ = [
    (r"\b(us|u\.s\.|american|north american)\s+(time\s?zones?|hours|business hours)", (-8, -5)),
    (r"\b(est|edt|eastern(\s+standard)?\s+time|\bet\b)\b", (-5, -5)),
    (r"\b(cst|cdt|central(\s+standard)?\s+time)\b(?!\s*europe)", (-6, -6)),
    (r"\b(pst|pdt|pacific(\s+standard)?\s+time|\bpt\b)\b", (-8, -8)),
    (r"\b(mst|mdt|mountain\s+time)\b", (-7, -7)),
    (r"\b(cet|cest|central european)\b", (1, 1)),
    (r"\b(gmt|bst|uk)\s+(time|hours|business hours)|\bgmt\b(?!\s*[+-])", (0, 0)),
    (r"\beuropean\s+(time\s?zones?|hours|business hours)", (0, 2)),
    (r"\b(americas|latam)\s+(time\s?zones?|hours)", (-8, -3)),
    (r"\b(apac|asia[- ]pacific)\s+(time\s?zones?|hours)", (5.5, 10)),
    (r"\b(aest|aedt|sydney time)\b", (10, 10)),
    (r"\b(ist|india standard time)\b", (5.5, 5.5)),
    (r"\b(sgt|singapore time)\b", (8, 8)),
]
_TZ_RX = [(re.compile(rx, re.I), band) for rx, band in _TZ]
_TZ_CONTEXT = re.compile(r"time\s?zones?|hours|overlap|working|work\s+(in|during|within)|availability|"
                         r"available|horario|zona horaria", re.I)
_UTC_RX = re.compile(r"\b(?:utc|gmt)\s?([+-−]\s?\d{1,2}(?::?30)?)(?:\s*(?:to|-|–|and|through)\s*(?:utc|gmt)?\s?([+-−]\s?\d{1,2}(?::?30)?))?", re.I)


def _off(s: str) -> float:
    s = s.replace("−", "-").replace(" ", "")
    sign = -1 if s.startswith("-") else 1
    s = s.lstrip("+-")
    h, _, m = s.partition(":")
    if not m and len(h) > 2:
        h, m = h[:-2], h[-2:]
    return sign * (int(h) + (int(m) / 60 if m else 0))


def _window(text: str, start: int, n: int = 90) -> str:
    w = text[start:start + n]
    cut = re.search(r"[.;!?\n]|\s(but|however|and we|we offer|you will)\s", w)
    return w[:cut.start()] if cut else w


def text_places(text: str) -> tuple[list[str], list[str], bool, list[str]]:
    """(countries, regions, says_worldwide, evidence) from restriction phrases in text."""
    cs, rs, world, ev = [], [], False, []
    for m in TRIGGER_RX.finditer(text):
        w = _window(text, m.end())
        if re.match(r"\s*(the\s+)?(world|any\s+(country|location))", w, re.I):
            world = True
            ev.append(m.group(0)[:40] + w[:30])
            continue
        c, r = countries_in(w, iso_tokens=True), regions_in(w)
        # "based in the United States or Canada"; ignore windows that only name a city of the employer
        if c or r:
            cs += [x for x in c if x not in cs]
            rs += [x for x in r if x not in rs]
            ev.append((m.group(0) + w)[:70])
    for m in TAG_RX.finditer(text):
        tag = m.group(1)
        c, r = countries_in(tag, iso_tokens=True), regions_in(tag)
        if tag.lower() in ("american",):
            c = ["US"]
        elif tag.lower() == "canadian":
            c = ["CA"]
        elif tag.lower() == "european":
            r = ["EUROPE"]
        if c or r:
            cs += [x for x in c if x not in cs]
            rs += [x for x in r if x not in rs]
            ev.append(m.group(0))
    return cs, rs, world, ev


def text_utc(text: str) -> tuple[float, float] | None:
    bands = []
    for rx, band in _TZ_RX:
        for m in rx.finditer(text):
            around = text[max(0, m.start() - 60):m.end() + 60]
            if _TZ_CONTEXT.search(around):
                bands.append((band[0] - TZ_SLACK, band[1] + TZ_SLACK))
                break
    for m in _UTC_RX.finditer(text):
        around = text[max(0, m.start() - 60):m.end() + 60]
        if _TZ_CONTEXT.search(around):
            a = _off(m.group(1))
            b = _off(m.group(2)) if m.group(2) else a
            bands.append((min(a, b) - UTC_SLACK, max(a, b) + UTC_SLACK))
    if not bands:
        return None
    return (min(b[0] for b in bands), max(b[1] for b in bands))


def is_remote(p: dict) -> bool:
    if p.get("remote") is True:
        return True
    if p.get("remote") is False:
        return False
    head = f"{p.get('title', '')} {p.get('location', '')}"
    if REMOTE_RX.search(head) and not ONSITE_RX.search(head):
        return True
    return bool(re.search(r"this (is a|is an|role is|position is) (fully |100% )?remote|fully remote (role|position)|"
                          r"100% remote|puesto (100% )?remoto|trabajo remoto", p.get("description") or "", re.I))


def who_can_apply(p: dict) -> dict:
    if not is_remote(p):
        return {"scope": "onsite", "countries": [], "regions": [], "utc": None, "why": "not remote"}
    loc = p.get("location") or ""
    title = p.get("title") or ""
    text = f"{title}\n{p.get('description') or ''}"
    t_cs, t_rs, t_world, ev = text_places(text)
    t_world = t_world or bool(TEXT_WORLD_RX.search(text))
    utc = text_utc(text)
    l_cs = [c for c in (p.get("countries") or []) if c in COUNTRIES]
    l_cs += [c for c in countries_in(loc, iso_tokens=True) if c not in l_cs]
    l_rs = regions_in(loc) + [r for r in regions_in(title) if r not in regions_in(loc)]
    tail = re.search(r"[(\[]\s*([^()\[\]]{2,40})\s*[)\]]\s*$|\s[-–|]\s*([^-–|]{2,40})$", title)
    if tail:
        l_cs += [c for c in countries_in(tail.group(1) or tail.group(2), iso_tokens=True) if c not in l_cs]
    l_world = bool(WORLD_RX.search(loc)) or p.get("remote_scope") == "worldwide"
    tag_cs, tag_rs, _, tag_ev = text_places(f"{title} | {loc}")

    def out(scope, cs=(), rs=(), why=""):
        return {"scope": scope, "countries": list(cs), "regions": list(rs),
                "utc": list(utc) if utc and scope in ("worldwide", "limited") else None, "why": why}

    # 2. The ad's own restriction words.
    if t_cs or t_rs:
        if t_world and not (l_cs or l_rs):
            return out("unclear", why="text says both worldwide and a place: " + "; ".join(ev[:2]))
        return out("limited", t_cs, t_rs, why="text: " + "; ".join(ev[:2]))
    # 3. Structured countries / location field.
    if l_cs or l_rs or tag_cs or tag_rs:
        cs = l_cs + [c for c in tag_cs if c not in l_cs]
        rs = l_rs + [r for r in tag_rs if r not in l_rs]
        if l_world and US_TAX_RX.search(text):
            return out("unclear", why="worldwide label, but US-only hiring signals")
        return out("limited", cs, rs, why=f"location: {loc[:60]}")
    # 5. Worldwide.
    if l_world or t_world:
        if US_TAX_RX.search(text):
            return out("unclear", why="worldwide label, but US-only hiring signals")
        return out("worldwide", why="worldwide" + (" (time zone band)" if utc else ""))
    if utc:
        return out("worldwide", why="only a time-zone band is stated")
    return out("unknown", why="no place stated")


def open_to(w: dict, country: str) -> str:
    """'yes' | 'no' | 'unclear' | 'unknown' for someone living in `country`."""
    s = w["scope"]
    if s == "onsite":
        return "no"
    if s in ("unclear", "unknown"):
        return s
    if s == "limited":
        allowed = set(w["countries"])
        for r in w["regions"]:
            allowed |= REGIONS.get(r, set())
        if country not in allowed:
            return "no"
    if w.get("utc"):
        lo, hi = w["utc"]
        if not utc_overlap(country, lo, hi):
            return "no"
    return "yes"


def evaluate() -> int:
    """Agreement with the seed study's reading of 'open to someone in Ecuador' on remote jobs."""
    from tools.common import SEED, iter_jsonl
    lab = {r["uid"]: r["open_ec"] for r in iter_jsonl(SEED / "place.jsonl")}
    desc = {}
    for d in iter_jsonl(SEED / "desc.jsonl"):
        if d["uid"] in lab:
            desc[d["uid"]] = d["text"]
    n = agree = 0
    conf: dict[tuple[str, str], int] = {}
    misses = []
    for r in iter_jsonl(SEED / "seed.jsonl"):
        truth = lab.get(r["uid"])
        if truth not in ("YES", "LIKELY", "NO") or not r.get("remote"):
            continue
        p = {**r, "description": desc.get(r["uid"], "")}
        got = open_to(who_can_apply(p), "EC")
        t = "open" if truth in ("YES", "LIKELY") else "closed"
        g = "open" if got == "yes" else "closed"
        n += 1
        agree += t == g
        conf[(t, got)] = conf.get((t, got), 0) + 1
        if t != g and len(misses) < 12:
            misses.append((truth, got, r["source"], r["title"][:50], (r["location"] or "")[:40],
                           who_can_apply(p)["why"][:80]))
    print(f"agreement on {n} remote seed jobs: {agree / max(n, 1):.1%}")
    for k, v in sorted(conf.items()):
        print(f"  seed {k[0]:6s} -> ours {k[1]:8s} {v}")
    for m in misses:
        print("  miss:", m)
    return 0


if __name__ == "__main__":
    if "--eval" in sys.argv:
        sys.exit(evaluate())
    print(__doc__)
