#!/usr/bin/env python3
"""
build_site_data.py -- turn tonight's merged jobs into the site's data files and the next
night's state.

Inputs:  .tmp/jobs.jsonl (merged), .tmp/labels.jsonl, .tmp/skills.jsonl,
         .tmp/emb/jobs.{bin,uids}, .tmp/state/quality.json, .tmp/raw/_status.json
Outputs: .tmp/state/jobs.jsonl     summaries + labels + skills, no ad text
         site/public/data/
           jobs.json     one array per field (compresses well), same order as vectors
           vectors.bin   N x 384 int8, then N float32 scales
           market.json   whole-market counts (who can apply, by role family)
           skills.json   the skill list with English and Spanish names and patterns
           quality.json  label agreement from eval_labels.py
           meta.json     build date, counts, source credits, model settings
           geo.json      countries (English, Spanish, UTC offsets) and regions

A job is listed when it has labels and a vector. Budget: vectors.bin at most 10 MB and
every other file at most 4 MB gzipped; over budget, the newest jobs are kept.

Usage:  python tools/build_site_data.py
"""
from __future__ import annotations

import gzip
import re
import json
import shutil
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import RAW, SITE_DATA, STATE, TMP, iter_jsonl, write_json, write_jsonl  # noqa: E402
from tools.geo import COUNTRIES, REGIONS  # noqa: E402
from tools.skills_vocab import KEPT, VOCAB  # noqa: E402
from tools.vectors import ROW, load_raw  # noqa: E402
from tools.vocab import (EMPLOYER_TYPES, ENGAGEMENT, IMPACT_EMPLOYERS, IMPACT_INDUSTRIES,  # noqa: E402
                         INDUSTRIES, ROLE_FAMILIES, SENIORITY)

MAX_VEC_BYTES = 10 * 1024 * 1024
MAX_GZ = 4 * 1024 * 1024
IMPACT_SOURCES = {"ngojobboard", "pcdn"}
STATE_KEYS = ["uid", "source", "title", "organization", "location", "url", "posted", "deadline", "first_seen",
              "summary", "w", "pay", "also", "labels", "skills", "imp"]

CREDITS = {
    "himalayas": ("Himalayas", "https://himalayas.app"),
    "remoteok": ("Remote OK", "https://remoteok.com"),
    "jobicy": ("Jobicy", "https://jobicy.com"),
    "weworkremotely": ("We Work Remotely", "https://weworkremotely.com"),
    "rwfa": ("Real Work From Anywhere", "https://www.realworkfromanywhere.com"),
    "arbeitnow": ("Arbeitnow", "https://www.arbeitnow.com"),
    "workingnomads": ("Working Nomads", "https://www.workingnomads.com"),
    "workable_board": ("Workable", "https://jobs.workable.com"),
    "greenhouse": ("Greenhouse job boards", "https://www.greenhouse.com"),
    "lever": ("Lever job boards", "https://www.lever.co"),
    "ashby": ("Ashby job boards", "https://www.ashbyhq.com"),
    "recruitee": ("Recruitee job boards", "https://recruitee.com"),
    "ngojobboard": ("NGO Job Board", "https://ngojobboard.org"),
    "pcdn": ("PCDN", "https://pcdn.global"),
}


def w_code(w: dict) -> str:
    """Compact who-can-apply: W worldwide, U unclear, N unknown, else L:<countries>;R:<regions>,
    with ;T:lo,hi appended for a time-zone band."""
    s = w["scope"]
    if s == "unclear":
        return "U"
    if s == "unknown":
        return "N"
    parts = ["W"] if s == "worldwide" else []
    if s == "limited":
        if w.get("countries"):
            parts.append("L:" + ",".join(w["countries"]))
        if w.get("regions"):
            parts.append("R:" + ",".join(w["regions"]))
    if w.get("utc"):
        parts.append("T:" + ",".join(f"{x:g}" for x in w["utc"]))
    return ";".join(parts) or "N"


