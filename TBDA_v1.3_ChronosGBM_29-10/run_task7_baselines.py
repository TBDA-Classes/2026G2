"""Task 7 — run both baselines on validation (S18) and test (S31) and write the comparison table.

    python run_task7_baselines.py [--data derived/Storey1_hourly_v1.1.parquet] [--out results]

Outputs (results/):
    task7_predictions_v<ver>.parquet   every forecast row (series, issue, target, lead, y_true, y_pred, model)
    task7_results.csv                  shared results table (S15) — Task 8 appends to it
    task7_comparison.xlsx              comparison / coverage / settings sheets
Baselines are not fitted on validation, so running validation and test together cannot leak:
Baseline 1 has no parameters and Baseline 2 is fitted on training rows only (asserted in code).
"""
import argparse
from pathlib import Path

import pandas as pd

import config as C
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median, score, append_results, comparison_table)

ap = argparse.ArgumentParser()
ap.add_argument("--data", type=Path, default=Path(C.DERIVED_PATH))
ap.add_argument("--out", type=Path, default=Path("results"))
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)

h = load_derived(a.data)
series = eligible_series(C.ELIGIBILITY_FILE, which="all")      # v1.2: baselines forecast every circuit
print(f"loaded {len(h):,} rows; eligible series ({len(series)}): {', '.join(series)}")
print(f"pre-outage hours (invalid in dataset): {int(h.energy_pre_outage.sum())}")

preds, cut = [], []
for split in ["validation", "test"]:                       # S18, S31
    for hz in C.HORIZONS:
        t = forecast_tasks(h, hz, split, series)
        b2 = baseline_weekday_hour_median(h, t)
        preds += [baseline_last_week(h, t), b2]
        cut.append({"split": split, "horizon": hz, "n_forecast_rows_per_model": len(t),
                    "first_issue_utc": t.issue_time.min(), "B2_fit_uses_train_hours_before_utc": b2.attrs["fit_cutoff"]})
P = pd.concat(preds, ignore_index=True)
P["target"] = "energy_Wh"
res = score(P, "energy_Wh")
allres = append_results(res, a.out / "task7_results.csv")

ver = C.DERIVED_VERSION
P.drop(columns=["input_hour"]).to_parquet(a.out / f"task7_predictions_v{ver}.parquet", index=False)

comp = comparison_table(res)
summary = (res.groupby(["split", "horizon", "model"])
              .agg(series=("series_id", "nunique"), median_MAE_rel=("MAE_rel", "median"),
                   mean_coverage=("coverage", "mean"), hours_scored=("n_valid", "sum")).reset_index())
wins = (comp.groupby(["split", "horizon"])["best_by_MAE"].value_counts().unstack(fill_value=0).reset_index())
settings = pd.DataFrame({"setting": ["dataset", "dataset_version", "THRESHOLD", "ENERGY_MAX_GAP", "ENERGY_TAIL_MAX",
                                     "SPLITS (UTC)", "day-ahead issue", "horizons", "metric mask"],
                         "value": [a.data.name, ver, C.THRESHOLD, C.ENERGY_MAX_GAP, C.ENERGY_TAIL_MAX, str(C.SPLITS),
                                   f"00:00 {C.ISSUE_TZ_DAY_AHEAD}", str(C.HORIZONS),
                                   "common: hours where y_true and every model's forecast exist"]})
with pd.ExcelWriter(a.out / "task7_comparison.xlsx") as xw:
    summary.to_excel(xw, sheet_name="summary", index=False)
    wins.to_excel(xw, sheet_name="wins_by_MAE", index=False)
    comp.to_excel(xw, sheet_name="comparison_by_series", index=False)
    res.to_excel(xw, sheet_name="results_long", index=False)
    pd.DataFrame(cut).astype(str).to_excel(xw, sheet_name="forecast_timing", index=False)
    settings.to_excel(xw, sheet_name="settings", index=False)

from openpyxl import load_workbook                                    # readable column widths
wb = load_workbook(a.out / "task7_comparison.xlsx")
for ws in wb.worksheets:
    ws.freeze_panes = "A2"
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(45, max(10, *(len(str(c.value or "")) + 2 for c in col)))
wb.save(a.out / "task7_comparison.xlsx")

pd.set_option("display.width", 200)
print(summary.to_string(index=False)); print(wins.to_string(index=False))
print(f"wrote {a.out}/task7_results.csv ({len(allres)} rows), task7_predictions_v{ver}.parquet, task7_comparison.xlsx")
