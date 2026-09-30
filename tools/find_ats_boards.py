#!/usr/bin/env python3
"""
find_ats_boards.py -- find employers' public job boards on Greenhouse, Lever, Ashby
and Recruitee, and write tools/sources/ats_boards.csv (name, ats, slug).

Candidates: names given in a text file (one per line, optional "|ats|slug" when the
board is already known), plus the remote-first and impact employers listed below.
Slugs are guessed from the name and each guess is checked against the ATS's public
board API; only boards that answer with at least one job are kept.

Usage:
    python tools/find_ats_boards.py [names.txt ...]
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.sources._http import S  # noqa: E402

OUT = Path(__file__).resolve().parent / "sources" / "ats_boards.csv"

EXTRA = """GitLab;Zapier;Doist;Buffer;Wikimedia Foundation;Mozilla;Canonical;Toggl;Hotjar;Remote;Deel;
Oyster HR;Kiva;GiveDirectly;Code for America;Ushahidi;Development Seed;Open Knowledge Foundation;DataKind;
Khan Academy;Creative Commons;International Rescue Committee;Clinton Health Access Initiative;One Acre Fund;
Watershed;Patch;Pachama;Climeworks;Too Good To Go;Wave;Chainalysis;Automattic;Articulate;Help Scout;
Close;Invision;Elastic;HashiCorp;Grafana Labs;Sourcegraph;PostHog;Supabase;Vercel;Netlify;Figma;Notion;
Duolingo;Coursera;Udemy;Babbel;Preply;Airtable;Webflow;Loom;Miro;Calendly;Dropbox;Stripe;Plaid;Brex;
Gusto;Rippling;Lattice;Culture Amp;Hopin;Contentful;Typeform;Personio;Factorial;Revolut;N26;Wise;
Monzo;Klarna;Spotify;SoundCloud;Mercy Corps;Oxfam;Save the Children;Amnesty International;Human Rights Watch;
Greenpeace;350.org;Rewiring America;Carbon180;RMI;Energy Foundation;ClimateWorks Foundation;
Environmental Defense Fund;The Nature Conservancy;World Resources Institute;Conservation International;
Wildlife Conservation Society;Rainforest Alliance;Acumen;Root Capital;Global Witness;ClientEarth;
Climate Policy Initiative;CDP;E3G;South Pole;Sylvera;Isometric;Carbon Direct;Enveritas;Klim;LiveEO;
Planet Labs;Ecosia;ClimatePartner;Palladium;DAI Global;Chemonics;Fairtrade International;
Forest Trends;Proforest;Preferred by Nature;Oikocredit;GiveWell;Open Philanthropy;80,000 Hours;
Center for Global Development;Innovations for Poverty Action;J-PAL;IDinsight;Evidence Action;
Village Enterprise;BRAC;Living Goods;Last Mile Health;Partners In Health;PATH;Population Council;
Gates Foundation;Mastercard Foundation;Omidyar Network;Skoll Foundation;Ashoka;Echoing Green;
Endeavor;Kiva Microfunds;Zipline;d.light;M-KOPA;Sun King;Bboxx;Twiga Foods;Apollo Agriculture;
Andela;Turing;Toptal;Crossover;Automattic;Aha!;Basecamp;Ghost;DuckDuckGo;Proton;Tailscale;
1Password;Bitwarden;Mattermost;Discourse;Gitpod;Replit;Hugging Face;Cohere;Mistral AI;Scale AI;
Labelbox;Surge AI;Appen;TELUS International;Welocalize;Lionbridge;RWS;Smartling;Unbabel""".replace("\n", "")

ATS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "recruitee": "https://{slug}.recruitee.com/api/offers/",
}


def slugs(name: str) -> list[str]:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\(.*?\)", " ", n)
    words = re.findall(r"[a-z0-9]+", n)
    stop = {"the", "of", "and", "for", "gmbh", "inc", "ltd", "llc", "international", "foundation", "secretariat"}
    core = [w for w in words if w not in stop] or words
    cands = ["".join(words), "".join(core), "-".join(words), "-".join(core)]
    if len(core) == 1:
        cands.append(core[0])
    out = []
    for c in cands:
        if c and c not in out and len(c) >= 3:
            out.append(c)
    return out


def _tokens(s: str) -> set[str]:
    n = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z0-9]{3,}", n)) - {"the", "and", "inc", "ltd", "gmbh", "llc", "careers", "jobs"}


def board_name(ats: str, slug: str, j) -> str | None:
    """The employer name the board itself reports, where the API gives one."""
    if ats == "greenhouse":
        try:
            return S.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=20).json().get("name")
        except Exception:
            return None
    if ats == "recruitee":
        offers = j.get("offers") or []
        return offers[0].get("company_name") if offers else None
    return None


def same_org(name: str, board: str | None, slug: str) -> bool:
    if board:
        a, b = _tokens(name), _tokens(board)
        return bool(a & b) and len(a & b) / len(a | b) >= 0.5
    # Lever and Ashby report no name: accept only a slug spelling out the whole name.
    return slug.replace("-", "") == re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).encode(
        "ascii", "ignore").decode().lower()) and len(slug) >= 5


def jobs_count(ats: str, slug: str, name: str | None = None) -> int:
    try:
        r = S.get(ATS[ats].format(slug=slug), timeout=20)
    except Exception:
        return 0
    if r.status_code != 200:
        return 0
    try:
        j = r.json()
    except ValueError:
        return 0
    if ats == "greenhouse" or ats == "ashby":
        n = len(j.get("jobs") or [])
    elif ats == "lever":
        n = len(j) if isinstance(j, list) else 0
    else:
        n = len(j.get("offers") or [])
    if n and name is not None and not same_org(name, board_name(ats, slug, j), slug):
        return 0
    return n


def main(argv: list[str]) -> int:
    known: dict[str, tuple[str, str]] = {}
    names: list[str] = []
    for f in argv:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            parts = [p.strip() for p in line.split("|")]
            if not parts[0]:
                continue
            names.append(parts[0])
            if len(parts) == 3 and parts[1] in ATS:
                known[parts[0]] = (parts[1], parts[2])
    names += [n.strip() for n in EXTRA.split(";") if n.strip()]
    seen, rows = set(), []
    for name in dict.fromkeys(names):
        tries = [known[name]] if name in known else [(a, s) for s in slugs(name) for a in ATS]
        for ats, slug in tries:
            if (ats, slug) in seen:
                continue
            n = jobs_count(ats, slug, None if name in known else name)
            if n:
                seen.add((ats, slug))
                rows.append({"name": name, "ats": ats, "slug": slug})
                print(f"  {name}: {ats}/{slug} ({n} jobs)", flush=True)
                break
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, ["name", "ats", "slug"], lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["name"].lower()))
    print(f"{len(rows)} boards written to {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