IMPACT_RX = re.compile(
    r"\b(non-?profit|not-for-profit|ngos?|charit(y|ies)|humanitarian|climate|decarboni[sz]\w*|renewables?|"
    r"clean energy|solar|conservation|biodiversity|reforestation|nature-based|international development|"
    r"global health|public health|human rights|refugees?|poverty|social impact|impact invest\w*|b corp|"
    r"carbon (removal|markets?|credits?|accounting)|circular economy|food security|smallholders?|"
    r"ong|sin fines de lucro|cambio climático|desarrollo sostenible|cooperación internacional|derechos humanos)\b", re.I)


def impact_hint(p: dict) -> bool:
    """A mission word in the title or employer name, or two different ones in the ad text."""
    if IMPACT_RX.search(f"{p.get('title', '')} {p.get('organization', '')}"):
        return True
    hits = {m.group(0).lower() for m in IMPACT_RX.finditer((p.get("description") or "")[:4000])}
    return len(hits) >= 2


def impact(p: dict) -> bool:
    L = p.get("labels") or {}
    return bool(L.get("ind") in IMPACT_INDUSTRIES or L.get("emp") in IMPACT_EMPLOYERS
                or p["source"] in IMPACT_SOURCES or p.get("imp"))


def gz_size(obj) -> int:
    return len(gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))


