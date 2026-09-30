#!/usr/bin/env python3
"""
label_knn.py -- label new jobs from the labelled seed jobs nearest to them.

Two steps, because the nightly run never has the seed's ad text:

  --train   (on a machine with the seed) fits the models and writes .tmp/state/model.npz
            and .tmp/state/employers.json. Both hold only numbers, codes and employer
            names: no ad text.
  (default) labels every job in .tmp/jobs.jsonl that has a vector and no labels yet,
            using the stored model, and writes .tmp/labels.jsonl.

Training data: the seed's labels. Role family and industry train on "checked" rows
only (a correction pass whose `how` is vote, checker or fullread). Seniority,
engagement and employer type were never checked; they train on every labelled row
and are always shown as approximate.

Methods (chosen by eval_labels.py, grouped 5-fold cross-validation):
  role family   logistic regression on the vectors (beat the k=15 vote)
  industry      the employer's own checked labels first (most common industry among its
                checked seed jobs, at least 2 and 60% agreeing); otherwise logistic
                regression, then the most common prediction across that employer's jobs
  others        k=15 distance-weighted vote over all labelled seed jobs; seniority reads
                the title first

Usage:  python tools/label_knn.py [--train]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import SEED, STATE, TMP, iter_jsonl, write_jsonl  # noqa: E402
from tools.vectors import load  # noqa: E402

CHECKED = {"vote", "checker", "fullread"}
K = 15
MODEL = STATE / "model.npz"
EMPLOYERS = STATE / "employers.json"

_SENIORITY_TITLE = [
    ("INTERN", r"\b(intern|internship|trainee|working student|werkstudent|pasant[ií]a|becari[oa]|pr[aá]cticas)\b"),
    ("LEAD", r"\b(head of|director|vp\b|vice president|chief|principal|lead\b|jefe|jefa|directora?)\b"),
    ("SENIOR", r"\b(senior|sr\.?|staff)\b"),
    ("JUNIOR", r"\b(junior|jr\.?|entry[- ]level|graduate)\b"),
]
_SEN_RX = [(c, re.compile(rx, re.I)) for c, rx in _SENIORITY_TITLE]


def org_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def seed_training() -> tuple[list[dict], np.ndarray]:
    """Labelled seed rows that have a vector, and their vectors (same order)."""
    uids, M = load(TMP / "emb" / "seed")
    idx = {u: i for i, u in enumerate(uids)}
    rows = [r for r in iter_jsonl(SEED / "seed.jsonl") if r.get("role_family") and r["uid"] in idx]
    return rows, M[[idx[r["uid"]] for r in rows]]


def knn_vote(train: np.ndarray, labels, query: np.ndarray, k: int = K) -> list[str]:
    """Distance-weighted vote of the k most similar training rows, per query row."""
    out = []
    labels = np.asarray(labels)
    for start in range(0, len(query), 2048):
        sims = query[start:start + 2048] @ train.T
        top = np.argpartition(-sims, kth=min(k, sims.shape[1] - 1), axis=1)[:, :k]
        for i, row in enumerate(top):
            w = defaultdict(float)
            for j in row:
                w[labels[j]] += max(float(sims[i, j]), 0.0) ** 4  # close neighbours count more
            out.append(max(w, key=w.get))
    return out


def fit_logreg(train: np.ndarray, labels):
    import warnings
    from sklearn.linear_model import LogisticRegression
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return LogisticRegression(max_iter=2000, C=4.0).fit(train, labels)


def smooth_by_employer(pred: list[str], orgs: list[str]) -> list[str]:
    """Most common prediction across each employer's jobs (employers with 2+ jobs)."""
    by = defaultdict(Counter)
    for p, o in zip(pred, orgs):
        if o:
            by[o][p] += 1
    return [by[o].most_common(1)[0][0] if o and sum(by[o].values()) >= 2 else p for p, o in zip(pred, orgs)]


