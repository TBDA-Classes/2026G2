"""Sprint 3 Task 1 — random forest forecaster, same setup as the Task 8 gradient boosting model.

    python task1_random_forest.py [--data derived/Storey1_hourly_v1.1.parquet]

Re-uses everything from Task 7/8 so the comparison is like-for-like:
- same derived hourly dataset v1.1, same 8 eligible series, same train/validation split (config.py)
- same forecast tasks per horizon (+1h, +6h, day-ahead issued 00:00 Madrid)
- same model inputs (task8_model.build_features), same per-series scaling, same fit cut-off
- same selection metric: mean over series of (validation MAE / series training mean)

Why a random forest, next to the existing gradient boosting model:
both are ensembles of decision trees, but they are built in opposite ways. Gradient boosting fits trees
SEQUENTIALLY, each one correcting the errors the previous ones left (it attacks bias). A random forest fits
trees INDEPENDENTLY, each on a bootstrap sample of the rows and a random subset of features at every split,
then averages them (it attacks variance). Comparing them tells us whether the remaining error at +6h and
day-ahead comes from the ensemble strategy or from the data itself.

Missing inputs: scikit-learn trees handle NaN natively (>= 1.4), exactly as the Task 8 model does, so no
imputation is needed here. This differs from the linear model, which had to impute. The forest therefore sees
the same inputs as the GBM, with no extra preprocessing step in between.

Two split criteria are compared on validation, mirroring the ridge/LAD comparison of the linear model:
- squared_error: the classic random forest; each leaf predicts the MEAN of its training rows
- absolute_error: each leaf predicts the MEDIAN; matches MAE, the primary metric, and is far less sensitive
  to a few very large hours. It is roughly 5x slower to fit.

Series handling: the pooled model gets one-hot series dummies. scikit-learn's forest has no native
categorical support (unlike HistGradientBoostingRegressor, which the Task 8 model uses with a series code),
so one-hot is used here, as in the linear model. Documented because it is a real difference between the
three implementations.

Never reads test targets: test rows are not built here. Run task1_random_forest_test.py once, after the
team agrees the configuration is frozen.

Writes results/task1_rf_tuning_log.csv, task1_rf_validation_predictions.parquet,
task1_rf_validation_results.csv, task1_rf_comparison.csv and models/task1_rf_config.json.
"""
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor

import config as C
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks, score
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features,
                         predictions_frame, scaled_mae_by_series)

ML = "ML_RandomForest"

# Fixed across the grid. 300 trees matches the Task 8 budget (max_iter=300) in spirit; forests do not
# overfit with more trees, they only get slower, so this is not a tuned parameter.
RF_FIXED = dict(n_estimators=300, bootstrap=True, n_jobs=-1)

# 8 configurations, the same grid size as the Task 8 model.
#   criterion     : the loss the splits optimise (see module docstring)
#   max_features  : fraction of inputs considered at each split. This is THE random forest knob — lower
#                   values decorrelate the trees more, which is what makes averaging them pay off.
#   min_samples_leaf: smallest leaf allowed; larger values smooth the predictions.
RF_GRID = [dict(criterion=c, max_features=mf, min_samples_leaf=ms)
           for c in ("squared_error", "absolute_error")
           for mf in (0.33, 1.0)
           for ms in (1, 10)]


