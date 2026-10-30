"""Task 8 — train on TRAINING data, choose the configuration on VALIDATION, freeze it.

    python run_task8_tune.py [--data derived/Storey1_hourly_v1.1.parquet]

Never reads test targets: test rows are not built here at all.
Writes:
    models/task8_<horizon>.joblib        the chosen fitted model per horizon
    models/task8_frozen_config.json      everything needed to reproduce / audit the choice (refuses to overwrite)
    results/task8_tuning_log.csv         validation score of every configuration
    results/task8_validation_predictions.parquet, results/task8_validation_results.csv
"""
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

import config as C
from task7_pipeline import sha256_file
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median, score)
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features, baseline_persistence,
                         GBMForecaster, predictions_frame, scaled_mae_by_series)

ML = "ML_GBM"
ap = argparse.ArgumentParser()
ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
ap.add_argument("--force", action="store_true", help="overwrite an existing frozen config (re-tuning!)")
a = ap.parse_args()
frozen = Path(C.FROZEN_CONFIG)
if frozen.exists() and not a.force:
    raise SystemExit(f"{frozen} exists — the configuration is frozen. Use --force only to deliberately re-tune.")
Path("models").mkdir(exist_ok=True); Path("results").mkdir(exist_ok=True)

h = load_derived(a.data)
S = eligible_series(C.ELIGIBILITY_FILE)
frames = _series_frames(h)
log, chosen, val_preds = [], {}, []

for hz in C.HORIZONS:
    cut = fit_cutoff(h, hz, S)
    F, scale = training_frame(h, hz, S, cut, frames=frames)
    vt = forecast_tasks(h, hz, "validation", S)
    V = build_features(h, vt, scale, frames=frames)
    best = None
    for mode in C.MODEL_MODES:
        for i, params in enumerate(C.GBM_GRID):
            m = GBMForecaster(mode, params, S).fit(F)
            P = predictions_frame(V, m.predict(V), ML)
            per = scaled_mae_by_series(P, scale)
            row = {"horizon": hz, "mode": mode, "config": i, **params, C.SELECTION_METRIC: per.mean(),
                   **{f"sMAE_{s}": v for s, v in per.items()}}
            log.append(row)
            if best is None or row[C.SELECTION_METRIC] < best[0][C.SELECTION_METRIC]:
                best = (row, m, P)
    row, m, P = best
    path = Path("models") / f"task8_{hz.replace('+', 'p')}.joblib"
    joblib.dump(m, path)
    chosen[hz] = dict(mode=row["mode"], params={k: row[k] for k in C.GBM_GRID[0]}, config_index=int(row["config"]),
                      validation_score=round(float(row[C.SELECTION_METRIC]), 6), fit_cutoff_utc=str(cut),
                      training_rows=int(F["y_scaled"].notna().sum()),
                      scale_Wh={s: round(float(v), 6) for s, v in scale.items()},
                      model_file=path.name, model_sha256=sha256_file(path))
    # baselines on the same validation forecasts, for the 4-model comparison
    val_preds += [P, baseline_last_week(h, vt), baseline_weekday_hour_median(h, vt), baseline_persistence(h, vt, frames=frames)]
    print(f"{hz}: best = {row['mode']} config {row['config']} {chosen[hz]['params']} score {row[C.SELECTION_METRIC]:.4f}")

log = pd.DataFrame(log); log.to_csv("results/task8_tuning_log.csv", index=False)
VP = pd.concat(val_preds, ignore_index=True)
VP.drop(columns=["input_hour"], errors="ignore").to_parquet("results/task8_validation_predictions.parquet", index=False)
models4 = ["B1_last_week", "B2_weekday_hour_median", "B3_persistence", ML]
res = pd.concat([score(VP, "energy_Wh", models=models4).assign(mask="common_4"),
                 score(VP, "energy_Wh", models=[ML]).assign(mask="own_ML")], ignore_index=True)
res.to_csv("results/task8_validation_results.csv", index=False)

meta = json.loads(a.data.with_name(a.data.stem + "_META.json").read_text())
cfg = dict(
    model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="Fitted on training data only (no refit on train+validation, protocol §4/§8/§9). Chosen on validation "
         f"by {C.SELECTION_METRIC} (mean over series of MAE / series training mean). Test not used before freezing.",
    dataset=dict(file=a.data.name, version=C.DERIVED_VERSION, sha256=sha256_file(a.data),
                 source_sha256=meta["source_sha256_file"]),
    series=S, splits_utc=C.SPLITS, day_ahead_issue=f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", features=FEATURES,
    fixed_params={**C.GBM_FIXED, "random_state": C.SEED}, grid=C.GBM_GRID, modes=C.MODEL_MODES,
    horizons=chosen, versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                                   pandas=pd.__version__, numpy=np.__version__),
)
frozen.write_text(json.dumps(cfg, indent=2))
print(f"wrote {frozen}, results/task8_tuning_log.csv ({len(log)} configs), validation results")
