"""Sprint 3 Task 1 — step 3: choose the parameters, and establish which differences are real.

    python step3_tuning.py --stage 1     # grid search on the all-16 objective
    python step3_tuning.py --stage 2     # seed repetition on the top configurations

WHAT IS DIFFERENT FROM THE EARLIER TUNING
-----------------------------------------
1. THE OBJECTIVE CHANGED. v2 selected on the 8 clean circuits. The deliverable is now all 16,
   so selection scores all 16, each on its own valid hours. Parameters that suit NE/NW are not
   necessarily the ones that transfer to circuits never seen in training.

2. NOISE IS MEASURED, NOT ASSUMED. In the v2 grid the top four configurations at +1h scored
   0.2474, 0.2474, 0.2475 and 0.2479 — a 0.2 % spread across genuinely different settings.
   Calling one of those "best" is reading randomness. Stage 2 re-runs the leading
   configurations across several random seeds and reports the standard error, so the final
   choice can be made with the one-standard-error rule instead of by picking a winner off a
   single number.

3. `criterion` IS SEARCHED AGAIN. It was fixed to absolute_error on v1 evidence, before
   max_depth existed in the grid and before the objective included unseen circuits. Both
   changed, so the assumption is re-tested rather than inherited.

SEARCH COST
-----------
n_estimators = 100 during the search, refitted at 300 for the final model. Verified on three
configurations: the ranking is identical at 100 and 300 and the scores differ by under 0.15 %,
while the search runs three times faster. n_estimators is a compute budget for a forest, not a
hyperparameter — more trees never make it worse.

Model: design B (no circuit identity), chosen in step 1 — identical accuracy to design A on
unseen circuits, with one fewer parameter and no special case for circuits added later.

Trains on the 8 clean NE/NW circuits. Never reads test targets.
"""
from __future__ import annotations

import argparse
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import task1_random_forest as rf1
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import _series_frames, series_scale, fit_cutoff, build_features, predictions_frame
from task1_random_forest_all16 import Forecaster

SEARCH_TREES = 100
FINAL_TREES = 300

GRID = [dict(criterion=c, max_depth=d, min_samples_leaf=ms, max_features=mf)
        for c in ("absolute_error", "squared_error")
        for d in (4, 6, 8, 12, None)
        for ms in (10, 30, 60)
        for mf in (0.5, 1.0)]


def score_sets(P: pd.DataFrame, scale: pd.Series, trained: list[str]) -> dict:
    """Scaled MAE and WAPE, over all 16 circuits and over the 8 trained ones separately."""
    per, out = {}, {}
    for s, g in P.groupby("series_id"):
        k = g[g["y_true"].notna() & g["y_pred"].notna()]
        if len(k) == 0:
            continue
        per[s] = (float((k["y_true"] - k["y_pred"]).abs().mean()) / scale[s],
                  float((k["y_true"] - k["y_pred"]).abs().sum()), float(k["y_true"].sum()))
    for name, sel in [("all16", list(per)), ("trained8", [s for s in per if s in trained]),
                      ("unseen8", [s for s in per if s not in trained])]:
        if not sel:
            continue
        out[f"sMAE_{name}"] = float(np.mean([per[s][0] for s in sel]))
        out[f"WAPE_{name}"] = float(sum(per[s][1] for s in sel) / sum(per[s][2] for s in sel))
    return out


def setup():
    h = load_derived(Path(C.DERIVED_PATH))
    trained = eligible_series(Path("derived") / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())
    frames = _series_frames(h)
    data = {}
    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, all_s)
        scale = series_scale(h, cut)
        tt = forecast_tasks(h, hz, "train", trained)
        tt = tt[tt["target_time"] < cut].reset_index(drop=True)
        F = build_features(h, tt, scale, frames=frames)
        V = build_features(h, forecast_tasks(h, hz, "validation", all_s), scale, frames=frames)
        data[hz] = (F, V, scale)
    return h, trained, all_s, data


def run_one(params, F, V, scale, trained, seed, trees):
    rf1.RF_FIXED["n_estimators"] = trees
    m = Forecaster(params, trained, use_identity=False, seed=seed).fit(F)
    P = predictions_frame(V, m.predict(V), "rf")
    return score_sets(P, scale, trained)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True)
    ap.add_argument("--top", type=int, default=5, help="stage 2: how many leading configs to repeat")
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args()
    Path("results").mkdir(exist_ok=True)
    h, trained, all_s, data = setup()
    print(f"train on {len(trained)} circuits, score on {len(all_s)}", flush=True)

    # ---------------------------------------------------------------- stage 1
    if a.stage == 1:
        rows, t0 = [], time.time()
        for hz in C.HORIZONS:
            F, V, scale = data[hz]
            for i, p in enumerate(GRID):
                s = run_one(p, F, V, scale, trained, C.SEED, SEARCH_TREES)
                rows.append({"horizon": hz, "config": i,
                             **{k: ("None" if v is None else v) for k, v in p.items()}, **s})
                if (i + 1) % 10 == 0:
                    print(f"  {hz:10s} {i+1}/{len(GRID)}  ({time.time()-t0:.0f}s)", flush=True)
            best = min([r for r in rows if r["horizon"] == hz], key=lambda r: r["sMAE_all16"])
            print(f"{hz}: best all16 {best['sMAE_all16']:.4f} "
                  f"({best['criterion']}, depth {best['max_depth']}, leaf {best['min_samples_leaf']}, "
                  f"mf {best['max_features']})", flush=True)
        pd.DataFrame(rows).to_csv("results/step3_stage1_grid.csv", index=False)
        print(f"\nwrote results/step3_stage1_grid.csv  ({time.time()-t0:.0f}s)")

    # ---------------------------------------------------------------- stage 2
    if a.stage == 2:
        g = pd.read_csv("results/step3_stage1_grid.csv")
        rows, t0 = [], time.time()
        for hz in C.HORIZONS:
            F, V, scale = data[hz]
            top = g[g.horizon == hz].nsmallest(a.top, "sMAE_all16")
            for _, r in top.iterrows():
                p = dict(criterion=r.criterion,
                         max_depth=None if (pd.isna(r.max_depth) or str(r.max_depth) == "None") else int(float(r.max_depth)),
                         min_samples_leaf=int(r.min_samples_leaf), max_features=float(r.max_features))
                for seed in range(a.seeds):
                    s = run_one(p, F, V, scale, trained, seed, SEARCH_TREES)
                    rows.append({"horizon": hz, "config": int(r.config), "seed": seed,
                                 **{k: ("None" if v is None else v) for k, v in p.items()}, **s})
                sub = [x for x in rows if x["horizon"] == hz and x["config"] == int(r.config)]
                v = [x["sMAE_all16"] for x in sub]
                print(f"  {hz:10s} cfg {int(r.config):3d} depth {str(p['max_depth']):4s} "
                      f"leaf {p['min_samples_leaf']:2d} mf {p['max_features']}  "
                      f"mean {np.mean(v):.4f}  sd {np.std(v, ddof=1):.4f}", flush=True)
        pd.DataFrame(rows).to_csv("results/step3_stage2_seeds.csv", index=False)
        print(f"\nwrote results/step3_stage2_seeds.csv  ({time.time()-t0:.0f}s)")
