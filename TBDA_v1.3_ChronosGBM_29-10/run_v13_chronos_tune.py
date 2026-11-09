"""v1.3 — Chronos-Bolt, extended grid: 4 sizes x 13 context lengths x 2 point forecasts = 104 combinations.
Chosen on VALIDATION with rule D10, frozen, then the hybrid cache is built with the frozen choice.

    python run_v13_chronos_tune.py
    python run_v13_chronos_tune.py --sizes small          # code check with one size (writes to results/smoke/)

Needs the weights of every size in weights/chronos-bolt-<size>/ (README_v1.3.md, step 3). Zero-shot: nothing is
fitted on our data. Run this BEFORE run_v13_hybrid_tune.py (the hybrid uses the frozen Chronos as inputs).

Writes models/chronos_frozen_config_v1.3.json, results/chronos_tuning_log_v1.3.csv,
results/chronos_validation_predictions_v1.3.parquet, results/chronos_context_quality_v1.3.csv and
results/chronos_cache_v1.3.parquet (frozen choice per horizon, TRAIN + VALIDATION issue times, no test).
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config as C
import chronos_model as CM
import chronos_v13 as CV
from selection import (scaled_scores, d10_choose, require_d10_agreed, baseline_preds, baseline_reference,
                       add_baseline_columns)
from task7_pipeline import sha256_file
from task7_baselines import load_derived, forecast_tasks, eligible_series
from task8_model import fit_cutoff, series_scale

ap = argparse.ArgumentParser()
ap.add_argument("--sizes", nargs="+", default=None, help="subset of sizes = smoke run (results/smoke/)")
args = ap.parse_args()
smoke = args.sizes is not None
SIZES = args.sizes or C.CHRONOS_SIZES_V13
OUT_R, OUT_M = (Path("results/smoke"), Path("results/smoke")) if smoke else (Path("results"), Path("models"))
OUT_R.mkdir(parents=True, exist_ok=True)
FROZEN = OUT_M / Path(C.FROZEN_V13["chronos"]).name
CACHE = OUT_R / Path(C.CHRONOS_CACHE_V13).name
if not smoke:
    require_d10_agreed()
if FROZEN.exists():
    raise SystemExit(f"{FROZEN} exists — the configuration is frozen. Delete it deliberately to re-tune.")
missing = [s for s in SIZES if not (CV.weights_dir(s) / "model.safetensors").exists()]
if missing:
    raise SystemExit(f"weights missing for {missing}: see README_v1.3.md step 3")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
grids = CM.series_grid(h)
tasks = {hz: forecast_tasks(h, hz, "validation", S_all) for hz in C.HORIZONS}
assert all((t["split"] == "validation").all() for t in tasks.values())
scales = {hz: series_scale(h, fit_cutoff(h, hz, S_all)) for hz in C.HORIZONS}
allt = pd.concat(tasks.values(), ignore_index=True)
refs = {hz: baseline_reference(baseline_preds(h, tasks[hz]), scales[hz], S_train, hz) for hz in C.HORIZONS}

log, preds, quality, weights = [], {}, [], {}
for size in SIZES:
    wd = CV.weights_dir(size)
    weights[size] = dict(model_sha256=CM.sha256(wd / "model.safetensors"), config_sha256=CM.sha256(wd / "config.json"))
    pipe = CM.load_pipeline(wd)
    for L in C.CTX_GRID_V13:
        t0 = time.time()
        P9 = CV.forecasts9(pipe, h, allt, L, grids=grids)
        for point in C.CHRONOS_POINTS_V13:
            P = CV.with_point(P9, point, size)
            for hz in C.HORIZONS:
                Ph = P[P["horizon"] == hz]
                s = scaled_scores(Ph, scales[hz], S_train)
                preds[(hz, size, L, point)] = Ph
                log.append(dict(horizon=hz, size=size, ctx_len=L, point=point,
                                **{k: v for k, v in s.items() if not k.startswith("per_series")},
                                **{f"sMAE_{k}": v for k, v in s["per_series_MAE"].items()}))
        calls = P9.drop_duplicates(["series_id", "issue_time"])
        q = calls.groupby("series_id").agg(calls=("issue_time", "size"),
                                           no_valid_context=("ctx_valid_h", lambda x: int((x == 0).sum())),
                                           under_50pct_valid=("ctx_valid_h", lambda x: int((x < 0.5 * L).sum())),
                                           mean_valid_share=("ctx_valid_h", lambda x: float((x / L).mean())))
        quality.append(q.assign(size=size, ctx_len=L).reset_index())
        print(f"{size} ctx {L}: {time.time() - t0:.0f}s")
    del pipe

log = pd.DataFrame(log)
chosen = {}
parts = []
for hz in C.HORIZONS:
    hl = log[log["horizon"] == hz].reset_index(drop=True)
    j, hl = d10_choose(hl)
    hl = add_baseline_columns(hl, *refs[hz])
    parts.append(hl)
    r = hl.loc[j]
    chosen[hz] = dict(size=r["size"], ctx_len=int(r["ctx_len"]), point=r["point"],
                      validation_score=round(float(r["mean_scaled_MAE"]), 6),
                      validation_scaled_RMSE=round(float(r["mean_scaled_RMSE"]), 6),
                      best_baseline=refs[hz][0]["best_baseline"],
                      best_baseline_score=round(refs[hz][0]["best_baseline_MAE"], 6),
                      n_tied=int(hl["d10_tied"].sum()), best_score=round(float(hl["mean_scaled_MAE"].min()), 6),
                      scale_Wh=scales[hz].round(6).to_dict())
    print(f"{hz}: D10 chose {r['size']}, ctx {int(r['ctx_len'])} h, {r['point']}  score {r['mean_scaled_MAE']:.4f} "
          f"({chosen[hz]['n_tied']} tied); best baseline {refs[hz][0]['best_baseline']} "
          f"{refs[hz][0]['best_baseline_MAE']:.4f}; {int(hl['clearly_beats_best_baseline'].sum())}/{len(hl)} clearly better")
log = pd.concat(parts, ignore_index=True)
log.to_csv(OUT_R / f"chronos_tuning_log_{C.TAG13}.csv", index=False)
pd.concat(quality).to_csv(OUT_R / f"chronos_context_quality_{C.TAG13}.csv", index=False)

import chronos, torch, transformers
cfg = dict(
    model=CM.MODEL, grid_version=C.TAG13, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="Zero-shot: nothing fitted on our data. Size, context length and point forecast chosen on validation by "
         f"rule D10 (tie margin {C.D10_TIE_MARGIN}, tie-break mean scaled RMSE). Test not used before freezing.",
    d10_agreed=C.D10_AGREED, weights=weights,
    dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION, sha256=sha256_file(C.DERIVED_PATH)),
    series=S_all, selection_series=S_train, splits_utc=C.SPLITS, day_ahead_issue="00:00 Europe/Madrid",
    quantiles_read=CV.Q9, prediction_length=CM.PRED_LEN, clip="forecasts clipped at 0",
    grid=dict(sizes=SIZES, ctx_len=C.CTX_GRID_V13, point=C.CHRONOS_POINTS_V13),
    n_combinations=len(SIZES) * len(C.CTX_GRID_V13) * len(C.CHRONOS_POINTS_V13), horizons=chosen,
    versions=dict(python=platform.python_version(), chronos=getattr(chronos, "__version__", "n/a"),
                  torch=torch.__version__, transformers=transformers.__version__, pandas=pd.__version__),
)
FROZEN.write_text(json.dumps(cfg, indent=2))
VP = pd.concat([preds[(hz, c["size"], c["ctx_len"], c["point"])] for hz, c in chosen.items()], ignore_index=True)
VP.to_parquet(OUT_R / f"chronos_validation_predictions_{C.TAG13}.parquet", index=False)

# ---- cache for the hybrid: frozen (size, context) per horizon, TRAIN + VALIDATION issue times, all circuits
parts = []
for hz, c in chosen.items():
    pipe = CM.load_pipeline(CV.weights_dir(c["size"]))
    for split in ["train", "validation"]:
        if split == "validation":
            P = preds[(hz, c["size"], c["ctx_len"], c["point"])]
        else:
            t0 = time.time()
            P = CV.forecasts9(pipe, h, forecast_tasks(h, hz, split, S_all), c["ctx_len"], grids=grids)
            print(f"cache {hz} {split}: {len(P):,} rows, {time.time() - t0:.0f}s")
        parts.append(P.assign(size=c["size"]))
    del pipe
cache = pd.concat(parts, ignore_index=True)
assert not cache["split"].isin(["test", "outside"]).any(), "cache must not contain test issue times"
assert cache.duplicated(["series_id", "horizon", "issue_time", "lead"]).sum() == 0
cache = cache[["series_id", "horizon", "issue_time", "target_time", "lead", "split", "q10", "q50", "q90",
               "pred_median", "pred_mean_q", "size", "ctx_len", "ctx_valid_h", "ctx_avail_h"]]
cache.to_parquet(CACHE, index=False)
print(f"wrote {FROZEN}, {CACHE}: {len(cache):,} rows; sha256 {sha256_file(CACHE)[:16]}…")
