"""Task 6 — forecasts of Chronos v1.3, ChronosGBM v1.3, Blend v1.3, GBM v1.3 and B1-B3 (dataset v1.2) from the FROZEN models.

Run inside the TBDA_v1.3 folder (next to config.py, task8_model.py, hybrid_model.py, models/):
    python3 run_task6_v13_predictions.py validation                                     # results/chronos_cache_v1.3.parquet
    python3 run_task6_v13_predictions.py test results/chronos_cache_v1.3_test.parquet   # cache with the test rows (Emily, 3 Nov)
Nothing is fitted or tuned. Blend weights from models/blend_frozen_config_v1.3.json.
No pyarrow in our environment: minipq.py (in Task6_rev0_03-11) reads the parquet files; with pyarrow, delete the two lines.
"""
import sys, json, joblib, os, numpy as np, pandas as pd
sys.path.insert(0, '../Task6_rev0_03-11'); import minipq
pd.read_parquet = lambda p, **k: minipq.read_parquet(p)
import config as C
from task7_baselines import load_derived, forecast_tasks, baseline_last_week, baseline_weekday_hour_median
from task8_model import _series_frames, build_features, baseline_persistence, predictions_frame
from hybrid_model import load_cache, build_features_hybrid
MAP = {"B1_last_week_v1.2": "B1_last_week", "B2_weekday_hour_median_v1.2": "B2_weekday_hour_median",
       "B3_persistence_v1.2": "B3_persistence", "GBM": "ML_GBM_v1.0", "GBM_v1.3": "ML_GBM_v1.3", "linear_regression": "ML_Linear",
       "RandomForest": "ML_RandomForest", "Chronos_v1.3": "ML_Chronos_v1.3", "ChronosGBM_v1.3": "ML_ChronosGBM_v1.3",
       "Blend_v1.3": "ML_Blend_v1.3"}   # file / model names used in Task6_rev0_03-11
OUTDIR = os.environ.get("TASK6_PRED_DIR", "../Task6_rev0_03-11/results/predictions")
split = sys.argv[1]; cache_path = sys.argv[2] if len(sys.argv) > 2 else C.CHRONOS_CACHE_V13
h = load_derived(); fr = _series_frames(h)
gc = json.load(open(C.FROZEN_V13["task8"])); hc = json.load(open(C.FROZEN_V13["hybrid"]))
cc = json.load(open(C.FROZEN_V13["chronos"])); bc = json.load(open(C.FROZEN_V13["blend"]))
cache = load_cache(cache_path, allow_test=(split == "test"))
ALL = hc["series"]; out = []
for hz in C.HORIZONS:
    ch = cc["horizons"][hz]
    cz = cache[(cache.horizon == hz) & (cache["size"] == ch["size"]) & (cache.ctx_len == ch["ctx_len"])]
    t = forecast_tasks(h, hz, split, ALL)
    G = build_features(h, t, pd.Series(gc["horizons"][hz]["scale_Wh"]), frames=fr)
    pg = joblib.load("models/" + gc["horizons"][hz]["model_file"]).predict(G)
    F = build_features_hybrid(h, t, pd.Series(hc["horizons"][hz].get("scale_Wh") or gc["horizons"][hz]["scale_Wh"]), cz, frames=fr)
    assert (F[["series_id", "target_time"]].values == G[["series_id", "target_time"]].values).all()
    ph = joblib.load("models/" + hc["horizons"][hz]["model_file"]).predict(F)
    col = "pred_median" if ch["point"] == "median" else "pred_mean_q"
    pc = np.clip(F.merge(cz[["series_id", "horizon", "issue_time", "lead", col]], on=["series_id", "horizon", "issue_time", "lead"], how="left")[col].to_numpy(), 0, None)
    w = bc["horizons"][hz]; pb = w["w_gbm"] * pg + w["w_hybrid"] * ph + w["w_chronos"] * pc
    for name, p in [("GBM_v1.3", pg), ("ChronosGBM_v1.3", ph), ("Chronos_v1.3", pc), ("Blend_v1.3", pb)]:
        out.append(predictions_frame(G, p, name))
    for name, P in [("B1_last_week_v1.2", baseline_last_week(h, t)), ("B2_weekday_hour_median_v1.2", baseline_weekday_hour_median(h, t)),
                    ("B3_persistence_v1.2", baseline_persistence(h, t, frames=fr))]:
        out.append(P.assign(model=name))
P = pd.concat(out, ignore_index=True)
P["horizon_h"] = P.horizon.map({"+1h": 1, "+6h": 6, "day-ahead": 24}); P["zone"] = P.series_id; P["circuit_zone"] = P.series_id.str.split("|").str[0]
d = OUTDIR; os.makedirs(d, exist_ok=True)
for mname, g in P.groupby("model"):
    g = g.rename(columns={"target_time": "target_hour", "y_true": "actual_Wh", "y_pred": "predicted_Wh", "lead": "lead_h"})
    g = g.assign(model=MAP[mname])
    g[["model","zone","circuit_zone","horizon_h","target_hour","actual_Wh","predicted_Wh","lead_h","issue_time"]].to_csv(f"{d}/{MAP[mname]}_{split}_predictions.csv", index=False)
    print(mname, len(g), g.actual_Wh.notna().sum(), g.predicted_Wh.notna().sum())
# check against the official validation scores (15 training circuits, GBM scale)
if split == "validation":
    TR = hc["training_series"]
    for hz in C.HORIZONS:
        sc = pd.Series(gc["horizons"][hz]["scale_Wh"]); row = [hz]
        for name, ref in [("GBM_v1.3", gc["horizons"][hz]["validation_score"]), ("Chronos_v1.3", cc["horizons"][hz]["validation_score"]),
                          ("ChronosGBM_v1.3", hc["horizons"][hz]["validation_score"]), ("Blend_v1.3", bc["horizons"][hz]["validation_score"])]:
            k = P[(P.model == name) & (P.horizon == hz) & P.y_true.notna() & P.series_id.isin(TR)]
            row.append(f"{name} {((k.y_true-k.y_pred).abs().groupby(k.series_id).mean()/sc).loc[TR].mean():.4f}/{ref:.4f}")
        print(*row)
