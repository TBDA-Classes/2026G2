"""v1.2 — ChronosGBM hybrid and GBM/Chronos blend: choose on VALIDATION, freeze (DECISIONS_v1.2.md D7, D7b).

    python run_v12_hybrid_tune.py          (after run_v12_chronos_tune.py and run_v12_gbm_tune.py)

Hybrid: the Task 8 GBM with the frozen Chronos forecast as extra inputs (chr_q10/q50/q90/width ÷ circuit scale,
chr_ctx_h). Same grid, fixed parameters, seed and modes as the GBM; fitted on the training circuits' training
rows (target hour < fit cut-off), forecasts for all circuits, selection over the training circuits (D6).

Blend: w × GBM + (1 − w) × Chronos q50 from the two FROZEN models' validation forecasts, w chosen per horizon.

Importance analysis: run_v12_hybrid_importance.py (separate, reads the frozen models).

Never builds test rows. Writes models/hybrid_v1.2_<horizon>.joblib, models/hybrid_frozen_config_v1.2.json,
models/blend_frozen_config_v1.2.json, results/hybrid_tuning_log_v1.2.csv, results/blend_tuning_log_v1.2.csv,
results/hybrid_validation_predictions_v1.2.parquet (hybrid + blend).
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
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import (_series_frames, fit_cutoff, GBMForecaster, predictions_frame, scaled_mae_by_series,
                         series_scale)
from hybrid_model import (CACHE_PATH, CHR_SCALED, HYBRID_FEATURES, load_cache, build_features_hybrid, blend)

ML = "ML_ChronosGBM"
frozen = Path(C.HYBRID_FROZEN_CONFIG)
frozen_blend = Path(f"models/blend_frozen_config_{C.TAG}.json")
for f in (frozen, frozen_blend):
    if f.exists():
        raise SystemExit(f"{f} exists — the configuration is frozen. Delete it deliberately to re-tune.")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
frames = _series_frames(h)
cache = load_cache()
chr_cfg = json.loads(Path(C.CHRONOS_FROZEN_CONFIG).read_text())
gbm_cfg = json.loads(Path(C.FROZEN_CONFIG).read_text())
assert chr_cfg["dataset"]["sha256"] == gbm_cfg["dataset"]["sha256"] == sha256_file(C.DERIVED_PATH)
for hz in C.HORIZONS:                                   # cache was made with the FROZEN Chronos context
    assert (cache.loc[cache["horizon"] == hz, "ctx_len"] == chr_cfg["horizons"][hz]["ctx_len"]).all()

log, chosen, val_preds = [], {}, []
for hz in C.HORIZONS:
    cut = fit_cutoff(h, hz, S_all)
    scale = series_scale(h, cut)
    t = forecast_tasks(h, hz, "train", S_train)
    t = t[t["target_time"] < cut].reset_index(drop=True)
    F = build_features_hybrid(h, t, scale, cache, frames=frames)
    assert (F["target_time"] < cut).all() and (F["split"] == "train").all()
    vt = forecast_tasks(h, hz, "validation", S_all)
    V = build_features_hybrid(h, vt, scale, cache, frames=frames)
    best = None
    for mode in C.MODEL_MODES:
        for i, params in enumerate(C.GBM_GRID):
            m = GBMForecaster(mode, params, S_train, features=HYBRID_FEATURES).fit(F)
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
    path = Path("models") / f"hybrid_{C.TAG}_{hz.replace('+', 'p')}.joblib"
    joblib.dump(m, path)
    chosen[hz] = dict(mode=row["mode"], params={k: row[k] for k in C.GBM_GRID[0]}, config_index=int(row["config"]),
                      validation_score=round(float(row[C.SELECTION_METRIC]), 6), fit_cutoff_utc=str(cut),
                      chronos_ctx_len=chr_cfg["horizons"][hz]["ctx_len"], training_rows=int(F["y_scaled"].notna().sum()),
                      scale_Wh={s: round(float(v), 6) for s, v in scale.items()},
                      model_file=path.name, model_sha256=sha256_file(path))
    val_preds.append(P)
    print(f"{hz}: best = {row['mode']} config {row['config']} {chosen[hz]['params']} "
          f"score {row[C.SELECTION_METRIC]:.4f} (all-16 {row['score_all16']:.4f}, core-8 {row['score_core8']:.4f})")

pd.DataFrame(log).to_csv(f"results/hybrid_tuning_log_{C.TAG}.csv", index=False)
cfg = dict(
    model=ML, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="GBM with the frozen Chronos-Bolt forecast as inputs. Fitted on the training circuits' training data only; "
         f"chosen on validation by {C.SELECTION_METRIC} over the training circuits (DECISIONS_v1.2.md D6, D7). "
         "Test not used before freezing.",
    dataset=gbm_cfg["dataset"], chronos_config=dict(file=Path(C.CHRONOS_FROZEN_CONFIG).name,
                                                    sha256=sha256_file(C.CHRONOS_FROZEN_CONFIG),
                                                    weights_sha256=chr_cfg["weights"]["model_sha256"]),
    chronos_cache=dict(file=CACHE_PATH.name, sha256=sha256_file(CACHE_PATH)),
    series=S_all, training_series=S_train, cold_start_series=sorted(set(S_all) - set(S_train)),
    splits_utc=C.SPLITS, day_ahead_issue=f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", features=HYBRID_FEATURES,
    fixed_params={**C.GBM_FIXED, "random_state": C.SEED}, grid=C.GBM_GRID, modes=C.MODEL_MODES, horizons=chosen,
    versions=dict(python=platform.python_version(), sklearn=sklearn.__version__, pandas=pd.__version__,
                  numpy=np.__version__),
)
frozen.write_text(json.dumps(cfg, indent=2))

# ---- blend of the two frozen models (D7b)
gv = pd.read_parquet(f"results/task8_validation_predictions_{C.TAG}.parquet")
gv = gv[gv["model"] == "ML_GBM"]
cv = pd.read_parquet(f"results/chronos_validation_predictions_{C.TAG}.parquet")
blog, bchosen = [], {}
for hz in C.HORIZONS:
    scale = pd.Series(gbm_cfg["horizons"][hz]["scale_Wh"])
    best = None
    for w in C.BLEND_WEIGHTS:
        B = blend(gv[gv["horizon"] == hz], cv[cv["horizon"] == hz], w)
        per = scaled_mae_by_series(B, scale)
        r = dict(horizon=hz, w_gbm=w, **{C.SELECTION_METRIC: per.reindex(S_train).mean()},
                 score_all16=per.mean(), score_core8=per.reindex(C.CORE_8).mean())
        blog.append(r)
        if best is None or r[C.SELECTION_METRIC] < best[0][C.SELECTION_METRIC]:
            best = (r, B)
    bchosen[hz] = dict(w_gbm=best[0]["w_gbm"], validation_score=round(float(best[0][C.SELECTION_METRIC]), 6))
    val_preds.append(best[1].assign(model="ML_Blend"))
    print(f"{hz}: blend w_gbm = {best[0]['w_gbm']}  score {best[0][C.SELECTION_METRIC]:.4f}")
pd.DataFrame(blog).to_csv(f"results/blend_tuning_log_{C.TAG}.csv", index=False)
frozen_blend.write_text(json.dumps(dict(
    model="ML_Blend", created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="w × frozen GBM + (1 − w) × frozen Chronos median; w chosen per horizon on validation (D7b).",
    weights=C.BLEND_WEIGHTS, gbm_config=sha256_file(C.FROZEN_CONFIG), chronos_config=sha256_file(C.CHRONOS_FROZEN_CONFIG),
    horizons=bchosen), indent=2))
VP = pd.concat(val_preds, ignore_index=True)
VP[["series_id", "issue_time", "target_time", "lead", "horizon", "split", "y_true", "y_pred", "model"]].to_parquet(
    f"results/hybrid_validation_predictions_{C.TAG}.parquet", index=False)

print(f"wrote {frozen}, {frozen_blend}, validation predictions ({len(VP):,} rows)")
