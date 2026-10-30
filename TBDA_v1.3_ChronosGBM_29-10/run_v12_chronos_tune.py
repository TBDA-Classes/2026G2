"""v1.2 — Chronos-Bolt on all 16 circuits: choose the context length on VALIDATION, freeze, then cache forecasts.

    python run_v12_chronos_tune.py

1. Validation forecasts for every context length in CTX_GRID, all 16 circuits (D5: every circuit is forecast).
2. Selection (D6): per horizon, lowest mean over the TRAINING circuits (S10 v1.2 `in_training`) of
   validation MAE / circuit training mean. Cold-start circuits are forecast but do not select.
3. Freeze -> models/chronos_frozen_config_v1.2.json (refuses to overwrite).
4. Cache (procedure P3.4): with the frozen context per horizon, forecasts for every TRAIN and VALIDATION issue
   time of all 16 circuits -> results/chronos_cache_v1.2.parquet. These are the hybrid's Chronos inputs.
   Test issue times are NOT generated here (point 8).

Also writes results/chronos_tuning_log_v1.2.csv, results/chronos_validation_predictions_v1.2.parquet and
results/chronos_context_quality_v1.2.csv (forecasts with no valid context hour, or < 50 % valid context hours).
"""
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import chronos_model as CM
from task7_pipeline import sha256_file
from task7_baselines import load_derived, forecast_tasks, eligible_series
from task8_model import fit_cutoff, series_scale, scaled_mae_by_series

FROZEN = Path(C.CHRONOS_FROZEN_CONFIG)
CACHE = Path(f"results/chronos_cache_{C.TAG}.parquet")
if FROZEN.exists():
    raise SystemExit(f"{FROZEN} exists — the configuration is frozen. Delete it deliberately to re-tune.")

h = load_derived(C.DERIVED_PATH)
S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
print(f"{len(S_all)} circuits forecast, {len(S_train)} select; cold-start: {sorted(set(S_all) - set(S_train))}")
grids = CM.series_grid(h)
pipe = CM.load_pipeline()
assert CM.sha256(CM.WEIGHTS_DIR / "model.safetensors") == json.loads(
    Path("models/chronos_frozen_config.json").read_text())["weights"]["model_sha256"], "different Chronos weights"

tasks = {hz: forecast_tasks(h, hz, "validation", S_all) for hz in C.HORIZONS}
assert all((t["split"] == "validation").all() for t in tasks.values())
# scale = circuit training mean (fitted quantity, train only), same cut-off rule as Task 8
scales = {hz: series_scale(h, fit_cutoff(h, hz, S_all)) for hz in C.HORIZONS}
allt = pd.concat(tasks.values(), ignore_index=True)

log, preds, quality = [], {}, []
for L in CM.CTX_GRID:
    t0 = time.time()
    P = CM.chronos_forecasts(pipe, h, allt, L, grids=grids)
    for hz in C.HORIZONS:
        Ph = P[P["horizon"] == hz]
        per = scaled_mae_by_series(Ph, scales[hz])
        preds[(hz, L)] = Ph
        sel = per.reindex(S_train)
        log.append(dict(horizon=hz, ctx_len=L, score=sel.mean(), score_all16=per.mean(),
                        score_core8=per.reindex(C.CORE_8).mean(), n_select=int(sel.notna().sum()),
                        **{f"scaled_MAE|{s}": v for s, v in per.items()}))
    calls = P.drop_duplicates(["series_id", "issue_time"])
    q = calls.groupby("series_id").agg(calls=("issue_time", "size"),
                                       no_valid_context=("ctx_valid_h", lambda x: int((x == 0).sum())),
                                       under_50pct_valid=("ctx_valid_h", lambda x: int((x < 0.5 * L).sum())),
                                       mean_valid_share=("ctx_valid_h", lambda x: float((x / L).mean())))
    quality.append(q.assign(ctx_len=L).reset_index())
    print(f"ctx {L}: {time.time() - t0:.0f}s  " + "  ".join(f"{r['horizon']} {r['score']:.4f}" for r in log[-3:]))

log = pd.DataFrame(log)
log.to_csv(f"results/chronos_tuning_log_{C.TAG}.csv", index=False)
pd.concat(quality).to_csv(f"results/chronos_context_quality_{C.TAG}.csv", index=False)
best = log.loc[log.groupby("horizon")["score"].idxmin()].set_index("horizon")

import chronos, torch, transformers
cfg = dict(
    model=CM.MODEL, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="Zero-shot: nothing fitted on our data. Context length chosen on validation by mean_scaled_MAE over the "
         "training circuits (DECISIONS_v1.2.md D6). All circuits are forecast. Test not used before freezing.",
    weights=dict(name="chronos-bolt-small (config _name_or_path: autogluon/chronos-bolt-small)",
                 model_sha256=CM.sha256(CM.WEIGHTS_DIR / "model.safetensors"),
                 config_sha256=CM.sha256(CM.WEIGHTS_DIR / "config.json")),
    dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION, sha256=sha256_file(C.DERIVED_PATH)),
    series=S_all, selection_series=S_train, splits_utc=C.SPLITS, day_ahead_issue="00:00 Europe/Madrid",
    point_forecast="median (0.5 quantile), clipped at 0", quantiles=CM.QUANTILES, prediction_length=CM.PRED_LEN,
    ctx_grid=CM.CTX_GRID,
    horizons={hz: dict(ctx_len=int(best.loc[hz, "ctx_len"]), validation_score=round(float(best.loc[hz, "score"]), 6),
                       scale_Wh=scales[hz].round(6).to_dict()) for hz in C.HORIZONS},
    versions=dict(python=platform.python_version(), chronos=getattr(chronos, "__version__", "n/a"),
                  torch=torch.__version__, transformers=transformers.__version__, pandas=pd.__version__),
)
FROZEN.write_text(json.dumps(cfg, indent=2))
VP = pd.concat([preds[(hz, cfg["horizons"][hz]["ctx_len"])] for hz in C.HORIZONS], ignore_index=True)
VP.to_parquet(f"results/chronos_validation_predictions_{C.TAG}.parquet", index=False)
pd.set_option("display.width", 200)
print(log.pivot(index="ctx_len", columns="horizon", values="score").round(4))
print("frozen:", {hz: v["ctx_len"] for hz, v in cfg["horizons"].items()})

# ---- cache for the hybrid: frozen context per horizon, TRAIN + VALIDATION issue times, all circuits
parts = []
for hz in C.HORIZONS:
    L = cfg["horizons"][hz]["ctx_len"]
    for split in ["train", "validation"]:
        t = forecast_tasks(h, hz, split, S_all)
        if split == "validation":
            P = preds[(hz, L)]                                       # identical calls, reuse
        else:
            t0 = time.time()
            P = CM.chronos_forecasts(pipe, h, t, L, grids=grids)
            print(f"cache {hz} {split}: {len(P):,} rows, {time.time() - t0:.0f}s")
        parts.append(P)
cache = pd.concat(parts, ignore_index=True)
assert not cache["split"].isin(["test", "outside"]).any(), "cache must not contain test issue times"
assert cache.duplicated(["series_id", "horizon", "issue_time", "lead"]).sum() == 0
cache = cache.rename(columns={"y_pred": "q50"})[
    ["series_id", "horizon", "issue_time", "target_time", "lead", "split", "q10", "q50", "q90", "ctx_len",
     "ctx_valid_h", "ctx_avail_h"]]
cache.to_parquet(CACHE, index=False)
print(f"wrote {CACHE}: {len(cache):,} rows; sha256 {sha256_file(CACHE)[:16]}…")
