"""Sprint 3 Task 1 — linear regression covering ALL 16 circuits (rework, same design as Model 3).

    python task1_linear_all16.py            # choose settings on validation (test not touched)
    python task1_linear_all16.py --test     # run the frozen choice ONCE on the test week

Same rule as the random forest (Model3_RandomForest/task1_random_forest_all16.py):
    what the model must output : all 16 circuits
    what the model trains on   : only the 8 clean NE/NW circuits (S10 eligibility, THRESHOLD 30)
Every circuit is scaled by its OWN training mean and is predicted from its own past values.

Designs compared on validation (pooled only: a per-circuit model cannot predict a circuit it never saw):
    A  pooled, with circuit identity  — one-hot dummy per training circuit; SE/SW get all zeros
    B  pooled, without circuit identity — purely feature-driven (the RF's chosen design)
Grid: ridge alpha 0.01/1/10/100, LAD alpha 0/1e-4/1e-3/1e-2/1e-1 (1e-2 and 1e-1 added because 1e-3
was at the edge of the old grid). Selection: mean over ALL 16 circuits of validation MAE / training mean.
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
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import QuantileRegressor, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import config as C
from task7_pipeline import sha256_file
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median)
from task8_model import (_series_frames, series_scale, fit_cutoff, build_features, baseline_persistence,
                         predictions_frame, scaled_mae_by_series)
from task8_model import FEATURES

CATEGORICAL = ["hour", "weekday"]
NUMERIC = [f for f in FEATURES if f not in CATEGORICAL + ["is_weekend"]]   # is_weekend is implied by weekday

ML = "ML_Linear"
CFG = Path("models/task1_linear_all16_config.json")
GUARD = Path("results/task1_linear_all16_TEST_ALREADY_RUN.txt")
GRID = ([dict(loss="ridge", alpha=a) for a in (0.01, 1.0, 10.0, 100.0)]
        + [dict(loss="lad", alpha=a) for a in (0.0, 1e-4, 1e-3, 1e-2, 1e-1)])
DESIGNS = {"A_with_identity": True, "B_without_identity": False}


class Linear16:
    def __init__(self, loss, alpha, use_identity):
        self.loss, self.alpha, self.use_identity = loss, alpha, use_identity

    def _cols(self):
        return NUMERIC + CATEGORICAL + (["series_id"] if self.use_identity else [])

    def fit(self, F):
        F = F[F["y_scaled"].notna()]
        cat = CATEGORICAL + (["series_id"] if self.use_identity else [])
        prep = ColumnTransformer([
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True,
                                                keep_empty_features=True), StandardScaler()), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),   # unseen circuit -> all-zero dummies
        ])
        reg = (Ridge(alpha=self.alpha) if self.loss == "ridge"
               else QuantileRegressor(quantile=0.5, alpha=self.alpha, solver="highs"))
        self.model = make_pipeline(prep, reg).fit(F[self._cols()], F["y_scaled"])
        return self

    def predict(self, F):
        return np.clip(self.model.predict(F[self._cols()]), 0, None) * F["scale"].to_numpy()


def setup(h, hz, train_s, all_s, frames):
    cut = fit_cutoff(h, hz, all_s)
    scale = series_scale(h, cut)
    pred_s = [s for s in all_s if s in scale.index and np.isfinite(scale[s]) and scale[s] > 0]
    tt = forecast_tasks(h, hz, "train", train_s)
    tt = tt[tt["target_time"] < cut].reset_index(drop=True)
    F = build_features(h, tt, scale, frames=frames)
    return cut, scale, pred_s, F


def per_circuit(P, scale, train_s, model):
    rows = []
    for sid, g in P.groupby("series_id"):
        k = g[g["y_true"].notna() & g["y_pred"].notna()]
        mae = float((k.y_true - k.y_pred).abs().mean()) if len(k) else np.nan
        rows.append(dict(model=model, series_id=sid, in_training=sid in train_s, n_rows=len(g), n_scored=len(k),
                         coverage=len(k) / len(g), MAE=mae,
                         RMSE=float(np.sqrt(((k.y_true - k.y_pred) ** 2).mean())) if len(k) else np.nan,
                         scaled_MAE=mae / scale[sid], mean_Wh=float(k.y_true.mean()) if len(k) else np.nan))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    Path("models").mkdir(exist_ok=True); Path("results").mkdir(exist_ok=True)
    h = load_derived(a.data)
    train_s = eligible_series(a.data.parent / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())
    frames = _series_frames(h)
    print(f"train on {len(train_s)} circuits, predict {len(all_s)}", flush=True)

    if not a.test:
        log, chosen, vp, pcs = [], {}, [], []
        for hz in C.HORIZONS:
            cut, scale, pred_s, F = setup(h, hz, train_s, all_s, frames)
            V = build_features(h, forecast_tasks(h, hz, "validation", pred_s), scale, frames=frames)
            best = None
            for design, use_id in DESIGNS.items():
                for i, p in enumerate(GRID):
                    m = Linear16(p["loss"], p["alpha"], use_id).fit(F)
                    P = predictions_frame(V, m.predict(V), ML)
                    per = scaled_mae_by_series(P, scale).reindex(pred_s)
                    row = {"horizon": hz, "design": design, "config": i, **p,
                           "score_all16": per.mean(), "score_trained8": per[train_s].mean(),
                           "score_unseen8": per.drop(train_s).mean(),
                           **{f"sMAE_{s}": v for s, v in per.items()}}
                    log.append(row)
                    print(f"  {hz:9s} {design:19s} {p['loss']:5s} a={p['alpha']:<6g} all16 {row['score_all16']:.4f}"
                          f"  trained {row['score_trained8']:.4f}  unseen {row['score_unseen8']:.4f}", flush=True)
                    if best is None or row["score_all16"] < best[0]["score_all16"]:
                        best = (row, P)
            row, P = best
            chosen[hz] = dict(design=row["design"], loss=row["loss"], alpha=row["alpha"],
                              validation_score_all16=round(float(row["score_all16"]), 6),
                              fit_cutoff_utc=str(cut), training_rows=int(F["y_scaled"].notna().sum()))
            vp.append(P.assign(horizon=hz)); pcs.append(per_circuit(P, scale, train_s, ML).assign(horizon=hz))
            print(f"{hz}: chosen {chosen[hz]}", flush=True)
        pd.DataFrame(log).to_csv("results/task1_linear_all16_tuning_log.csv", index=False)
        pd.concat(vp).to_parquet("results/task1_linear_all16_validation_predictions.parquet", index=False)
        pd.concat(pcs).to_csv("results/task1_linear_all16_validation_per_circuit.csv", index=False)
        meta = json.loads(a.data.with_name(a.data.stem + "_META.json").read_text())
        CFG.write_text(json.dumps(dict(
            model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            rule="Trained on the 8 NE/NW circuits, predicts all 16; chosen on validation by mean scaled MAE over "
                 "all 16 circuits. Test not used.",
            dataset=dict(file=a.data.name, version=C.DERIVED_VERSION, sha256=sha256_file(a.data),
                         source_sha256=meta["source_sha256_file"]),
            training_circuits=train_s, predicted_circuits=all_s, splits_utc=C.SPLITS,
            numeric_inputs=NUMERIC, categorical_inputs=CATEGORICAL, grid=GRID, designs=list(DESIGNS),
            horizons=chosen, versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                                           pandas=pd.__version__, numpy=np.__version__)), indent=2))
        print(f"wrote {CFG}")
    else:
        if GUARD.exists():
            raise SystemExit(f"{GUARD} exists: the test week has already been scored.")
        cfg = json.loads(CFG.read_text())
        assert sha256_file(a.data) == cfg["dataset"]["sha256"] and train_s == cfg["training_circuits"]
        preds, pcs = [], []
        for hz, c in cfg["horizons"].items():
            cut, scale, pred_s, F = setup(h, hz, train_s, all_s, frames)
            assert str(cut) == c["fit_cutoff_utc"] and int(F["y_scaled"].notna().sum()) == c["training_rows"]
            m = Linear16(c["loss"], c["alpha"], DESIGNS[c["design"]]).fit(F)
            tasks = forecast_tasks(h, hz, "test", pred_s)            # the only place test is touched
            T = build_features(h, tasks, scale, frames=frames)
            P = predictions_frame(T, m.predict(T), ML)
            preds.append(P)
            pcs.append(per_circuit(P, scale, train_s, ML).assign(horizon=hz))
            for name, B in [("B1_last_week", baseline_last_week(h, tasks)),
                            ("B2_weekday_hour_median", baseline_weekday_hour_median(h, tasks)),
                            ("B3_persistence", baseline_persistence(h, tasks, frames=frames))]:
                pcs.append(per_circuit(B, scale, train_s, name).assign(horizon=hz))
            print(f"{hz}: test all16 scaled MAE {pcs[-4].scaled_MAE.mean():.4f}", flush=True)
        pd.concat(preds).to_parquet("results/task1_linear_all16_test_predictions.parquet", index=False)
        pd.concat(pcs).to_csv("results/task1_linear_all16_test_per_circuit.csv", index=False)
        GUARD.write_text(f"Test week scored once on {datetime.now(timezone.utc).isoformat(timespec='seconds')}.\n")
        print("wrote results/task1_linear_all16_test_*")
