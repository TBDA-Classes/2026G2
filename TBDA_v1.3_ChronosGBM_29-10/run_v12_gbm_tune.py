"""v1.2 — standalone GBM (Task 8 model) on dataset v1.2: train, choose on VALIDATION, freeze.

    python run_v12_gbm_tune.py

Same model, features, grid, fixed parameters and seed as Task 8. Changes (DECISIONS_v1.2.md):
- fitted on the TRAINING circuits (S10 v1.2 `in_training`, D4), validation forecasts for ALL circuits (D5);
  a circuit outside training is forecast by the pooled mode only (unseen circuit code, D4b);
- selection (D6): mean scaled validation MAE over the training circuits.
Never builds test rows. Also stores B1–B3 validation forecasts for all circuits (input for point 8).

Writes models/task8_v1.2_<horizon>.joblib, models/task8_frozen_config_v1.2.json, results/task8_tuning_log_v1.2.csv,
results/task8_validation_predictions_v1.2.parquet (GBM chosen config + B1, B2, B3).
"""
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
                             baseline_weekday_hour_median)
from task8_model import (FEATURES, _series_frames, fit_cutoff, training_frame, build_features, baseline_persistence,
                         GBMForecaster, predictions_frame, scaled_mae_by_series, series_scale)

ML = "ML_GBM"
frozen = Path(C.FROZEN_CONFIG)
assert C.DERIVED_VERSION == "1.2" and frozen.name.endswith("_v1.2.json")
if frozen.exists():
    raise SystemExit(f"{frozen} exists — the configuration is frozen. Delete it deliberately to re-tune.")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
frames = _series_frames(h)
log, chosen, val_preds = [], {}, []

for hz in C.HORIZONS:
    cut = fit_cutoff(h, hz, S_all)
    F, _ = training_frame(h, hz, S_train, cut, frames=frames)          # fit on training circuits only
    scale = series_scale(h, cut)                                        # every circuit (train hours < cut)
    vt = forecast_tasks(h, hz, "validation", S_all)
    assert (vt["split"] == "validation").all()
    V = build_features(h, vt, scale, frames=frames)
    best = None
    for mode in C.MODEL_MODES:
        for i, params in enumerate(C.GBM_GRID):
            m = GBMForecaster(mode, params, S_train).fit(F)
            P = predictions_frame(V, m.predict(V), ML)
            per = scaled_mae_by_series(P, scale)
            sel = per.reindex(S_train)
            row = {"horizon": hz, "mode": mode, "config": i, **params, C.SELECTION_METRIC: sel.mean(),
                   "score_all16": per.mean(), "score_core8": per.reindex(C.CORE_8).mean(),
                   **{f"sMAE_{s}": v for s, v in per.items()}}
            log.append(row)
            if best is None or row[C.SELECTION_METRIC] < best[0][C.SELECTION_METRIC]:
                best = (row, m, P)
    row, m, P = best
    path = Path("models") / f"task8_{C.TAG}_{hz.replace('+', 'p')}.joblib"
    joblib.dump(m, path)
    chosen[hz] = dict(mode=row["mode"], params={k: row[k] for k in C.GBM_GRID[0]}, config_index=int(row["config"]),
                      validation_score=round(float(row[C.SELECTION_METRIC]), 6), fit_cutoff_utc=str(cut),
                      training_rows=int(F["y_scaled"].notna().sum()),
                      scale_Wh={s: round(float(v), 6) for s, v in scale.items()},
                      model_file=path.name, model_sha256=sha256_file(path))
    val_preds += [P, baseline_last_week(h, vt), baseline_weekday_hour_median(h, vt),
                  baseline_persistence(h, vt, frames=frames)]
    print(f"{hz}: best = {row['mode']} config {row['config']} {chosen[hz]['params']} "
          f"score {row[C.SELECTION_METRIC]:.4f} (all-16 {row['score_all16']:.4f}, core-8 {row['score_core8']:.4f})")

log = pd.DataFrame(log)
log.to_csv(f"results/task8_tuning_log_{C.TAG}.csv", index=False)
VP = pd.concat(val_preds, ignore_index=True).drop(columns=["input_hour"], errors="ignore")
VP.to_parquet(f"results/task8_validation_predictions_{C.TAG}.parquet", index=False)

meta = json.loads(Path(C.DERIVED_PATH).with_name(Path(C.DERIVED_PATH).stem + "_META.json").read_text())
cfg = dict(
    model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="Fitted on the training circuits' training data only (no refit on train+validation). Chosen on validation "
         f"by {C.SELECTION_METRIC} over the training circuits (DECISIONS_v1.2.md D6). Test not used before freezing.",
    dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION, sha256=sha256_file(C.DERIVED_PATH),
                 source_sha256=meta["source_sha256_file"]),
    series=S_all, training_series=S_train, cold_start_series=sorted(set(S_all) - set(S_train)),
    splits_utc=C.SPLITS, day_ahead_issue=f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", features=FEATURES,
    fixed_params={**C.GBM_FIXED, "random_state": C.SEED}, grid=C.GBM_GRID, modes=C.MODEL_MODES,
    horizons=chosen, versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                                   pandas=pd.__version__, numpy=np.__version__),
)
frozen.write_text(json.dumps(cfg, indent=2))
print(f"wrote {frozen}, tuning log ({len(log)} configs), validation predictions ({len(VP):,} rows)")
