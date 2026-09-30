#!/usr/bin/env python3
"""impact_counts.py -- how many listed impact-sector jobs are open to people in Kenya,
Colombia and Ecuador (and how many jobs overall). Reads site/public/data/.

Usage:  python tools/impact_counts.py [KE CO EC ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import SITE_DATA  # noqa: E402
from tools.geo import REGIONS, utc_overlap  # noqa: E402


def open_to(code: str, country: str) -> bool:
    if code in ("U", "N"):
        return False
    world, cs, rs, utc = False, [], [], None
    for part in code.split(";"):
        if part == "W":
            world = True
        elif part.startswith("L:"):
            cs = part[2:].split(",")
        elif part.startswith("R:"):
            rs = part[2:].split(",")
        elif part.startswith("T:"):
            utc = [float(x) for x in part[2:].split(",")]
    if not world and country not in cs and not any(country in REGIONS.get(r, set()) for r in rs):
        return False
    return not utc or utc_overlap(country, utc[0], utc[1])


def main(argv: list[str]) -> int:
    jobs = json.loads((SITE_DATA / "jobs.json").read_text(encoding="utf-8"))
    countries = argv or ["KE", "CO", "EC"]
    n_imp = sum(jobs["imp"])
    print(f"Listed jobs: {jobs['n']}; impact sector: {n_imp}\n")
    for c in countries:
        all_open = sum(open_to(w, c) for w in jobs["w"])
        imp_open = sum(open_to(w, c) for w, i in zip(jobs["w"], jobs["imp"]) if i)
        print(f"- {c}: {all_open} jobs open, {imp_open} of them impact sector")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
