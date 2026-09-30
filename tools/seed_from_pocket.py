#!/usr/bin/env python3
"""
seed_from_pocket.py -- import the earlier labelling study as training data.

The seed is used for training and counts only. It is never listed on the site:
the listed jobs come from tonight's fetch.

Input (copied once into .tmp/seed/ by hand or with --src DIR):
  postings.jsonl    56k postings with full text
  labels.jsonl      AI labels, fields nested under "labels." and "facts."
  labels_fix.jsonl  role family + industry corrections, laid over labels.jsonl

Output (all in .tmp/seed/, never committed):
  seed.jsonl   one row per posting, ONLY the fields in ALLOWED
  desc.jsonl   {uid, text}: full ad text for embedding and skill mining
  req.jsonl    {uid, items}: requirement phrases, for the skill vocabulary
  place.jsonl  {uid, open_ec}: the study's reading of whether a remote job is open
               to someone in Ecuador, used only to test who_can_apply.py

"Checked" = a correction row whose `how` is vote, checker or fullread. None of
these is a hand check; they are agreeing AI labels.

Usage:
    python tools/seed_from_pocket.py [--src DIR]
"""
from __future__ import annotations

import argparse
import codecs
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import SEED, iter_jsonl, write_jsonl  # noqa: E402
from tools.vocab import role_code  # noqa: E402

FILES = ["postings.jsonl", "labels.jsonl", "labels_fix.jsonl"]
ALLOWED = [
    "uid", "title", "organization", "url", "source", "posted", "deadline", "location",
    "countries", "remote", "remote_scope",
    "salary_min", "salary_max", "salary_currency", "salary_period",
    "role_family", "industry", "seniority", "engagement", "employer_type", "how",
]
EXCLUDED_SOURCES = {
    "hn": "posts by individual people",
    codecs.decode("wbozngpu", "rot13"): "a personal pipeline",
    "ba": "not remote",
    "jobtech": "not remote",
    "eures_en": "not remote",
    "ted": "tenders (later version)",
    "worldbank": "tenders (later version)",
    "fourdayweek": "its terms forbid training or populating another job board",
    "getonboard": "its terms forbid republishing and model training",
}
CHECKED = {"vote", "checker", "fullread"}


def copy_inputs(src: Path) -> None:
    SEED.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy2(src / f, SEED / f)


def load_labels() -> dict[str, dict]:
    """Last label record per uid, with the corrections laid over role family and industry."""
    labels: dict[str, dict] = {}
    for r in iter_jsonl(SEED / "labels.jsonl"):
        if r.get("labels"):
            labels[r["uid"]] = {"labels": r["labels"], "facts": r.get("facts") or {}}
    for r in iter_jsonl(SEED / "labels_fix.jsonl"):
        if r["uid"] in labels:
            L = dict(labels[r["uid"]]["labels"])
            L["role_family"], L["industry"], L["how"] = r["role_family"], r["industry"], r["how"]
            labels[r["uid"]]["labels"] = L
    return labels


def project(p: dict, lab: dict | None) -> dict:
    L = (lab or {}).get("labels", {})
    row = {
        "uid": p["uid"],
        "title": p.get("title") or "",
        "organization": p.get("company") or "",
        "url": p.get("url") or "",
        "source": p["source"],
        "posted": p.get("posted"),
        "deadline": p.get("deadline"),
        "location": p.get("location") or "",
        "countries": p.get("countries") or [],
        "remote": p.get("remote"),
        "remote_scope": p.get("remote_scope"),
        "salary_min": p.get("salary_min"),
        "salary_max": p.get("salary_max"),
        "salary_currency": p.get("salary_currency"),
        "salary_period": p.get("salary_period"),
        "role_family": role_code(L.get("role_family")) if L else None,
        "industry": L.get("industry") if L else None,
        "seniority": L.get("seniority") if L else None,
        "engagement": L.get("engagement") if L else None,
        "employer_type": L.get("employer_type") if L else None,
        "how": L.get("how") if L else None,
    }
    assert list(row) == ALLOWED
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, help="folder holding the three input files")
    a = ap.parse_args(argv)
    if a.src:
        copy_inputs(a.src)
    missing = [f for f in FILES if not (SEED / f).exists()]
    if missing:
        print(f"missing in .tmp/seed: {missing}; pass --src")
        return 1

    labels = load_labels()
    rows, desc, req, place = [], [], [], []
    kept, dropped = Counter(), Counter()
    for p in iter_jsonl(SEED / "postings.jsonl"):
        if p["source"] in EXCLUDED_SOURCES:
            dropped[p["source"]] += 1
            continue
        lab = labels.get(p["uid"])
        rows.append(project(p, lab))
        kept[p["source"]] += 1
        if p.get("description"):
            desc.append({"uid": p["uid"], "text": p["description"]})
        if lab:
            items = [str(x) for x in (lab["labels"].get("must_haves") or []) if x]
            if items:
                req.append({"uid": p["uid"], "items": items})
            ec = lab["labels"].get("open_to_ecuador")
            if ec:
                place.append({"uid": p["uid"], "open_ec": ec})

    write_jsonl(SEED / "seed.jsonl", rows)
    write_jsonl(SEED / "desc.jsonl", desc)
    write_jsonl(SEED / "req.jsonl", req)
    write_jsonl(SEED / "place.jsonl", place)

    labelled = sum(1 for r in rows if r["role_family"])
    checked = sum(1 for r in rows if r["how"] in CHECKED)
    print(f"seed rows: {len(rows)}  labelled: {labelled}  checked: {checked}")
    for s, n in kept.most_common():
        print(f"  kept {s:18s} {n:6d}")
    for s, n in dropped.most_common():
        print(f"  dropped {s:15s} {n:6d}  ({EXCLUDED_SOURCES[s]})")
    print(f"descriptions: {len(desc)}  requirement lists: {len(req)}  place facts: {len(place)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
