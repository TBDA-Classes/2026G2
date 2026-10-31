"""v1.3 — linear model (Sprint 3 Task 1, `task1_linear.py`) on the extended v1.3 grid: train, choose on VALIDATION, freeze.

    python run_v13_linear_tune.py              (needs derived/Storey1_hourly_v1.2.parquet and the GBM v1.3 frozen config)
    python run_v13_linear_tune.py --smoke      (tiny grid, reads/writes results/smoke/)

Why this file exists: the Sprint 3 linear model only had 7 configurations per mode (task1_linear.py), and its best
alpha (0.001, LAD) sat at the edge of the grid. The teacher asked for >= 100 combinations per model (D11), so this
script widens the grid and tests the "limit the inputs to the training range" idea listed as open in Mert's README
(README_Task1_linear.md, points 1 and 2).

Same as the GBM v1.3 runs: dataset v1.2, same splits, same inputs (task8_model.FEATURES), same per-circuit scaling,
fitted on the TRAINING circuits (S10 `in_training`), validation forecasts for ALL circuits, selection by mean scaled
validation MAE over the training circuits (D6), ties inside the grid resolved by rule D10 (selection.d10_choose).
Never builds test rows. Nothing here changes the model choice already committed in models/model_choice_v1.3.json.

Grid per horizon and mode (pooled, per_series):
    ridge  alpha in 13 values 0.001 ... 1000 (x3 steps)           x 3 clip rules = 39
    LAD    alpha in 9 values 0, 1e-5 ... 0.1 (quantile 0.5)       x 3 clip rules = 27      -> 66 per mode, 132 per horizon
    clip rule: none | minmax (training min/max) | p01_p99 (training 1st/99th percentile), applied to the standardised
    numeric inputs only (not to the one-hot columns and not to the 0/1 "was missing" indicators).

Writes models/linear_frozen_config_v1.3.json, results/linear_tuning_log_v1.3.csv,
results/linear_validation_predictions_v1.3.parquet.
"""
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import QuantileRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config as C
from selection import scaled_scores, d10_choose, require_d10_agreed
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features, predictions_frame,
                         series_scale)
from task1_linear import LinearForecaster, NUMERIC, CATEGORICAL

ML = "ML_Linear"
CLIP_RULES = ["none", "minmax", "p01_p99"]
RIDGE_ALPHAS = [0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0]   # 13
LAD_ALPHAS = [0.0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 1e-1]                                   # 9
GRID_V13 = ([dict(loss="ridge", alpha=a, clip=c) for a in RIDGE_ALPHAS for c in CLIP_RULES]
            + [dict(loss="lad", alpha=a, clip=c) for a in LAD_ALPHAS for c in CLIP_RULES])           # 39 + 27 = 66


class ClipToTraining(BaseEstimator, TransformerMixin):
    """Clip the first `n_cols` columns to bounds learned on the TRAINING rows (rule: none | minmax | p01_p99)."""

    def __init__(self, rule="none", n_cols=0):
        self.rule, self.n_cols = rule, n_cols

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        k = X[:, :self.n_cols]
        if self.rule == "minmax":
            self.lo_, self.hi_ = k.min(axis=0), k.max(axis=0)
        elif self.rule == "p01_p99":
            self.lo_, self.hi_ = np.percentile(k, 1, axis=0), np.percentile(k, 99, axis=0)
        else:
            self.lo_ = self.hi_ = None
        return self

    def transform(self, X):
        X = np.array(X, dtype=float, copy=True)
        if self.lo_ is not None:
            X[:, :self.n_cols] = np.clip(X[:, :self.n_cols], self.lo_, self.hi_)
        return X


