# -*- coding: utf-8 -*-
"""
Exploratory evidence for the scope decision (2025-only training).
Authors: Jules (main author), Claude (co-author).

Reads the cleaned data (CLEAN DATA all zones.zip, field energy_Wh) and writes:
  analysis/regime_comparison_by_circuit.csv   historical (2020-23) vs recent (2025): coverage, level, weekday-daytime level,
                                              correlation of the mean 24 h profiles
  analysis/yearly_mean_by_circuit.csv         mean hourly energy per calendar year (hours with all readings valid)
  analysis/same_season_by_circuit.csv         mean hourly energy for 18 Aug-13 Oct of each year (same season as 2025)
  analysis/profile_model_history_test.csv     weekday x hour MEDIAN profile trained on different periods, scored on the test week
  analysis/profile_model_history_by_circuit.csv

IMPORTANT: the profile model here is a quick exploratory harness, not the official Task 6 baseline B2.
It is only used to compare training periods against each other under identical conditions.
Run from the repository root:  python Final_Evidence/scripts/regime_comparison.py
"""
import zipfile, io
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Final_Evidence" / "analysis"; OUT.mkdir(parents=True, exist_ok=True)
ZIP = ROOT / "CLEAN DATA all zones.zip"
PRED = ROOT / "Task6_rev0_03-11/results/predictions/ML_Blend_v1.3_test_predictions.csv"
CUT = pd.Timestamp("2024-01-01")

fr = []
with zipfile.ZipFile(ZIP) as z:
    for zone in ["NE", "NW", "SE", "SW"]:
        with z.open(f"{zone}/clean_Storey1_{zone}_CLEAN_DATA.csv") as f:
            d = pd.read_csv(f, usecols=["sensor", "Timestamp", "energy_Wh"]); d["zone"] = zone; fr.append(d)
d = pd.concat(fr)
d["series"] = d.zone + "|" + d.sensor
d["hour"] = pd.to_datetime(d["Timestamp"]).dt.floor("h")
h = d.groupby(["series", "hour"]).agg(n=("energy_Wh", "size"), nv=("energy_Wh", "count"), E=("energy_Wh", "sum")).reset_index()
h["regime"] = np.where(h.hour < CUT, "hist", "recent")
hv = h[(h.nv == h.n) & (h.n > 0)].copy()          # hours where every reading is valid

# 1. coverage, level, profile
rows = []
for s, g in h.groupby("series"):
    row = {"series": s}; prof = {}
    for r in ["hist", "recent"]:
        x = g[g.regime == r]; xv = hv[(hv.series == s) & (hv.regime == r)]
        wd = xv[(xv.hour.dt.dayofweek < 5) & xv.hour.dt.hour.between(8, 18)]
        row.update({f"{r}_hours": len(x), f"{r}_valid_hours": len(xv), f"{r}_first": x.hour.min(), f"{r}_last": x.hour.max(),
                    f"{r}_mean_Wh": xv.E.mean(), f"{r}_weekday_daytime_mean_Wh": wd.E.mean()})
        prof[r] = xv.groupby(xv.hour.dt.hour).E.mean().reindex(range(24)).values
    a, b = prof["hist"], prof["recent"]; ok = ~(np.isnan(a) | np.isnan(b))
    row["profile_corr_24h"] = np.corrcoef(a[ok], b[ok])[0, 1] if ok.sum() > 3 and a[ok].std() > 0 and b[ok].std() > 0 else np.nan
    row["level_ratio_recent_over_hist"] = row["recent_mean_Wh"] / row["hist_mean_Wh"] if row["hist_mean_Wh"] else np.nan
    rows.append(row)
pd.DataFrame(rows).to_csv(OUT / "regime_comparison_by_circuit.csv", index=False, float_format="%.3f")

# 2. yearly and same-season means
hv["year"] = hv.hour.dt.year
hv.groupby(["series", "year"]).E.mean().unstack("year").to_csv(OUT / "yearly_mean_by_circuit.csv", float_format="%.2f")
win = (hv.hour.dt.month * 100 + hv.hour.dt.day).between(818, 1013)
hv[win].groupby(["series", "year"]).E.mean().unstack("year").to_csv(OUT / "same_season_by_circuit.csv", float_format="%.2f")

# 3. profile model trained on different periods, scored on the 2025 test week (29 Sep - 5 Oct)
P = pd.read_csv(PRED, parse_dates=["target_hour"]); P = P[P.horizon_h == 1][["zone", "target_hour", "actual_Wh"]].copy()
P["target_hour"] = P.target_hour.dt.tz_convert(None) if P.target_hour.dt.tz is not None else P.target_hour
P["dow"], P["hr"] = P.target_hour.dt.dayofweek, P.target_hour.dt.hour
hv["win"] = win


def profile(df):
    df = df.assign(dow=df.hour.dt.dayofweek, hr=df.hour.dt.hour)
    return df.groupby(["series", "dow", "hr"]).E.median().rename("pred").reset_index()


def score(train, circuits=None):
    x = P.merge(profile(train), left_on=["zone", "dow", "hr"], right_on=["series", "dow", "hr"], how="left")
    if circuits is not None: x = x[x.zone.isin(circuits)]
    x = x[x.pred.notna()]
    return round((x.pred - x.actual_Wh).abs().mean(), 1), len(x)


tr25 = hv[(hv.hour >= "2025-08-19") & (hv.hour < "2025-09-22")]
sets = {
    "2025 train weeks (19 Aug-21 Sep)": tr25,
    "2020 same season (18 Aug-13 Oct)": hv[(hv.year == 2020) & hv.win],
    "2021 same season (18 Aug-13 Oct)": hv[(hv.year == 2021) & hv.win],
    "2022 same season (18 Aug-13 Oct)": hv[(hv.year == 2022) & hv.win],
    "2020-22 same season, pooled": hv[(hv.hour < CUT) & hv.win],
    "all 2020-23, every season": hv[hv.hour < CUT],
    "2025 train + 2020-22 same season": pd.concat([tr25, hv[(hv.hour < CUT) & hv.win]]),
}
res = [{"training data": k, "MAE_Wh_16_circuits": score(v)[0], "test_circuit_hours": score(v)[1]} for k, v in sets.items()]
pd.DataFrame(res).to_csv(OUT / "profile_model_history_test.csv", index=False)
circ = sorted(P.zone.unique())
pc = pd.DataFrame({"circuit": circ})
for k in ["2025 train weeks (19 Aug-21 Sep)", "2022 same season (18 Aug-13 Oct)", "all 2020-23, every season", "2025 train + 2020-22 same season"]:
    pc[k] = [score(sets[k][sets[k].series == c], [c])[0] for c in circ]
pc.to_csv(OUT / "profile_model_history_by_circuit.csv", index=False)
print(pd.DataFrame(res).to_string(index=False)); print(pc.to_string(index=False))
