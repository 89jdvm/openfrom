#!/usr/bin/env python3
"""
eval_labels.py -- how often the nearest-match labels agree with the checked AI labels.

5-fold cross-validation grouped by employer (no employer is in both the training and
the test part), on checked seed rows only, next to the majority baseline (always
guessing the most common label). Role family is tried two ways, k=15 vote and logistic
regression; the better one is written to .tmp/label_method.json for label_knn.py.

The employer lookup for industry cannot be tested this way (the employer is always
held out), so the industry figure is for nearest match alone: a floor.

Output: .tmp/quality.json (copied into the site data by build_site_data.py)

Usage:  python tools/eval_labels.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import TMP  # noqa: E402
from tools.label_knn import CHECKED, fit_logreg, knn_vote, org_key, seed_training, smooth_by_employer  # noqa: E402


def folds(groups: list[str], k: int = 5, seed: int = 7) -> list[np.ndarray]:
    uniq = sorted(set(groups))
    rng = np.random.default_rng(seed)
    rng.shuffle(uniq)
    fold_of = {g: i % k for i, g in enumerate(uniq)}
    f = np.array([fold_of[g] for g in groups])
    return [np.where(f == i)[0] for i in range(k)]


def cv(X, y, groups, predict, smooth=None) -> float:
    y = np.asarray(y)
    right = total = 0
    for test in folds(groups):
        train = np.setdiff1d(np.arange(len(y)), test)
        pred = np.asarray(predict(X[train], list(y[train]), X[test]))
        if smooth is not None:
            pred = np.asarray(smooth_by_employer(list(pred), [smooth[i] for i in test]))
        right += int((pred == y[test]).sum())
        total += len(test)
    return right / total


def baseline(y, groups) -> float:
    y = np.asarray(y)
    right = total = 0
    for test in folds(groups):
        train = np.setdiff1d(np.arange(len(y)), test)
        top = Counter(y[train]).most_common(1)[0][0]
        right += int((y[test] == top).sum())
        total += len(test)
    return right / total


def main() -> int:
    rows, X = seed_training()
    chk = np.array([r.get("how") in CHECKED for r in rows])
    Xc = X[chk]
    rc = [r for r, c in zip(rows, chk) if c]
    groups = [org_key(r["organization"]) or r["uid"] for r in rc]
    knn = lambda tr, y, te: knn_vote(tr, y, te)  # noqa: E731
    logreg = lambda tr, y, te: fit_logreg(tr, y).predict(te)  # noqa: E731

    res = {}
    y_rf = [r["role_family"] for r in rc]
    rf_knn, rf_lr = cv(Xc, y_rf, groups, knn), cv(Xc, y_rf, groups, logreg)
    best = "logreg" if rf_lr > rf_knn else "knn"
    res["role_family"] = {"agreement": round(max(rf_knn, rf_lr), 3), "baseline": round(baseline(y_rf, groups), 3),
                          "method": best, "knn": round(rf_knn, 3), "logreg": round(rf_lr, 3), "n": len(rc)}
    y_ind = [r["industry"] for r in rc]
    ind_lr = cv(Xc, y_ind, groups, logreg, smooth=groups)
    res["industry"] = {"agreement": round(ind_lr, 3), "baseline": round(baseline(y_ind, groups), 3),
                       "method": "logreg + employer vote", "knn": round(cv(Xc, y_ind, groups, knn), 3),
                       "n": len(rc)}
    groups_all = [org_key(r["organization"]) or r["uid"] for r in rows]
    for f in ("seniority", "engagement", "employer_type"):
        y = [r[f] or "NS" for r in rows]
        res[f] = {"agreement": round(cv(X, y, groups_all, knn), 3), "baseline": round(baseline(y, groups_all), 3),
                  "method": "knn", "n": len(rows), "approximate": True}
    quality = {"date": date.today().isoformat(), "folds": 5, "grouped_by": "employer",
               "compared_with": "checked AI labels", "fields": res}
    (TMP / "quality.json").write_text(json.dumps(quality, indent=1), encoding="utf-8")
    (TMP / "label_method.json").write_text(json.dumps({"rf": best}), encoding="utf-8")
    for f, v in res.items():
        print(f"{f:14s} agreement {v['agreement']:.1%}  baseline {v['baseline']:.1%}  ({v['method']}, n={v['n']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
