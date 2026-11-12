"""Hourly mean of the presence (motion) detector `Pres` per zone, from the team's clean data (CLEAN DATA all zones.zip).
Output: analysis/presence_hourly.csv  (zone, h = UTC hour, Pres = share of minutes with presence, 0-1; NaN = no detector / no reading)
Used by analysis_occupancy.py. The column is called "Bsens" by the team."""
import zipfile, pandas as pd
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent          # package folder (Sprint4_UX_EnergyWatch)
REPO = ROOT.parent                                      # repository root
MODEL = REPO / "TBDA_v1.3_ChronosGBM_29-10"
T6 = REPO / "Task6_rev0_03-11" / "results" / "predictions"
OUT = ROOT / "analysis"; OUT.mkdir(exist_ok=True)

z = zipfile.ZipFile(REPO / "CLEAN DATA all zones.zip")
fr = []
for zone in ["NE", "NW", "SE", "SW"]:
    with z.open(f"{zone}/clean_Storey1_{zone}_CLEAN_DATA.csv") as f:
        d = pd.read_csv(f, usecols=["Timestamp", "Pres"], parse_dates=["Timestamp"])
    d = d[d.Timestamp >= "2025-08-18"]
    d["h"] = d.Timestamp.dt.floor("h").dt.tz_localize("UTC")
    g = d.groupby("h").Pres.mean().reset_index(); g["zone"] = zone; fr.append(g)
out = pd.concat(fr)[["zone", "h", "Pres"]]
out.to_csv(OUT / "presence_hourly.csv", index=False)
print("presence_hourly.csv", len(out), "rows")
