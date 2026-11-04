"""Task 6 — validation forecasts of GBM v1.0, Linear Regression (rebuilt) and Random Forest (dataset v1.1).

Run inside the Task78_rev0_19-10 folder after task6_linear_rebuild.py:
    python3 run_task6_v11_validation.py
"""
import sys, json, joblib, numpy as np, pandas as pd, os
sys.path.insert(0, '../Task6_rev0_03-11'); import minipq
pd.read_parquet = lambda p, **k: minipq.read_parquet(p)
import config as C
from task7_baselines import load_derived, forecast_tasks
from task8_model import _series_frames, build_features, predictions_frame
MAP = {"B1_last_week_v1.2": "B1_last_week", "B2_weekday_hour_median_v1.2": "B2_weekday_hour_median",
       "B3_persistence_v1.2": "B3_persistence", "GBM": "ML_GBM_v1.0", "GBM_v1.3": "ML_GBM_v1.3", "linear_regression": "ML_Linear",
       "RandomForest": "ML_RandomForest", "Chronos_v1.3": "ML_Chronos_v1.3", "ChronosGBM_v1.3": "ML_ChronosGBM_v1.3",
       "Blend_v1.3": "ML_Blend_v1.3"}   # file / model names used in Task6_rev0_03-11
OUTDIR = os.environ.get("TASK6_PRED_DIR", "../Task6_rev0_03-11/results/predictions")
h = load_derived(); fr = _series_frames(h)
cfg = json.load(open(C.FROZEN_CONFIG)); out = []
for hz, c in cfg["horizons"].items():
    m = joblib.load("models/" + c["model_file"]); sc = pd.Series(c["scale_Wh"])
    T = build_features(h, forecast_tasks(h, hz, "validation", cfg["series"]), sc, frames=fr)
    out.append(predictions_frame(T, m.predict(T), "GBM"))
L = pd.read_pickle("results/task6_linear_rebuild.pkl"); out.append(L[L.split == "validation"])
R = minipq.read_parquet("results/task1_rf_final_validation_predictions.parquet")      # from the Random Forest package
out.append(R.assign(model="RandomForest"))
P = pd.concat(out, ignore_index=True)
P["horizon_h"] = P.horizon.map({"+1h": 1, "+6h": 6, "day-ahead": 24}); P["zone"] = P.series_id; P["circuit_zone"] = P.series_id.str.split("|").str[0]
d = OUTDIR; os.makedirs(d, exist_ok=True)
for mname, g in P.groupby("model"):
    g = g.rename(columns={"target_time": "target_hour", "y_true": "actual_Wh", "y_pred": "predicted_Wh", "lead": "lead_h"})
    g = g.assign(model=MAP[mname])
    g[["model","zone","circuit_zone","horizon_h","target_hour","actual_Wh","predicted_Wh","lead_h","issue_time"]].to_csv(f"{d}/{MAP[mname]}_validation_predictions.csv", index=False)
    print(mname, len(g), g.actual_Wh.notna().sum(), g.zone.nunique())
# official validation scores: GBM (frozen cfg), linear 16 (0.340/0.392/0.395)
for hz, c in cfg["horizons"].items():
    sc = pd.Series(c["scale_Wh"])
    for mname, S in [("GBM", cfg["series"])]:
        k = P[(P.model == mname) & (P.horizon == hz) & P.y_true.notna()]
        print(hz, mname, round(((k.y_true - k.y_pred).abs().groupby(k.series_id).mean() / sc).mean(), 6), "official", c.get("validation_score"))