def main() -> int:
    labels = {r["uid"]: {k: r[k] for k in ("rf", "ind", "sen", "eng", "emp")} for r in iter_jsonl(TMP / "labels.jsonl")}
    skills = {r["uid"]: r["skills"] for r in iter_jsonl(TMP / "skills.jsonl")}
    vuids, vrows = load_raw(TMP / "emb" / "jobs") if Path(f"{TMP / 'emb' / 'jobs'}.uids").exists() else ([], None)
    vidx = {u: i for i, u in enumerate(vuids)}

    jobs = []
    for p in iter_jsonl(TMP / "jobs.jsonl"):
        p["labels"] = p.get("labels") or labels.get(p["uid"])
        if p.get("skills") is None:
            p["skills"] = skills.get(p["uid"])
        if p.get("imp") is None:
            p["imp"] = impact_hint(p)
        if p["labels"] and p["uid"] in vidx:
            jobs.append(p)
    jobs.sort(key=lambda p: (p.get("posted") or p.get("first_seen") or ""), reverse=True)
    cap = MAX_VEC_BYTES // ROW
    dropped_budget = max(0, len(jobs) - cap)
    jobs = jobs[:cap]

    # The next night's state: never the ad text.
    STATE.mkdir(parents=True, exist_ok=True)
    write_jsonl(STATE / "jobs.jsonl", ({k: p.get(k) for k in STATE_KEYS} for p in jobs))
    if (TMP / "quality.json").exists():
        shutil.copy2(TMP / "quality.json", STATE / "quality.json")

    srcs = sorted({p["source"] for p in jobs})
    sidx = {s: i for i, s in enumerate(srcs)}
    cols = {
        "title": [p["title"] for p in jobs],
        "org": [(p.get("organization") or "").strip(" -–—|·,") for p in jobs],
        "url": [p["url"] for p in jobs],
        "src": [sidx[p["source"]] for p in jobs],
        "posted": [p.get("posted") or p.get("first_seen") or "" for p in jobs],
        "loc": [(p.get("location") or "")[:120] for p in jobs],
        "w": [w_code(p["w"]) for p in jobs],
        "pay": [p.get("pay") or 0 for p in jobs],
        "rf": [p["labels"]["rf"] for p in jobs],
        "ind": [p["labels"]["ind"] for p in jobs],
        "sen": [p["labels"]["sen"] for p in jobs],
        "eng": [p["labels"]["eng"] for p in jobs],
        "emp": [p["labels"]["emp"] for p in jobs],
        "sk": [",".join(p.get("skills") or []) for p in jobs],
        "imp": [1 if impact(p) else 0 for p in jobs],
        "sum": [p.get("summary") or "" for p in jobs],
    }
    jobs_json = {"n": len(jobs), "sources": srcs, **cols}
    while gz_size(jobs_json) > MAX_GZ and jobs_json["n"] > 1000:  # keep the newest
        keep = int(jobs_json["n"] * 0.9)
        for k in cols:
            jobs_json[k] = jobs_json[k][:keep]
        dropped_budget += jobs_json["n"] - keep
        jobs_json["n"] = keep
        jobs = jobs[:keep]

    SITE_DATA.mkdir(parents=True, exist_ok=True)
    write_json(SITE_DATA / "jobs.json", jobs_json)
    rows = vrows[[vidx[p["uid"]] for p in jobs]] if jobs else np.zeros((0, ROW), np.uint8)
    with (SITE_DATA / "vectors.bin").open("wb") as f:
        f.write(rows[:, 4:].tobytes())   # N x 384 int8
        f.write(rows[:, :4].tobytes())   # N float32 scales

    scope = Counter(p["w"]["scope"] for p in jobs)
    by_rf = Counter(p["labels"]["rf"] for p in jobs)
    market = {
        "n": len(jobs),
        "scope": dict(scope),
        "worldwide_share": round(scope.get("worldwide", 0) / max(len(jobs), 1), 3),
        "role_families": dict(by_rf.most_common()),
        "impact": sum(cols["imp"]),
    }
    write_json(SITE_DATA / "market.json", market)

    kept = json.loads(KEPT.read_text(encoding="utf-8")) if KEPT.exists() else None
    vocab = [s for s in json.loads(VOCAB.read_text(encoding="utf-8")) if kept is None or s["id"] in kept]
    write_json(SITE_DATA / "skills.json", vocab)

    mp = STATE / "model.npz"
    if mp.exists():
        m = np.load(mp, allow_pickle=False)
        write_json(SITE_DATA / "rfmodel.json", {
            "cls": [str(c) for c in m["rf_cls"]],
            "b": [round(float(x), 4) for x in m["rf_b"]],
            "coef": [[round(float(x), 4) for x in row] for row in m["rf_coef"]],
        })

    q = STATE / "quality.json"
    write_json(SITE_DATA / "quality.json", json.loads(q.read_text(encoding="utf-8")) if q.exists() else {})

    status = json.loads((RAW / "_status.json").read_text(encoding="utf-8")) if (RAW / "_status.json").exists() else {}
    per_source = Counter(p["source"] for p in jobs)
    meta = {
        "built": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "date": date.today().isoformat(),
        "n": len(jobs),
        "dropped_for_budget": dropped_budget,
        "sources": [{"id": s, "name": CREDITS.get(s, (s, ""))[0], "url": CREDITS.get(s, ("", ""))[1],
                     "jobs": per_source[s]} for s in sorted(per_source, key=lambda s: -per_source[s])],
        "fetch": {k: {"rows": v.get("rows"), "down": bool(v.get("error")), "at": v.get("at")} for k, v in status.items()},
        "model": {"name": "Xenova/multilingual-e5-small", "revision": "761b726dd34fb83930e26aab4e9ac3899aa1fa78",
                  "dtype": "q8", "dim": 384, "pooling": "mean", "normalize": True},
        "labels": {
            "rf": {k: v for k, v in ROLE_FAMILIES.items()},
            "ind": {k: v for k, v in INDUSTRIES.items()},
            "sen": SENIORITY, "eng": ENGAGEMENT, "emp": EMPLOYER_TYPES,
        },
    }
    write_json(SITE_DATA / "meta.json", meta)
    geo = {"countries": {c: [v["en"], v["es"], v["utc"][0], v["utc"][1]] for c, v in COUNTRIES.items()},
           "regions": {k: sorted(v) for k, v in REGIONS.items()}}
    write_json(SITE_DATA / "geo.json", geo)

    sizes = {f.name: f.stat().st_size for f in SITE_DATA.iterdir()}
    print(f"listed {len(jobs)} jobs ({dropped_budget} left out for size); worldwide {market['worldwide_share']:.1%}; "
          f"impact {market['impact']}")
    print("  " + ", ".join(f"{k} {v / 1e6:.2f} MB" for k, v in sorted(sizes.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