def employer_industry(rows: list[dict]) -> dict[str, str]:
    by = defaultdict(Counter)
    for r in rows:
        if r.get("how") in CHECKED and r.get("industry"):
            by[org_key(r["organization"])][r["industry"]] += 1
    out = {}
    for org, c in by.items():
        code, n = c.most_common(1)[0]
        if org and n >= 2 and n / sum(c.values()) >= 0.6:
            out[org] = code
    return out


def title_seniority(title: str) -> str | None:
    for code, rx in _SEN_RX:
        if rx.search(title or ""):
            return code
    return None


def train() -> int:
    rows, X = seed_training()
    chk = np.array([r.get("how") in CHECKED for r in rows])
    rc = [r for r, c in zip(rows, chk) if c]
    m_rf = fit_logreg(X[chk], [r["role_family"] for r in rc])
    m_ind = fit_logreg(X[chk], [r["industry"] for r in rc])
    q = np.clip(np.round(X * 127), -127, 127).astype(np.int8)  # unit vectors: fixed scale 1/127
    STATE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        MODEL,
        rf_coef=m_rf.coef_.astype(np.float32), rf_b=m_rf.intercept_.astype(np.float32), rf_cls=np.array(m_rf.classes_, dtype=str),
        ind_coef=m_ind.coef_.astype(np.float32), ind_b=m_ind.intercept_.astype(np.float32), ind_cls=np.array(m_ind.classes_, dtype=str),
        knn_vec=q, sen=np.array([r["seniority"] or "NS" for r in rows]),
        eng=np.array([r["engagement"] or "NS" for r in rows]),
        emp=np.array([r["employer_type"] or "NS" for r in rows]))
    EMPLOYERS.write_text(json.dumps(employer_industry(rows), ensure_ascii=False, sort_keys=True, indent=0),
                         encoding="utf-8")
    print(f"trained on {len(rows)} labelled seed jobs ({len(rc)} checked); "
          f"model {MODEL.stat().st_size / 1e6:.1f} MB")
    return 0


def _predict(coef, b, cls, Q) -> list[str]:
    return list(cls[np.argmax(Q @ coef.T + b, axis=1)])


def apply() -> int:
    m = np.load(MODEL, allow_pickle=False)
    emp_ind = json.loads(EMPLOYERS.read_text(encoding="utf-8"))
    uids, Q = load(TMP / "emb" / "jobs")
    qidx = {u: i for i, u in enumerate(uids)}
    jobs = [p for p in iter_jsonl(TMP / "jobs.jsonl") if p["uid"] in qidx and not p.get("labels")]
    if not jobs:
        write_jsonl(TMP / "labels.jsonl", [])
        print("no unlabelled jobs with vectors")
        return 0
    Qj = Q[[qidx[p["uid"]] for p in jobs]]
    orgs = [org_key(p.get("organization")) for p in jobs]
    rf = _predict(m["rf_coef"], m["rf_b"], m["rf_cls"], Qj)
    ind = smooth_by_employer(_predict(m["ind_coef"], m["ind_b"], m["ind_cls"], Qj), orgs)
    K_ = m["knn_vec"].astype(np.float32) / 127.0
    sen, eng, emp = (knn_vote(K_, m[f], Qj) for f in ("sen", "eng", "emp"))
    out, from_emp = [], 0
    for i, p in enumerate(jobs):
        e = emp_ind.get(orgs[i])
        from_emp += e is not None
        out.append({"uid": p["uid"], "rf": rf[i], "ind": e or ind[i],
                    "sen": title_seniority(p.get("title")) or sen[i], "eng": eng[i], "emp": emp[i]})
    write_jsonl(TMP / "labels.jsonl", out)
    print(f"labelled {len(out)} jobs; industry from the employer's own labels for {from_emp}")
    return 0


if __name__ == "__main__":
    sys.exit(train() if "--train" in sys.argv else apply())
