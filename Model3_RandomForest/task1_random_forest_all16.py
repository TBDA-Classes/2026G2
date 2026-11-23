"""Sprint 3 Task 1 — random forest covering ALL 16 circuits (step 1 of the rework).

    python task1_random_forest_all16.py

WHY
---
The data owner requires forecasts for every zone and circuit of the floor, but allows us to
choose what the model LEARNS from, provided the choice is logical, explained and documented.

Those are two separate things:
    what the model must output : all 16 circuits
    what the model trains on   : only circuits we can defend

The hourly dataset already contains all 16 circuits (16 x 1,341 = 21,456 rows). The S10
eligibility rule only decided which circuits were EVALUATED, never which could be predicted.
So no dataset change is needed: train on the 8 clean NE/NW circuits, predict all 16, and
report each circuit's error together with how many hours it could actually be scored on.

TRAINING SET (decision, documented)
-----------------------------------
The 8 NE/NW circuits, which hold 99.4-100 % valid hours in validation and test against
34-89 % for SE/SW. Their own past values still drive the SE/SW forecasts, so those circuits
are predicted from their own behaviour, not from NE/NW history.

THE DESIGN QUESTION TESTED HERE
-------------------------------
The pooled model identifies each circuit with a one-hot dummy. A circuit never seen in
training gets an all-zero dummy, so the model treats it as "some circuit" and leans on the
numeric features. Two designs are compared:

    A  with circuit identity    — dummies for the 8 training circuits; unseen circuits all-zero
    B  without circuit identity — no dummies at all; purely feature-driven, so every circuit
                                  is handled the same way whether or not it was in training

B should transfer better to unseen circuits; A should fit the training circuits better. This
script measures both rather than assuming.

Parameters are FIXED here to the v2 winners. Choosing parameters is step 3; this step is only
about coverage and the design question, so the two designs are compared on equal settings.

Never reads test targets.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median)
from task8_model import (FEATURES, _series_frames, series_scale, fit_cutoff, build_features,
                         baseline_persistence, predictions_frame)
from task1_random_forest import RF_FIXED
from sklearn.ensemble import RandomForestRegressor

# v2 winners, fixed for this step
V2_PARAMS = {
    "+1h":       dict(criterion="absolute_error", max_depth=8, min_samples_leaf=30, max_features=1.0),
    "+6h":       dict(criterion="absolute_error", max_depth=6, min_samples_leaf=10, max_features=1.0),
    "day-ahead": dict(criterion="absolute_error", max_depth=6, min_samples_leaf=10, max_features=1.0),
}


class Forecaster:
    """Pooled random forest, with or without one-hot circuit identity."""

    def __init__(self, params: dict, train_series: list[str], use_identity: bool, seed=C.SEED):
        self.params, self.train_series, self.use_identity, self.seed = dict(params), list(train_series), use_identity, seed
        self.model = None

    def _X(self, F: pd.DataFrame) -> pd.DataFrame:
        X = F[FEATURES].astype(float).copy()
        if self.use_identity:
            sid = F["series_id"].to_numpy()
            for s in self.train_series:                 # unseen circuits get all zeros
                X[f"series={s}"] = (sid == s).astype(float)
        return X

    def fit(self, F: pd.DataFrame):
        F = F[F["y_scaled"].notna()]
        self.model = RandomForestRegressor(**RF_FIXED, **self.params, random_state=self.seed)
        self.model.fit(self._X(F), F["y_scaled"])
        return self

    def predict(self, F: pd.DataFrame) -> np.ndarray:
        return np.clip(self.model.predict(self._X(F)), 0, None) * F["scale"].to_numpy()


def per_circuit_metrics(P: pd.DataFrame, scale: pd.Series, n_targets: pd.Series) -> pd.DataFrame:
    """MAE, scaled MAE, WAPE and coverage for every circuit."""
    rows = []
    for sid, g in P.groupby("series_id"):
        k = g[g["y_true"].notna() & g["y_pred"].notna()]
        if len(k) == 0:
            rows.append(dict(series_id=sid, n_scored=0, coverage=0.0, MAE=np.nan,
                             scaled_MAE=np.nan, WAPE=np.nan, mean_Wh=np.nan))
            continue
        mae = float((k["y_true"] - k["y_pred"]).abs().mean())
        rows.append(dict(series_id=sid, n_scored=len(k),
                         coverage=len(k) / max(int(n_targets.get(sid, len(g))), 1),
                         MAE=mae, scaled_MAE=mae / scale[sid],
                         WAPE=float((k["y_true"] - k["y_pred"]).abs().sum() / k["y_true"].sum()),
                         mean_Wh=float(k["y_true"].mean())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
    a = ap.parse_args()
    Path("results").mkdir(exist_ok=True)

    h = load_derived(a.data)
    TRAIN_S = eligible_series(a.data.parent / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    ALL_S = sorted(h["series_id"].unique())
    UNSEEN = [s for s in ALL_S if s not in TRAIN_S]
    print(f"train on {len(TRAIN_S)} circuits, predict {len(ALL_S)}")
    print(f"  unseen in training: {UNSEEN}\n", flush=True)

    frames = _series_frames(h)
    out, preds_all = [], []

    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, ALL_S)
        scale_all = series_scale(h, cut)                       # every circuit scaled by its OWN training mean
        missing = [s for s in ALL_S if s not in scale_all.index or not np.isfinite(scale_all.get(s, np.nan))]
        if missing:
            print(f"  {hz}: no training scale for {missing} — excluded from prediction")
        pred_S = [s for s in ALL_S if s not in missing]

        # training rows: clean circuits only
        ttasks = forecast_tasks(h, hz, "train", TRAIN_S)
        ttasks = ttasks[ttasks["target_time"] < cut].reset_index(drop=True)
        F = build_features(h, ttasks, scale_all, frames=frames)

        # prediction rows: every circuit
        vtasks = forecast_tasks(h, hz, "validation", pred_S)
        V = build_features(h, vtasks, scale_all, frames=frames)
        # coverage denominator = every forecast row we tried to make, not only the ones with truth
        n_targets = V.groupby("series_id").size()

        for design, use_id in [("A with circuit identity", True), ("B without circuit identity", False)]:
            m = Forecaster(V2_PARAMS[hz], TRAIN_S, use_id).fit(F)
            P = predictions_frame(V, m.predict(V), f"RF_{'A' if use_id else 'B'}")
            pc = per_circuit_metrics(P, scale_all, n_targets)
            pc["horizon"], pc["design"] = hz, design
            pc["in_training"] = pc.series_id.isin(TRAIN_S)
            out.append(pc)
            preds_all.append(P.assign(design=design, horizon=hz))
            seen = pc[pc.in_training]; uns = pc[~pc.in_training]
            print(f"  {hz:10s} {design:28s} trained circuits sMAE {seen.scaled_MAE.mean():.4f} | "
                  f"unseen circuits sMAE {uns.scaled_MAE.mean():.4f}  WAPE {100*uns.WAPE.mean():.1f}%",
                  flush=True)

        # baselines on all circuits, for reference
        for name, B in [("B1_last_week", baseline_last_week(h, vtasks)),
                        ("B2_weekday_hour_median", baseline_weekday_hour_median(h, vtasks)),
                        ("B3_persistence", baseline_persistence(h, vtasks, frames=frames))]:
            pc = per_circuit_metrics(B.rename(columns={"y_pred": "y_pred"}), scale_all, n_targets)
            pc["horizon"], pc["design"] = hz, name
            pc["in_training"] = pc.series_id.isin(TRAIN_S)
            out.append(pc)

    R = pd.concat(out, ignore_index=True)
    R.to_csv("results/task1_rf_all16_per_circuit.csv", index=False)
    pd.concat(preds_all, ignore_index=True).to_parquet("results/task1_rf_all16_predictions.parquet", index=False)

    print("\n" + "=" * 92)
    print("SCALED MAE by circuit — validation week (trained circuits marked *)")
    print("=" * 92)
    for hz in C.HORIZONS:
        k = R[(R.horizon == hz) & R.design.str.startswith(("A ", "B "))]
        p = k.pivot_table(index="series_id", columns="design", values="scaled_MAE")
        cov = k[k.design.str.startswith("A ")].set_index("series_id")["coverage"]
        p["coverage"] = cov
        p["*"] = ["*" if s in TRAIN_S else "" for s in p.index]
        print(f"\n--- {hz} ---")
        print(p.round(3).to_string())
    print("\nwrote results/task1_rf_all16_per_circuit.csv")
