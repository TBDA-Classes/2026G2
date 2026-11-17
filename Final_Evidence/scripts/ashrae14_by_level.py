# -*- coding: utf-8 -*-
"""
ASHRAE Guideline 14 style check of Blend v1.3, by level (circuit, load type, zone, building).

Authors: Jules (main author), Claude (co-author).

Scored hours: EXACTLY the Task 6 common hours (inner join of every model's prediction file,
hours with a valid measurement) -> 1,911 circuit-hours per horizon on the test week.
Zone / building totals use only the hours where every circuit of that zone / building is in the mask.

Run from the repository root:
    python Final_Evidence/scripts/ashrae14_by_level.py
Outputs: Final_Evidence/analysis/ashrae14_by_level_{test,validation}.csv
"""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRED = ROOT / "Task6_rev0_03-11" / "results" / "predictions"
OUT = ROOT / "Final_Evidence" / "analysis"
H = {1: "+1h", 6: "+6h", 24: "day-ahead"}
MODEL = "ML_Blend_v1.3"
LOAD = {"HVAC": "HVAC", "Plugs & Sockets": "Plugs & Sockets", "Lighting": "Lighting",
        "Emerg. Lighting": "Emergency lighting", "RACK": "Rack (constant)", "Hand Dryer": "Hand dryer"}


M16 = ["ML_RandomForest", "ML_Linear", "ML_GBM_v1.3", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3",
       "ML_Blend_v1.3", "B1_last_week", "B2_weekday_hour_median", "B3_persistence"]   # same list as Task6 run_task6_all.sh


def load(split):
    """Normalise like task6_compare.py (circuit = column containing '|'), keep the hours valid for all 9 models."""
    frames = {}
    for m in M16:
        d = pd.read_csv(PRED / f"{m}_{split}_predictions.csv")
        circ = d["zone"] if d["zone"].astype(str).str.contains(r"\|").all() else d["circuit_zone"]
        d = pd.DataFrame({"zone": circ.astype(str), "horizon_h": d["horizon_h"].astype(int),
                          "target_hour": pd.to_datetime(d["target_hour"], utc=True),
                          "actual_Wh": pd.to_numeric(d["actual_Wh"], errors="coerce"),
                          "predicted_Wh": pd.to_numeric(d["predicted_Wh"], errors="coerce")})
        d = d.dropna(subset=["actual_Wh", "predicted_Wh"]).set_index(["zone", "horizon_h", "target_hour"])
        frames[m] = d
    keys = None
    for d in frames.values():
        k = set(d.index)
        keys = k if keys is None else keys & k
    return frames, keys


def metrics(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    n, m = len(a), a.mean()
    if n == 0 or m == 0:
        return dict(n=n, mean_Wh=m, MAE_Wh=np.nan, CV_RMSE_pct=np.nan, NMBE_ashrae_pct=np.nan, NMBE_forecast_minus_actual_pct=np.nan)
    e = p - a
    return dict(n=n, mean_Wh=round(m, 2), MAE_Wh=round(np.abs(e).mean(), 2),
                CV_RMSE_pct=round(100 * np.sqrt((e ** 2).mean()) / m, 1),
                NMBE_ashrae_pct=round(-100 * e.sum() / a.sum(), 1),          # ASHRAE: (measured - predicted)
                NMBE_forecast_minus_actual_pct=round(100 * e.sum() / a.sum(), 1))


def run(split):
    frames, keys = load(split)
    d = frames[MODEL].loc[sorted(keys)].reset_index()
    d["circuit"] = d["zone"]; d["zone_id"] = d["circuit"].str[:2]
    d["load"] = d["circuit"].str.split("|").str[1].map(LOAD)
    rows = []
    for h, hn in H.items():
        x = d[d.horizon_h == h]
        rows.append(dict(level="pooled 16 circuits (circuit-hours)", name="all", horizon=hn, **metrics(x.actual_Wh, x.predicted_Wh)))
        for c, g in x.groupby("circuit"):
            rows.append(dict(level="circuit", name=c, horizon=hn, **metrics(g.actual_Wh, g.predicted_Wh)))
        for l, g in x.groupby("load"):
            rows.append(dict(level="load type (pooled)", name=l, horizon=hn, **metrics(g.actual_Wh, g.predicted_Wh)))
        n_circ = x.groupby("zone_id").circuit.nunique()
        for z, g in x.groupby("zone_id"):
            t = g.groupby("target_hour").agg(a=("actual_Wh", "sum"), p=("predicted_Wh", "sum"), k=("circuit", "nunique"))
            t = t[t.k == n_circ[z]]
            rows.append(dict(level="zone total", name=z, horizon=hn, **metrics(t.a, t.p)))
        t = x.groupby("target_hour").agg(a=("actual_Wh", "sum"), p=("predicted_Wh", "sum"), k=("circuit", "nunique"))
        t = t[t.k == 16]
        rows.append(dict(level="building total (all 16 circuits)", name="building", horizon=hn, **metrics(t.a, t.p)))
    r = pd.DataFrame(rows)
    r["ashrae_hourly_CV_le_30"] = r.CV_RMSE_pct <= 30
    r["ashrae_hourly_NMBE_le_10"] = r.NMBE_ashrae_pct.abs() <= 10
    OUT.mkdir(parents=True, exist_ok=True)
    r.to_csv(OUT / f"ashrae14_by_level_{split}.csv", index=False)
    return r


if __name__ == "__main__":
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 400)
    for s in ("test", "validation"):
        r = run(s)
        print(f"\n=== {s} ===")
        print(r[r.horizon == "day-ahead"].drop(columns=["horizon"]).to_string(index=False))
