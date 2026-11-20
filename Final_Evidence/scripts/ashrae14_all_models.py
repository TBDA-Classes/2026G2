# -*- coding: utf-8 -*-
"""
ASHRAE Guideline 14 check of ALL nine Task 6 models (not only Blend v1.3).

Same hours and same formulas as Jules' script ashrae14_by_level.py:
we import its functions, so nothing is defined twice.
  - hours: the Task 6 common hours (1,911 circuit-hours per horizon on test)
  - CV(RMSE) = 100 x RMSE / mean of the measurements
  - NMBE (ASHRAE sign) = 100 x sum(measured - forecast) / sum(measured)
  - hourly limits: CV(RMSE) <= 30 % and |NMBE| <= 10 %

Run from the repository root:
    python Final_Evidence/scripts/ashrae14_all_models.py
Outputs (Final_Evidence/analysis/):
    ashrae14_all_models_{test,validation}.csv             one row per model and horizon
    ashrae14_all_models_by_circuit_{test,validation}.csv  one row per model, horizon and circuit

Report only: nothing here is used to choose or tune a model.
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ashrae14_by_level import load, metrics, M16, H, OUT   # Jules' script, same folder


def passes(r):
    return r["CV_RMSE_pct"] <= 30 and abs(r["NMBE_ashrae_pct"]) <= 10


def run(split):
    frames, keys = load(split)
    summary, by_circuit = [], []
    for model in M16:
        d = frames[model].loc[sorted(keys)].reset_index()
        for h, hn in H.items():
            x = d[d.horizon_h == h]

            # 1) each circuit
            n_pass = 0
            for c, g in x.groupby("zone"):
                r = metrics(g.actual_Wh, g.predicted_Wh)
                r["passes"] = passes(r)
                n_pass += r["passes"]
                by_circuit.append(dict(model=model, horizon=hn, circuit=c, **r))

            # 2) building total: sum of the 16 circuits, only hours where all 16 are present
            t = x.groupby("target_hour").agg(a=("actual_Wh", "sum"), p=("predicted_Wh", "sum"),
                                             k=("zone", "nunique"))
            t = t[t.k == 16]
            b = metrics(t.a, t.p)

            summary.append(dict(model=model, horizon=hn,
                                MAE_Wh=metrics(x.actual_Wh, x.predicted_Wh)["MAE_Wh"],
                                building_hours=b["n"],
                                building_CV_RMSE_pct=b["CV_RMSE_pct"],
                                building_NMBE_ashrae_pct=b["NMBE_ashrae_pct"],
                                building_passes=passes(b),
                                circuits_passing=n_pass,
                                circuits_total=x.zone.nunique()))

    OUT.mkdir(parents=True, exist_ok=True)
    s = pd.DataFrame(summary)
    s.to_csv(OUT / f"ashrae14_all_models_{split}.csv", index=False)
    pd.DataFrame(by_circuit).to_csv(OUT / f"ashrae14_all_models_by_circuit_{split}.csv", index=False)
    return s


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    for split in ("test", "validation"):
        print(f"\n=== {split} ===")
        print(run(split).to_string(index=False))
