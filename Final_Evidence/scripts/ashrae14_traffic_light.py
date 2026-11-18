# -*- coding: utf-8 -*-
"""
Traffic-light status (green / yellow / red) of Blend v1.3 by level, from ashrae14_by_level_test.csv.
Authors: Jules (main author), Claude (co-author).

Expected CV(RMSE) limit: teacher targets of 15 Nov where they exist (constant loads 15 %, plugs 30 %, HVAC 50 %),
otherwise ASHRAE 14 hourly reference (30 %). |NMBE| limit 10 % everywhere.
Green: CV <= limit and |NMBE| <= 10.  Yellow: CV <= 1.5 x limit and |NMBE| <= 15.  Red: beyond.

Run after ashrae14_by_level.py, from the repository root:
    python Final_Evidence/scripts/ashrae14_traffic_light.py
Output: Final_Evidence/analysis/ashrae14_traffic_light_test.csv
"""
from pathlib import Path
import pandas as pd

A = Path(__file__).resolve().parents[1] / "analysis"
r = pd.read_csv(A / "ashrae14_by_level_test.csv")


def limit(row):
    if row.level != "circuit":
        return 30, "ASHRAE 14 hourly"
    t = row["name"].split("|")[1]
    if t in ("RACK", "Emerg. Lighting"):
        return 15, "teacher target"
    if t == "Plugs & Sockets":
        return 30, "teacher target"
    if t == "HVAC":
        return 50, "teacher target"
    return 30, "ASHRAE 14 hourly"          # Lighting, Hand Dryer: no teacher target


def status(cv, nmbe, lim):
    a = abs(nmbe)
    if cv <= lim and a <= 10:
        return "green"
    if cv <= 1.5 * lim and a <= 15:
        return "yellow"
    return "red"


lims = r.apply(limit, axis=1, result_type="expand")
r["expected_CV_limit_pct"], r["expected_basis"] = lims[0], lims[1]
r["status"] = [status(c, n, l) for c, n, l in zip(r.CV_RMSE_pct, r.NMBE_ashrae_pct, r.expected_CV_limit_pct)]
cols = ["level", "name", "horizon", "n", "mean_Wh", "expected_CV_limit_pct", "expected_basis", "CV_RMSE_pct", "NMBE_ashrae_pct", "status"]
out = r[r.level.isin(["circuit", "zone total", "building total (all 16 circuits)"])][cols]
out.to_csv(A / "ashrae14_traffic_light_test.csv", index=False)
print(out[out.horizon == "day-ahead"].groupby(["level", "status"]).size())