class LinearForecasterClip(LinearForecaster):
    """LinearForecaster of task1_linear.py plus an optional clip of the standardised numeric inputs."""

    def __init__(self, mode, loss, alpha, clip, series):
        super().__init__(mode, loss, alpha, series)
        assert clip in CLIP_RULES
        self.clip = clip

    def _new(self, pooled):
        cat = CATEGORICAL + (["series_id"] if pooled else [])
        # imputer output = the NUMERIC columns in order, then the missing-indicators: clip only the first len(NUMERIC)
        num = make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True),
                            StandardScaler(), ClipToTraining(self.clip, len(NUMERIC)))
        prep = ColumnTransformer([("num", num, NUMERIC),
                                  ("cat", OneHotEncoder(handle_unknown="ignore", drop=None), cat)])
        reg = (Ridge(alpha=self.alpha) if self.loss == "ridge"
               else QuantileRegressor(quantile=0.5, alpha=self.alpha, solver="highs"))
        return make_pipeline(prep, reg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    R, M = (Path("results/smoke"), Path("results/smoke")) if args.smoke else (Path("results"), Path("models"))
    R.mkdir(parents=True, exist_ok=True); M.mkdir(parents=True, exist_ok=True)
    frozen = M / "linear_frozen_config_v1.3.json"
    if not args.smoke:
        require_d10_agreed()
    if frozen.exists():
        raise SystemExit(f"{frozen} exists — frozen. Delete it deliberately to re-tune.")
    grid = ([dict(loss="ridge", alpha=1.0, clip="none"), dict(loss="lad", alpha=1e-3, clip="minmax")]
            if args.smoke else GRID_V13)
    assert args.smoke or len(grid) * len(C.MODEL_MODES) >= 100

    h = load_derived(C.DERIVED_PATH)
    S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
    S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
    frames = _series_frames(h)
    gbm_cfg = json.loads((Path("models") / Path(C.FROZEN_V13["task8"]).name).read_text())   # scale check only
    log, chosen, val_preds = [], {}, []

    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, S_all)
        F, _ = training_frame(h, hz, S_train, cut, frames=frames)
        scale = series_scale(h, cut)
        ref = pd.Series(gbm_cfg["horizons"][hz]["scale_Wh"])
        assert np.allclose(scale.reindex(ref.index), ref, rtol=0, atol=1e-5), "scale differs from the frozen GBM"
        vt = forecast_tasks(h, hz, "validation", S_all)
        assert (vt["split"] == "validation").all()                      # no test row is ever built here
        V = build_features(h, vt, scale, frames=frames)
        rows, preds = [], []
        for mode in C.MODEL_MODES:
            for i, p in enumerate(grid):
                m = LinearForecasterClip(mode, p["loss"], p["alpha"], p["clip"], S_train).fit(F)
                P = predictions_frame(V, m.predict(V), ML)
                s = scaled_scores(P, scale, S_train)
                rows.append(dict(horizon=hz, mode=mode, config=i, **p,
                                 **{k: v for k, v in s.items() if not k.startswith("per_series")},
                                 **{f"sMAE_{k}": v for k, v in s["per_series_MAE"].items()}))
                preds.append(P)
                print(f"  {hz:9s} {mode:10s} {p['loss']:5s} alpha={p['alpha']:<7g} clip={p['clip']:8s} "
                      f"score {s['mean_scaled_MAE']:.4f}", flush=True)
        hl = pd.DataFrame(rows)
        j, hl = d10_choose(hl)                                           # D10 inside one grid
        r = hl.loc[j]
        log.append(hl)
        val_preds.append(preds[j])
        chosen[hz] = dict(mode=r["mode"], loss=r["loss"], alpha=float(r["alpha"]), clip=r["clip"],
                          config_index=int(r["config"]), validation_score=round(float(r["mean_scaled_MAE"]), 6),
                          validation_scaled_RMSE=round(float(r["mean_scaled_RMSE"]), 6),
                          n_tied=int(hl["d10_tied"].sum()), best_score=round(float(hl["mean_scaled_MAE"].min()), 6),
                          fit_cutoff_utc=str(cut), training_rows=int(F["y_scaled"].notna().sum()),
                          scale_Wh={s: round(float(v), 6) for s, v in scale.items()})
        print(f"{hz}: D10 chose {r['mode']} {r['loss']} alpha={r['alpha']:g} clip={r['clip']} "
              f"score {r['mean_scaled_MAE']:.4f} ({chosen[hz]['n_tied']} tied, best {chosen[hz]['best_score']:.4f})",
              flush=True)

    pd.concat(log, ignore_index=True).to_csv(R / f"linear_tuning_log_{C.TAG13}.csv", index=False)
    pd.concat(val_preds, ignore_index=True).to_parquet(R / f"linear_validation_predictions_{C.TAG13}.parquet",
                                                       index=False)
    meta = json.loads(Path(C.DERIVED_PATH).with_name(Path(C.DERIVED_PATH).stem + "_META.json").read_text())
    frozen.write_text(json.dumps(dict(
        model=ML, grid_version=C.TAG13, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rule="Fitted on the training circuits' training data only. Chosen on validation by "
             f"{C.SELECTION_METRIC} over the training circuits (D6), ties by rule D10. Test not used.",
        d10_agreed=C.D10_AGREED,
        dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION, sha256=sha256_file(C.DERIVED_PATH),
                     source_sha256=meta["source_sha256_file"]),
        series=S_all, training_series=S_train, splits_utc=C.SPLITS, numeric_inputs=NUMERIC,
        categorical_inputs=CATEGORICAL, grid=grid, modes=C.MODEL_MODES, n_configurations=len(grid) * len(C.MODEL_MODES),
        horizons=chosen, versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                                       pandas=pd.__version__, numpy=np.__version__)), indent=2))
    print(f"wrote {frozen}, tuning log, validation predictions")


if __name__ == "__main__":
    main()
