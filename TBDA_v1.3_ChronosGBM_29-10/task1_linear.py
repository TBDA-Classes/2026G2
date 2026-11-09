"""Sprint 3 Task 1 — linear regression forecaster, same setup as the Task 8 gradient boosting model.

    python task1_linear.py [--data derived/Storey1_hourly_v1.1.parquet]

Re-uses everything from Task 7/8 so the comparison is like-for-like:
- same derived hourly dataset v1.1, same 8 eligible series, same train/validation split (config.py)
- same forecast tasks per horizon (+1h, +6h, day-ahead issued 00:00 Madrid)
- same model inputs (task8_model.build_features), same per-series scaling, same fit cut-off
- same selection metric: mean over series of (validation MAE / series training mean)

Linear models cannot handle missing inputs, so: numeric inputs are imputed with the TRAINING median plus a
0/1 "was missing" column, then standardised (both fitted on training rows only). Hour and weekday are one-hot,
and the pooled model gets one-hot series dummies (its own level per circuit).

Two loss functions are compared on validation:
- ridge: least squares with an L2 penalty (alpha), the classic linear regression
- lad:   least absolute deviation (median regression), matches MAE, the primary metric

Never reads test targets: test rows are not built here.
Writes results/task1_linear_tuning_log.csv, task1_linear_validation_predictions.parquet,
task1_linear_validation_results.csv, task1_linear_comparison.csv and models/task1_linear_config.json.
"""
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import QuantileRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config as C
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks, score
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features,
                         predictions_frame, scaled_mae_by_series)

ML = "ML_Linear"
CATEGORICAL = ["hour", "weekday"]
NUMERIC = [f for f in FEATURES if f not in CATEGORICAL + ["is_weekend"]]   # is_weekend is implied by weekday
GRID = ([dict(loss="ridge", alpha=a) for a in (0.01, 1.0, 10.0, 100.0)]
        + [dict(loss="lad", alpha=a) for a in (0.0, 1e-4, 1e-3)])         # 7 configurations


class LinearForecaster:
    """Pooled (one model, series dummies) or per-series linear model on scaled targets."""

    def __init__(self, mode: str, loss: str, alpha: float, series: list[str]):
        assert mode in C.MODEL_MODES and loss in ("ridge", "lad")
        self.mode, self.loss, self.alpha, self.series = mode, loss, alpha, list(series)
        self.models: dict = {}

    def _cols(self, pooled):
        return NUMERIC + CATEGORICAL + (["series_id"] if pooled else [])

    def _new(self, pooled):
        cat = CATEGORICAL + (["series_id"] if pooled else [])
        prep = ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True,
                                                keep_empty_features=True), StandardScaler()), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", drop=None), cat),
        ])
        reg = (Ridge(alpha=self.alpha) if self.loss == "ridge"
               else QuantileRegressor(quantile=0.5, alpha=self.alpha, solver="highs"))
        return make_pipeline(prep, reg)

    def fit(self, F: pd.DataFrame):
        F = F[F["y_scaled"].notna()]                                    # missing targets are never filled
        if self.mode == "pooled":
            self.models["ALL"] = self._new(True).fit(F[self._cols(True)], F["y_scaled"])
        else:
            for s in self.series:
                g = F[F["series_id"] == s]
                self.models[s] = self._new(False).fit(g[self._cols(False)], g["y_scaled"])
        return self

    def predict(self, F: pd.DataFrame) -> np.ndarray:
        out = np.full(len(F), np.nan)
        if self.mode == "pooled":
            out[:] = self.models["ALL"].predict(F[self._cols(True)])
        else:
            for s in self.series:
                m = (F["series_id"] == s).to_numpy()
                if m.any():
                    out[m] = self.models[s].predict(F.loc[m, self._cols(False)])
        return np.clip(out, 0, None) * F["scale"].to_numpy()          # energy cannot be negative


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
    a = ap.parse_args()
    Path("models").mkdir(exist_ok=True); Path("results").mkdir(exist_ok=True)

    h = load_derived(a.data)
    S = eligible_series(C.ELIGIBILITY_FILE)
    frames = _series_frames(h)
    log, chosen, val_preds = [], {}, []

    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, S)
        F, scale = training_frame(h, hz, S, cut, frames=frames)
        V = build_features(h, forecast_tasks(h, hz, "validation", S), scale, frames=frames)
        best = None
        for mode in C.MODEL_MODES:
            for i, p in enumerate(GRID):
                m = LinearForecaster(mode, p["loss"], p["alpha"], S).fit(F)
                P = predictions_frame(V, m.predict(V), ML)
                per = scaled_mae_by_series(P, scale)
                row = {"horizon": hz, "mode": mode, "config": i, **p, C.SELECTION_METRIC: per.mean(),
                       **{f"sMAE_{s}": v for s, v in per.items()}}
                log.append(row)
                print(f"  {hz:9s} {mode:10s} {p['loss']:5s} alpha={p['alpha']:<7g} score {per.mean():.4f}")
                if best is None or row[C.SELECTION_METRIC] < best[0][C.SELECTION_METRIC]:
                    best = (row, P)
        row, P = best
        chosen[hz] = dict(mode=row["mode"], loss=row["loss"], alpha=row["alpha"], config_index=int(row["config"]),
                          validation_score=round(float(row[C.SELECTION_METRIC]), 6), fit_cutoff_utc=str(cut),
                          training_rows=int(F["y_scaled"].notna().sum()))
        val_preds.append(P)
        print(f"{hz}: best = {row['mode']} {row['loss']} alpha={row['alpha']} score {row[C.SELECTION_METRIC]:.4f}")

    pd.DataFrame(log).to_csv("results/task1_linear_tuning_log.csv", index=False)
    VP = pd.concat(val_preds, ignore_index=True)
    VP.to_parquet("results/task1_linear_validation_predictions.parquet", index=False)
    score(VP, "energy_Wh", models=[ML]).to_csv("results/task1_linear_validation_results.csv", index=False)

    # side-by-side with the Task 8 baselines and GBM on exactly the same validation hours
    t8 = Path("results/task8_validation_predictions.parquet")
    if t8.exists():
        allp = pd.concat([pd.read_parquet(t8), VP], ignore_index=True)
        models5 = ["B1_last_week", "B2_weekday_hour_median", "B3_persistence", "ML_GBM", ML]
        score(allp, "energy_Wh", models=models5).to_csv("results/task1_linear_comparison.csv", index=False)

    meta = json.loads(a.data.with_name(a.data.stem + "_META.json").read_text())
    Path("models/task1_linear_config.json").write_text(json.dumps(dict(
        model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rule="Same protocol as Task 8: fitted on training data only, chosen on validation by "
             f"{C.SELECTION_METRIC}. Test not used.",
        dataset=dict(file=a.data.name, version=C.DERIVED_VERSION, sha256=sha256_file(a.data),
                     source_sha256=meta["source_sha256_file"]),
        series=S, splits_utc=C.SPLITS, numeric_inputs=NUMERIC, categorical_inputs=CATEGORICAL, grid=GRID,
        modes=C.MODEL_MODES, horizons=chosen,
        versions=dict(python=platform.python_version(), sklearn=sklearn.__version__, pandas=pd.__version__,
                      numpy=np.__version__)), indent=2))
    print("wrote results/task1_linear_* and models/task1_linear_config.json")
