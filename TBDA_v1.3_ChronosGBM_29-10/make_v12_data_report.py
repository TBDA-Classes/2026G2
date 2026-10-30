"""Dataset v1.2 — regression check vs v1.1 (NE/NW) and per-circuit data report.

    python make_v12_data_report.py

Writes results/v1.2_nenw_validity_changes.csv and results/v1.2_data_report.xlsx. Data only: no model, no score.
"""
import numpy as np
import pandas as pd

import config as C
from task7_baselines import load_derived

new = load_derived(C.DERIVED_PATH)
old = load_derived("derived/Storey1_hourly_v1.1.parquet")

# ---- 1. regression check: every NE/NW hour whose validity changed, with the reason
k = ["series_id", "hour_utc"]
m = new.merge(old[k + ["energy_valid", "energy_Wh"]], on=k, suffixes=("", "_v11"))
nenw = m[m["series_id"].str[:2].isin(["NE", "NW"])]
ch = nenw[nenw["energy_valid"] != nenw["energy_valid_v11"]].copy()


def reason(r):
    if r.energy_valid and not r.energy_valid_v11:
        return "now valid: fewer than 30 readings, no gap > 15 min (D1)"
    if r.energy_inconsistent:
        return "now invalid: energy > 2 x power + 1 Wh (D2)"
    return "now invalid: other (CHECK)"


ch["reason"] = ch.apply(reason, axis=1)
ch["hour_utc"] = ch["hour_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")
cols = ["series_id", "hour_utc", "split", "reason", "energy_n_obs", "energy_max_gap_min", "W_mean", "energy_Wh_v11",
        "energy_source", "energy_spread_share"]
ch[cols].sort_values(k).to_csv(f"results/{C.TAG}_nenw_validity_changes.csv", index=False)
print("NE/NW hours with changed validity:", len(ch))
print(ch.groupby(["series_id", "split", "reason"]).size().to_string())
assert not (ch["reason"] == "now invalid: other (CHECK)").any(), "unexplained NE/NW validity change"

# ---- 2. per circuit and split: hours, valid share, hours lost per reason
h = new[new["split"].isin(["train", "validation", "test"])].copy()
h["no_data"] = h["energy_n_obs"] == 0
h["lost_gap"] = ~h["no_data"] & h["energy_catch_up"].astype(bool)
h["lost_pre_outage"] = ~h["no_data"] & ~h["lost_gap"] & h["energy_pre_outage"].astype(bool)
h["lost_inconsistent"] = h["energy_inconsistent"]
h["unchecked_valid"] = h["energy_valid"] & ~h["energy_checked"]
g = h.groupby(["series_id", "split"])
rep = pd.DataFrame({
    "hours": g.size(), "valid": g["energy_valid"].sum(), "valid_share": g["energy_valid"].mean().round(3),
    "lost_no_data": g["no_data"].sum(), "lost_gap_gt15": g["lost_gap"].sum(),
    "lost_pre_outage": g["lost_pre_outage"].sum(), "lost_inconsistent": g["lost_inconsistent"].sum(),
    "valid_unchecked": g["unchecked_valid"].sum(), "zero_energy_with_power": g["energy_zero_with_power"].sum(),
    "mean_spread_share": g["energy_spread_share"].mean().round(3),
}).reset_index()
rep["split"] = pd.Categorical(rep["split"], ["train", "validation", "test"])
rep = rep.sort_values(["series_id", "split"])

# ---- 3. weekly energy / power ratio (hours with valid energy and power, mean power > 5 W), BEFORE the D2 flag
raw = new.copy()
raw["E"] = np.where(raw["energy_inconsistent"], np.nan, raw["energy_Wh"])
# flagged hours have energy_Wh = NaN in the file; take the ratio from checked hours only, flagged ones counted apart
w = raw[raw["energy_checked"] & (raw["W_mean"] > 5)].copy()
w["week_start"] = w["hour_utc"].dt.tz_convert(None).dt.to_period("W-SUN").dt.start_time.dt.date
w["ratio"] = w["E"] / w["W_mean"]
w["flagged"] = w["energy_inconsistent"]
weekly = w.pivot_table(index="series_id", columns="week_start", values="ratio", aggfunc="median").round(2)
weekly_flag = w.pivot_table(index="series_id", columns="week_start", values="flagged", aggfunc="mean").round(2)

# ---- 4. flagged share by energy source (does the D2 flag follow `spread`?)
c = new[new["energy_checked"]].copy()
c["main_source"] = np.where(c["energy_spread_share"] >= 0.5, "mostly spread", "mostly counter/power")
by_src = (c.groupby(["series_id", "main_source"])["energy_inconsistent"].agg(["size", "mean"])
          .rename(columns={"size": "checked_hours", "mean": "flagged_share"}).round(3).reset_index())
by_src_all = (c.groupby("main_source")["energy_inconsistent"].agg(["size", "mean"])
              .rename(columns={"size": "checked_hours", "mean": "flagged_share"}).round(3).reset_index())

el = pd.read_excel(C.ELIGIBILITY_FILE, sheet_name="all_series")
with pd.ExcelWriter(f"results/{C.TAG}_data_report.xlsx") as xw:
    pd.DataFrame({"sheet": ["circuits", "by_split", "weekly_ratio", "weekly_flagged", "flag_by_source",
                            "flag_by_source_all", "nenw_changes"],
                  "content": ["S10 v1.2: core (reporting), in_training (D4) and why",
                              "Per circuit and split: valid hours and hours lost per reason",
                              "Median hourly energy / mean power per week (checked hours, W > 5 W); flagged hours excluded",
                              "Share of checked hours flagged by D2, per week",
                              "Flagged share for hours mostly derived by `spread` vs by counter/power",
                              "Same, all circuits together",
                              "Every NE/NW hour whose validity differs from v1.1, with the reason"]}
                 ).to_excel(xw, sheet_name="README", index=False)
    el.to_excel(xw, sheet_name="circuits", index=False)
    rep.to_excel(xw, sheet_name="by_split", index=False)
    weekly.to_excel(xw, sheet_name="weekly_ratio")
    weekly_flag.to_excel(xw, sheet_name="weekly_flagged")
    by_src.to_excel(xw, sheet_name="flag_by_source", index=False)
    by_src_all.to_excel(xw, sheet_name="flag_by_source_all", index=False)
    ch[cols].to_excel(xw, sheet_name="nenw_changes", index=False)
print(rep[rep.split != "train"].to_string(index=False))
print(weekly_flag.to_string()); print(by_src_all.to_string(index=False))
