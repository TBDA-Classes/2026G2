"""Sprint 3 Task 1 — step 3, stage 3: rolling-origin validation inside the training period.

    python step3_rolling.py

WHY
---
Every selection decision in this project so far rests on ONE validation week: 168 hours.
Differences of one or two percent between configurations cannot be distinguished from noise on
a sample that small, which is how a 1 % gap got read as a winner earlier in the sprint.

This script re-scores the leading configurations on several expanding-window folds taken from
INSIDE the training period, and averages across them. A configuration that wins on three
independent weeks is a real winner; one that wins on a single week may not be.

FOLDS (expanding window, all inside the official training period 19 Aug - 21 Sep)

    fold 1   fit 19 Aug - 31 Aug   score 1 - 7 Sep
    fold 2   fit 19 Aug -  7 Sep   score 8 - 14 Sep
    fold 3   fit 19 Aug - 14 Sep   score 15 - 21 Sep

PROTOCOL
--------
This does not touch the official validation week, which stays as the final confirmation, and
it never touches the test week. The splits in config.py are unchanged — the folds are built by
relabelling a copy of the dataset in memory, so nothing on disk moves and no other model is
affected.

CAVEAT, stated rather than hidden: the folds have shorter training windows than the real model
(13, 20 and 27 days against 34), and the earliest fold has little history for the 168-hour and
4-week lag features. So the fold scores are not comparable to the official validation score in
absolute terms. They are used only to RANK configurations against each other, which is what
selection needs.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import task1_random_forest as rf1
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import _series_frames, series_scale, fit_cutoff, build_features, predictions_frame
from task1_random_forest_all16 import Forecaster
from step3_tuning import score_sets, SEARCH_TREES

FOLDS = [
    ("fold1", "2025-08-19", "2025-09-01", "2025-09-01", "2025-09-08"),
    ("fold2", "2025-08-19", "2025-09-08", "2025-09-08", "2025-09-15"),
    ("fold3", "2025-08-19", "2025-09-15", "2025-09-15", "2025-09-22"),
]


def relabel(h: pd.DataFrame, tr_start, tr_end, va_start, va_end) -> pd.DataFrame:
    """A copy of the dataset with `split` rewritten for one fold. Nothing on disk changes."""
    g = h.copy()
    t = g["hour_utc"]
    tr = (t >= pd.Timestamp(tr_start, tz="UTC")) & (t < pd.Timestamp(tr_end, tz="UTC"))
    va = (t >= pd.Timestamp(va_start, tz="UTC")) & (t < pd.Timestamp(va_end, tz="UTC"))
    g["split"] = np.where(tr, "train", np.where(va, "validation", "outside"))
    return g


if __name__ == "__main__":
    Path("results").mkdir(exist_ok=True)
    h = load_derived(Path(C.DERIVED_PATH))
    trained = eligible_series(Path("derived") / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())

    # Candidates: the configuration chosen on the official validation week (first in each list)
    # plus the nearest alternatives, so the folds can either confirm or overturn the choice.
    CANDIDATES = {
        "+1h": [dict(max_depth=12, min_samples_leaf=100, max_features=1.0),
                dict(max_depth=12, min_samples_leaf=60, max_features=1.0),
                dict(max_depth=8, min_samples_leaf=60, max_features=1.0),
                dict(max_depth=4, min_samples_leaf=250, max_features=0.5)],
        "+6h": [dict(max_depth=4, min_samples_leaf=250, max_features=0.5),
                dict(max_depth=4, min_samples_leaf=150, max_features=0.5),
                dict(max_depth=12, min_samples_leaf=60, max_features=0.5),
                dict(max_depth=12, min_samples_leaf=100, max_features=1.0)],
        "day-ahead": [dict(max_depth=4, min_samples_leaf=250, max_features=0.5),
                      dict(max_depth=4, min_samples_leaf=150, max_features=0.5),
                      dict(max_depth=12, min_samples_leaf=60, max_features=0.5),
                      dict(max_depth=12, min_samples_leaf=100, max_features=1.0)],
    }
    rows, t0 = [], time.time()

    for hz in C.HORIZONS:
        cands = pd.DataFrame([dict(config=i, criterion="absolute_error", **p)
                              for i, p in enumerate(CANDIDATES[hz])])

        for name, tr0, tr1, va0, va1 in FOLDS:
            hf = relabel(h, tr0, tr1, va0, va1)
            frames = _series_frames(hf)
            cut = fit_cutoff(hf, hz, all_s)
            scale = series_scale(hf, cut)
            ok = [s for s in all_s if s in scale.index and np.isfinite(scale.get(s, np.nan))]
            tt = forecast_tasks(hf, hz, "train", [s for s in trained if s in ok])
            tt = tt[tt["target_time"] < cut].reset_index(drop=True)
            F = build_features(hf, tt, scale, frames=frames)
            V = build_features(hf, forecast_tasks(hf, hz, "validation", ok), scale, frames=frames)

            for _, r in cands.iterrows():
                p = dict(criterion=r.criterion,
                         max_depth=None if (pd.isna(r.max_depth) or str(r.max_depth) == "None") else int(float(r.max_depth)),
                         min_samples_leaf=int(r.min_samples_leaf), max_features=float(r.max_features))
                rf1.RF_FIXED["n_estimators"] = SEARCH_TREES
                m = Forecaster(p, trained, use_identity=False, seed=C.SEED).fit(F)
                P = predictions_frame(V, m.predict(V), "rf")
                s = score_sets(P, scale, trained)
                rows.append({"horizon": hz, "fold": name, "config": int(r.config),
                             **{k: ("None" if v is None else v) for k, v in p.items()},
                             "train_rows": int(F["y_scaled"].notna().sum()), **s})
            print(f"  {hz:10s} {name} done ({time.time()-t0:.0f}s)", flush=True)

    R = pd.DataFrame(rows)
    R.to_csv("results/step3_stage3_rolling.csv", index=False)

    print("\n" + "=" * 80)
    print("MEAN scaled MAE across folds (all 16 circuits)")
    print("=" * 80)
    for hz in C.HORIZONS:
        k = R[R.horizon == hz]
        agg = (k.groupby(["config", "criterion", "max_depth", "min_samples_leaf", "max_features"])
                 ["sMAE_all16"].agg(["mean", "std", "count"]).reset_index()
                 .sort_values("mean"))
        print(f"\n--- {hz} ---")
        print(agg.round(4).to_string(index=False))
    print("\nwrote results/step3_stage3_rolling.csv")
