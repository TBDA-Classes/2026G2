"""v1.3 — ChronosGBM hybrid, extended grid (128 combinations), chosen on VALIDATION with rule D10, frozen.

    python run_v13_hybrid_tune.py              (after run_v13_chronos_tune.py)
    python run_v13_hybrid_tune.py --smoke      (2 configurations, uses results/smoke/ cache if no v1.3 cache)

Same as run_v12_hybrid_tune.py (inputs D7, training rows, fit cut-off, seed) except: grid GBM_GRID_V13, pooled
mode only, Chronos inputs from the FROZEN v1.3 Chronos (results/chronos_cache_v1.3.parquet), choice by D10.
The blend is a separate script in v1.3 (run_v13_blend_tune.py). Never builds test rows.

Writes models/hybrid_v1.3_<horizon>.joblib, models/hybrid_frozen_config_v1.3.json,
results/hybrid_tuning_log_v1.3.csv, results/hybrid_validation_predictions_v1.3.parquet.
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
                       add_baseline_columns)
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import _series_frames, fit_cutoff, GBMForecaster, predictions_frame, series_scale
from hybrid_model import HYBRID_FEATURES, load_cache, build_features_hybrid

ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()

ML = "ML_ChronosGBM"
GRID = C.GBM_GRID_V13[:2] if args.smoke else C.GBM_GRID_V13
OUT_R, OUT_M = (Path("results/smoke"), Path("results/smoke")) if args.smoke else (Path("results"), Path("models"))
OUT_R.mkdir(parents=True, exist_ok=True)
frozen = OUT_M / Path(C.FROZEN_V13["hybrid"]).name
chr_frozen = OUT_M / Path(C.FROZEN_V13["chronos"]).name
cache_path = OUT_R / Path(C.CHRONOS_CACHE_V13).name
if not args.smoke:
    require_d10_agreed()
if frozen.exists():
    raise SystemExit(f"{frozen} exists — the configuration is frozen. Delete it deliberately to re-tune.")
if not chr_frozen.exists() or not cache_path.exists():
    raise SystemExit(f"run run_v13_chronos_tune.py first ({chr_frozen} / {cache_path} missing)")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
frames = _series_frames(h)
cache = load_cache(cache_path)
chr_cfg = json.loads(chr_frozen.read_text())
assert chr_cfg["dataset"]["sha256"] == sha256_file(C.DERIVED_PATH)
for hz, c in chr_cfg["horizons"].items():            # cache was made with the FROZEN Chronos choice
    ch = cache[cache["horizon"] == hz]
    assert (ch["ctx_len"] == c["ctx_len"]).all() and (ch["size"] == c["size"]).all(), f"cache does not match {hz}"

log, chosen, val_preds = [], {}, []
for hz in C.HORIZONS:
    t0 = time.time()
    cut = fit_cutoff(h, hz, S_all)
    scale = series_scale(h, cut)
    t = forecast_tasks(h, hz, "train", S_train)
    t = t[t["target_time"] < cut].reset_index(drop=True)
    F = build_features_hybrid(h, t, scale, cache, frames=frames)
    assert (F["target_time"] < cut).all() and (F["split"] == "train").all()
    vt = forecast_tasks(h, hz, "validation", S_all)
    V = build_features_hybrid(h, vt, scale, cache, frames=frames)
    ref, ref_tab = baseline_reference(baseline_preds(h, vt, frames=frames), scale, S_train, hz)
    rows, models, preds = [], [], []
    for i, params in enumerate(GRID):
        m = GBMForecaster(C.GBM_MODE_V13, params, S_train, features=HYBRID_FEATURES).fit(F)
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
    path = OUT_M / f"hybrid_{C.TAG13}_{hz.replace('+', 'p')}.joblib"
    joblib.dump(m, path)
    chosen[hz] = dict(mode=C.GBM_MODE_V13,
                      params={k: (int(row[k]) if k in ("max_leaf_nodes", "min_samples_leaf") else float(row[k]))
                              for k in GRID[0]},
                      config_index=int(row["config"]), validation_score=round(float(row["mean_scaled_MAE"]), 6),
                      validation_scaled_RMSE=round(float(row["mean_scaled_RMSE"]), 6),
                      best_baseline=ref["best_baseline"], best_baseline_score=round(ref["best_baseline_MAE"], 6),
                      n_tied=int(hlog["d10_tied"].sum()), best_score=round(float(hlog["mean_scaled_MAE"].min()), 6),
                      fit_cutoff_utc=str(cut), chronos=dict(size=chr_cfg["horizons"][hz]["size"],
                                                            ctx_len=chr_cfg["horizons"][hz]["ctx_len"]),
                      training_rows=int(F["y_scaled"].notna().sum()),
                      scale_Wh={s: round(float(v), 6) for s, v in scale.items()},
                      model_file=path.name, model_sha256=sha256_file(path))
    val_preds.append(P)
    print(f"{hz}: {len(GRID)} fits in {time.time() - t0:.0f}s; D10 chose config {int(row['config'])} "
          f"{chosen[hz]['params']} score {row['mean_scaled_MAE']:.4f} ({chosen[hz]['n_tied']} tied); "
          f"best baseline {ref['best_baseline']} {ref['best_baseline_MAE']:.4f}; "
          f"{int(hlog['clearly_beats_best_baseline'].sum())}/{len(hlog)} configs clearly better")

pd.concat(log, ignore_index=True).to_csv(OUT_R / f"hybrid_tuning_log_{C.TAG13}.csv", index=False)
cfg = dict(
    model=ML, grid_version=C.TAG13, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="GBM with the frozen v1.3 Chronos-Bolt forecast as inputs (q10, q50, q90 whatever point forecast Chronos "
         "froze). Fitted on the training circuits' training data only; chosen on validation by rule D10. "
         "Test not used before freezing.",
    d10_agreed=C.D10_AGREED,
    dataset=chr_cfg["dataset"], chronos_config=dict(file=chr_frozen.name, sha256=sha256_file(chr_frozen)),
    chronos_cache=dict(file=cache_path.name, sha256=sha256_file(cache_path)),
    series=S_all, training_series=S_train, cold_start_series=sorted(set(S_all) - set(S_train)),
    splits_utc=C.SPLITS, day_ahead_issue=f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", features=HYBRID_FEATURES,
    fixed_params={k: v for k, v in {**C.GBM_FIXED, "random_state": C.SEED}.items() if k not in GRID[0]},
    grid=GRID, n_combinations=len(GRID), mode=C.GBM_MODE_V13, horizons=chosen,
    versions=dict(python=platform.python_version(), sklearn=sklearn.__version__, pandas=pd.__version__,
                  numpy=np.__version__),
)
frozen.write_text(json.dumps(cfg, indent=2))
VP = pd.concat(val_preds, ignore_index=True)
VP[["series_id", "issue_time", "target_time", "lead", "horizon", "split", "y_true", "y_pred", "model"]].to_parquet(
    OUT_R / f"hybrid_validation_predictions_{C.TAG13}.parquet", index=False)
print(f"wrote {frozen}, validation predictions ({len(VP):,} rows)")