class RandomForestForecaster:
    """Pooled (one model, one-hot series dummies) or per-series random forest on scaled targets."""

    def __init__(self, mode: str, params: dict, series: list[str], seed: int = C.SEED):
        assert mode in C.MODEL_MODES
        self.mode, self.params, self.series, self.seed = mode, dict(params), list(series), seed
        self.models: dict = {}

    def _X(self, F: pd.DataFrame) -> pd.DataFrame:
        X = F[FEATURES].astype(float).copy()
        if self.mode == "pooled":
            # one-hot, with the column order fixed by self.series so train and predict always agree
            sid = F["series_id"].to_numpy()
            for s in self.series:
                X[f"series={s}"] = (sid == s).astype(float)
        return X

    def _new(self):
        return RandomForestRegressor(**RF_FIXED, **self.params, random_state=self.seed)

    def fit(self, F: pd.DataFrame):
        F = F[F["y_scaled"].notna()]                                    # missing targets are never filled
        if self.mode == "pooled":
            self.models["ALL"] = self._new().fit(self._X(F), F["y_scaled"])
        else:
            for s in self.series:
                g = F[F["series_id"] == s]
                self.models[s] = self._new().fit(self._X(g), g["y_scaled"])
        return self

    def predict(self, F: pd.DataFrame) -> np.ndarray:
        out = np.full(len(F), np.nan)
        if self.mode == "pooled":
            out[:] = self.models["ALL"].predict(self._X(F))
        else:
            for s in self.series:
                m = (F["series_id"] == s).to_numpy()
                if m.any():
                    out[m] = self.models[s].predict(self._X(F[m]))
        return np.clip(out, 0, None) * F["scale"].to_numpy()          # energy cannot be negative


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
    a = ap.parse_args()
    Path("models").mkdir(exist_ok=True); Path("results").mkdir(exist_ok=True)

    h = load_derived(a.data)
    S = eligible_series(a.data.parent / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    frames = _series_frames(h)
    log, chosen, val_preds = [], {}, []

    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, S)
        F, scale = training_frame(h, hz, S, cut, frames=frames)
        V = build_features(h, forecast_tasks(h, hz, "validation", S), scale, frames=frames)
        best = None
        for mode in C.MODEL_MODES:
            for i, p in enumerate(RF_GRID):
                m = RandomForestForecaster(mode, p, S).fit(F)
                P = predictions_frame(V, m.predict(V), ML)
                per = scaled_mae_by_series(P, scale)
                row = {"horizon": hz, "mode": mode, "config": i, **p, C.SELECTION_METRIC: per.mean(),
                       **{f"sMAE_{s}": v for s, v in per.items()}}
                log.append(row)
                print(f"  {hz:10s} {mode:10s} {p['criterion']:15s} mf={p['max_features']:<5} "
                      f"leaf={p['min_samples_leaf']:<3} score {per.mean():.4f}", flush=True)
                if best is None or row[C.SELECTION_METRIC] < best[0][C.SELECTION_METRIC]:
                    best = (row, P)
        row, P = best
        chosen[hz] = dict(mode=row["mode"], params={k: row[k] for k in RF_GRID[0]},
                          config_index=int(row["config"]),
                          validation_score=round(float(row[C.SELECTION_METRIC]), 6),
                          fit_cutoff_utc=str(cut), training_rows=int(F["y_scaled"].notna().sum()))
        val_preds.append(P)
        print(f"{hz}: best = {row['mode']} {row['criterion']} mf={row['max_features']} "
              f"leaf={row['min_samples_leaf']} score {row[C.SELECTION_METRIC]:.4f}", flush=True)

    pd.DataFrame(log).to_csv("results/task1_rf_tuning_log.csv", index=False)
    VP = pd.concat(val_preds, ignore_index=True)
    VP.to_parquet("results/task1_rf_validation_predictions.parquet", index=False)
    score(VP, "energy_Wh", models=[ML]).to_csv("results/task1_rf_validation_results.csv", index=False)

    # side-by-side with the Task 8 baselines, the GBM and the linear model on exactly the same hours
    parts, names = [], []
    t8 = Path("results/task8_validation_predictions.parquet")
    if t8.exists():
        parts.append(pd.read_parquet(t8))
        names += ["B1_last_week", "B2_weekday_hour_median", "B3_persistence", "ML_GBM"]
    lin = Path("results/task1_linear_validation_predictions.parquet")
    if lin.exists():
        parts.append(pd.read_parquet(lin))
        names.append("ML_Linear")
    if parts:
        allp = pd.concat(parts + [VP], ignore_index=True)
        score(allp, "energy_Wh", models=names + [ML]).to_csv("results/task1_rf_comparison.csv", index=False)

    meta = json.loads(a.data.with_name(a.data.stem + "_META.json").read_text())
    Path("models/task1_rf_config.json").write_text(json.dumps(dict(
        model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rule="Same protocol as Task 8: fitted on training data only, chosen on validation by "
             f"{C.SELECTION_METRIC}. Test not used.",
        dataset=dict(file=a.data.name, version=C.DERIVED_VERSION, sha256=sha256_file(a.data),
                     source_sha256=meta["source_sha256_file"]),
        series=S, splits_utc=C.SPLITS, features=FEATURES,
        series_encoding="one-hot dummies (pooled mode)",
        missing_values="handled natively by the trees, no imputation",
        fixed_params={**RF_FIXED, "random_state": C.SEED}, grid=RF_GRID, modes=C.MODEL_MODES,
        horizons=chosen,
        versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                      pandas=pd.__version__, numpy=np.__version__)), indent=2))
    print("wrote results/task1_rf_* and models/task1_rf_config.json")
