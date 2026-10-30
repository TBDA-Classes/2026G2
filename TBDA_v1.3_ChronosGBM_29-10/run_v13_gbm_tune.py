"""v1.3 — standalone GBM, extended grid (128 combinations), chosen on VALIDATION with rule D10, frozen.

    python run_v13_gbm_tune.py                 # full run
    python run_v13_gbm_tune.py --smoke         # 2 configurations, writes to results/smoke/ only (code check)

Same dataset (v1.2), features, fixed parameters, seed, training circuits and fit cut-off as run_v12_gbm_tune.py.
Changes: grid GBM_GRID_V13 (learning_rate x max_leaf_nodes x min_samples_leaf x l2_regularization), pooled mode
only (GBM_MODE_V13), choice by D10 (selection.py). Never builds test rows.

Baselines B1–B3 are scored on the same rows and written next to every configuration (D10c, tracked only).

Writes models/task8_v1.3_<horizon>.joblib, models/task8_frozen_config_v1.3.json, results/task8_tuning_log_v1.3.csv,
results/task8_validation_predictions_v1.3.parquet (chosen GBM + B1, B2, B3).
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

import config as C
from selection import (scaled_scores, d10_choose, require_d10_agreed, baseline_preds, baseline_reference,
                       add_baseline_columns, write_baseline_reference)
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks, baseline_last_week, \
    baseline_weekday_hour_median
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features, baseline_persistence,
                         GBMForecaster, predictions_frame, series_scale)

ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()

ML = "ML_GBM"
GRID = C.GBM_GRID_V13[:2] if args.smoke else C.GBM_GRID_V13
OUT_R, OUT_M = (Path("results/smoke"), Path("results/smoke")) if args.smoke else (Path("results"), Path("models"))
OUT_R.mkdir(parents=True, exist_ok=True)
frozen = OUT_M / Path(C.FROZEN_V13["task8"]).name
if not args.smoke:
    require_d10_agreed()
if frozen.exists():
    raise SystemExit(f"{frozen} exists — the configuration is frozen. Delete it deliberately to re-tune.")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
frames = _series_frames(h)
log, chosen, val_preds, ref_tables = [], {}, [], []

for hz in C.HORIZONS:
    t0 = time.time()
    cut = fit_cutoff(h, hz, S_all)
    F, _ = training_frame(h, hz, S_train, cut, frames=frames)
    scale = series_scale(h, cut)
    vt = forecast_tasks(h, hz, "validation", S_all)
    assert (vt["split"] == "validation").all()
    V = build_features(h, vt, scale, frames=frames)
    B = baseline_preds(h, vt, frames=frames)
    ref, ref_tab = baseline_reference(B, scale, S_train, hz)
    ref_tables.append(ref_tab)
    rows, models, preds = [], [], []
    for i, params in enumerate(GRID):
        m = GBMForecaster(C.GBM_MODE_V13, params, S_train).fit(F)
        P = predictions_frame(V, m.predict(V), ML)
        s = scaled_scores(P, scale, S_train)
        rows.append({"horizon": hz, "mode": C.GBM_MODE_V13, "config": i, **params,
                     **{k: v for k, v in s.items() if not k.startswith("per_series")},
                     **{f"sMAE_{k}": v for k, v in s["per_series_MAE"].items()}})
        models.append(m), preds.append(P)
    hlog = pd.DataFrame(rows)
    j, hlog = d10_choose(hlog)
    hlog = add_baseline_columns(hlog, ref, ref_tab)
    log.append(hlog)
    row, m, P = hlog.loc[j], models[j], preds[j]
    path = OUT_M / f"task8_{C.TAG13}_{hz.replace('+', 'p')}.joblib"
    joblib.dump(m, path)
    chosen[hz] = dict(mode=C.GBM_MODE_V13, params={k: (float(row[k]) if k != "max_leaf_nodes" and k != "min_samples_leaf"
                                                       else int(row[k])) for k in GRID[0]},
                      config_index=int(row["config"]), validation_score=round(float(row["mean_scaled_MAE"]), 6),
                      validation_scaled_RMSE=round(float(row["mean_scaled_RMSE"]), 6),
                      best_baseline=ref["best_baseline"], best_baseline_score=round(ref["best_baseline_MAE"], 6),
                      n_tied=int(hlog["d10_tied"].sum()), best_score=round(float(hlog["mean_scaled_MAE"].min()), 6),
                      fit_cutoff_utc=str(cut), training_rows=int(F["y_scaled"].notna().sum()),
                      scale_Wh={s: round(float(v), 6) for s, v in scale.items()},
                      model_file=path.name, model_sha256=sha256_file(path))
    val_preds += [P, B]
    print(f"{hz}: {len(GRID)} fits in {time.time() - t0:.0f}s; D10 chose config {int(row['config'])} "
          f"{chosen[hz]['params']} score {row['mean_scaled_MAE']:.4f} ({chosen[hz]['n_tied']} tied); "
          f"best baseline {ref['best_baseline']} {ref['best_baseline_MAE']:.4f}; "
          f"{int(hlog['clearly_beats_best_baseline'].sum())}/{len(hlog)} configs clearly better")

log = pd.concat(log, ignore_index=True)
log.to_csv(OUT_R / f"task8_tuning_log_{C.TAG13}.csv", index=False)
write_baseline_reference(ref_tables, OUT_R / f"baseline_reference_{C.TAG13}.csv")
VP = pd.concat(val_preds, ignore_index=True).drop(columns=["input_hour"], errors="ignore")
VP.to_parquet(OUT_R / f"task8_validation_predictions_{C.TAG13}.parquet", index=False)

meta = json.loads(Path(C.DERIVED_PATH).with_name(Path(C.DERIVED_PATH).stem + "_META.json").read_text())
cfg = dict(
    model=ML, grid_version=C.TAG13, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="Fitted on the training circuits' training data only. Chosen on validation by rule D10 "
         f"(tie margin {C.D10_TIE_MARGIN} scaled MAE, tie-break mean scaled RMSE; DECISIONS_v1.2.md). "
         "Test not used before freezing.",
    d10_agreed=C.D10_AGREED,
    dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION, sha256=sha256_file(C.DERIVED_PATH),
                 source_sha256=meta["source_sha256_file"]),
    series=S_all, training_series=S_train, cold_start_series=sorted(set(S_all) - set(S_train)),
    splits_utc=C.SPLITS, day_ahead_issue=f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", features=FEATURES,
    fixed_params={k: v for k, v in {**C.GBM_FIXED, "random_state": C.SEED}.items() if k not in GRID[0]},
    grid=GRID, n_combinations=len(GRID), mode=C.GBM_MODE_V13, horizons=chosen,
    versions=dict(python=platform.python_version(), sklearn=sklearn.__version__, pandas=pd.__version__,
                  numpy=np.__version__),
)
frozen.write_text(json.dumps(cfg, indent=2))
print(f"wrote {frozen}, tuning log ({len(log)} rows), validation predictions ({len(VP):,} rows)")
