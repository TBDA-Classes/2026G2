"""Post-hoc description of the linear model's TEST errors: by Madrid hour of day, and how much of the error comes from
two known events. Reads only the files Mert published; computes tables; changes and tunes nothing.

    python docs/linear_error_by_hour/analysis_linear_by_hour.py [--pred PATH] [--per-circuit PATH] [--out DIR]

Inputs (model1_LinearRegression_all16/):
    linear_test_predictions_all16.csv           hourly test forecasts, 16 circuits x 3 horizons x 168 h
    task1_linear_all16_test_per_circuit.csv     MAE and scaled MAE per circuit (gives each circuit's scale = MAE / scaled MAE)
Metric = the team's: per circuit, MAE / circuit training mean; then the mean over circuits (each circuit counts once).
Sanity check: the script reproduces the scaled MAE of Mert's README (0.613 / 0.831 / 0.838 over 16 circuits) before it
writes anything.

Events (target day, UTC), named in README_Task1_linear.md and the team's test notes:
    NE|HVAC            2025-10-03   (24 scored hours per horizon)
    NW|Emerg. Lighting 2025-10-05   (24 scored hours per horizon; the test week ends on 5 Oct, so 6 Oct has no rows)
Writes by_hour.csv, by_block.csv, summary.csv in --out.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

EVENTS = {"NE|HVAC": ["2025-10-03"], "NW|Emerg. Lighting": ["2025-10-05"]}
BLOCKS = [(-1, 5, "00-05"), (5, 11, "06-11"), (11, 17, "12-17"), (17, 23, "18-23")]
HORIZONS = ["+1h", "+6h", "day-ahead"]
README_ALL16 = {"+1h": 0.613, "+6h": 0.831, "day-ahead": 0.838}      # Mert's README, test, 16 circuits


def load(pred_path, pc_path):
    d = pd.read_csv(pred_path)
    pc = pd.read_csv(pc_path)
    pc = pc[pc["model"] == "ML_Linear"]                     # the file also holds the baselines B1-B3
    # each circuit's training mean, per horizon (the fit cut-off differs a little between horizons: < 1 % apart)
    scale = (pc["MAE"] / pc["scaled_MAE"]).set_axis(pd.MultiIndex.from_frame(pc[["series_id", "horizon"]]))
    assert scale.index.is_unique and len(scale) == 48 and (scale > 0).all()
    d["hour"] = pd.to_datetime(d["target_hour_madrid"]).dt.hour
    d["day_utc"] = d["target_hour"].str[:10]
    k = d.dropna(subset=["actual_Wh", "predicted_Wh"]).copy()
    key = pd.MultiIndex.from_frame(k[["circuit_zone", "horizon_label"]])
    k["sae"] = (k["actual_Wh"] - k["predicted_Wh"]).abs() / scale.reindex(key).to_numpy()
    assert k["sae"].notna().all()
    k["event"] = False
    for c, days in EVENTS.items():
        k.loc[(k["circuit_zone"] == c) & k["day_utc"].isin(days), "event"] = True
    return k


def circuit_mean(df, by):
    """Mean over circuits of each circuit's mean scaled error, per group `by` (each circuit counts once)."""
    per = df.groupby(["horizon_label", "circuit_zone"] + by, observed=True)["sae"].mean()
    return per.groupby(["horizon_label"] + by, observed=True).mean()


def main():
    ap = argparse.ArgumentParser()
    root = Path("model1_LinearRegression_all16")
    ap.add_argument("--pred", type=Path, default=root / "linear_test_predictions_all16.csv")
    ap.add_argument("--per-circuit", type=Path, default=root / "task1_linear_all16_test_per_circuit.csv")
    ap.add_argument("--out", type=Path, default=Path("docs/linear_error_by_hour"))   # run from the repo root
    a = ap.parse_args()
    k = load(a.pred, a.per_circuit)
    train = k[k["circuit_in_training"] == True]
    unseen = k[k["circuit_in_training"] == False]
    assert train["circuit_zone"].nunique() == 8 and unseen["circuit_zone"].nunique() == 8

    # sanity check against the README of Mert
    chk = circuit_mean(k, [])
    for h, v in README_ALL16.items():
        assert abs(chk[h] - v) < 0.005, f"{h}: {chk[h]:.3f} does not reproduce the README value {v}"

    a.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, df in (("trained 8, all hours", train), ("trained 8, without event days", train[~train["event"]])):
        t = circuit_mean(df, ["hour"]).rename("scaled_MAE").reset_index()
        t.insert(0, "subset", name)
        rows.append(t)
    byhour = pd.concat(rows, ignore_index=True)
    byhour.to_csv(a.out / "by_hour.csv", index=False, float_format="%.4f")

    rows = []
    for name, df in (("trained 8, all hours", train), ("trained 8, without event days", train[~train["event"]])):
        df = df.assign(block=pd.cut(df["hour"], [b[0] for b in BLOCKS] + [23],
                                    labels=[b[2] for b in BLOCKS]))
        t = circuit_mean(df, ["block"]).rename("scaled_MAE").reset_index()
        t.insert(0, "subset", name)
        rows.append(t)
    pd.concat(rows, ignore_index=True).to_csv(a.out / "by_block.csv", index=False, float_format="%.4f")

    summ = []
    for h in HORIZONS:
        row = {"horizon": h}
        row["all16"] = circuit_mean(k[k.horizon_label == h], [])[h]
        row["trained8"] = circuit_mean(train[train.horizon_label == h], [])[h]
        row["unseen8_SE_SW"] = circuit_mean(unseen[unseen.horizon_label == h], [])[h]
        row["trained8_without_event_days"] = circuit_mean(train[(train.horizon_label == h) & ~train["event"]], [])[h]
        row["all16_without_event_days"] = circuit_mean(k[(k.horizon_label == h) & ~k["event"]], [])[h]
        tr = train[train.horizon_label == h]
        row["event_rows"] = int(tr["event"].sum())
        row["trained8_rows"] = len(tr)
        row["share_of_trained8_error_from_event_rows"] = tr.loc[tr["event"], "sae"].sum() / tr["sae"].sum()
        summ.append(row)
    pd.DataFrame(summ).to_csv(a.out / "summary.csv", index=False, float_format="%.4f")
    print(pd.DataFrame(summ).round(3).to_string(index=False))
    print(f"wrote {a.out}/by_hour.csv, by_block.csv, summary.csv")


if __name__ == "__main__":
    main()
