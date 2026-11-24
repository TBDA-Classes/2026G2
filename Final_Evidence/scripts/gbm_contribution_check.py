"""
GBM contribution check and GBM v1.3 validation recomputation
=============================================================

Evidence for 18_GBM_Justification (and the GBM section of 17_Model_Justification_Blend_v1.3).
Read only: no file outside Final_Evidence/analysis/ is written. No model is fitted.

A. Blend v1.3 with and without the GBM (test week, after the choice)
   1. Rule D10 applied to the 231 v1.3 blend mixes restricted to w_gbm = 0:
      tie = within 0.005 of the best of ALL 231 mixes, tie-break = lowest mean scaled RMSE.
   2. "Blend without GBM" = w_hybrid x ChronosGBM v1.3 + w_chronos x Chronos-Bolt v1.3 (frozen test forecasts).
   3. Both blends scored with the Task 6 code (task6_compare.evaluate: MAE in Wh, circular moving-block
      bootstrap, 24-hour blocks, 2,000 resamples) on two masks:
        - blend_valid: every test hour where the Blend and its three parts have a forecast and a valid actual
        - task6_official: the official Task 6 mask (hours valid for all nine models, 1,911 per horizon)
   This check was made after the test week and did not influence the model choice (frozen 29-30 Oct).

B. GBM v1.3 validation score recomputed from the stored validation forecasts
   Mean over the 15 training circuits of (validation MAE / circuit training mean), compared with the
   score written in models/task8_frozen_config_v1.3.json (12a_Cleaning_Checks.md A2 could not reproduce it).

Run from the repository root:   python Final_Evidence/scripts/gbm_contribution_check.py
Needs: pandas, numpy, pyarrow.
Outputs: Final_Evidence/analysis/gbm_contribution_test.csv, gbm_validation_recompute.csv
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
T6 = ROOT / "Task6_rev0_03-11"
V13 = ROOT / "TBDA_v1.3_ChronosGBM_29-10"
OUT = ROOT / "Final_Evidence" / "analysis"
TIE_MARGIN = 0.005
HORIZONS = {"+1h": 1, "+6h": 6, "day-ahead": 24}

# reuse the official Task 6 scoring code (same bootstrap, same seed rule)
os.environ.setdefault("SCALE_FILE", str(T6 / "data" / "task6_circuit_scale_train_mean_v1.2.csv"))
sys.path.insert(0, str(T6))
import task6_compare as t6  # noqa: E402

NINE = ["ML_RandomForest", "ML_Linear", "ML_GBM_v1.3", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3",
        "ML_Blend_v1.3", "B1_last_week", "B2_weekday_hour_median", "B3_persistence"]


def d10_without_gbm(log, horizon):
    g = log[log.horizon == horizon]
    best_all = g.mean_scaled_MAE.min()
    chosen = g[g.d10_chosen == True].iloc[0]  # noqa: E712
    tied = g[(g.w_gbm == 0) & (g.mean_scaled_MAE <= best_all + TIE_MARGIN)]
    pick = tied.sort_values(["mean_scaled_RMSE", "mean_scaled_MAE"]).iloc[0]
    return chosen, pick, len(tied)


def part_a():
    log = pd.read_csv(V13 / "results" / "blend_tuning_log_v1.3.csv")
    pred = {m: t6.load(T6 / "results" / "predictions" / f"{m}_test_predictions.csv") for m in NINE}
    key = ["circuit", "zone", "horizon_h", "target_hour"]
    rows = []
    seed = t6.SEED + 1000
    for hz, h in HORIZONS.items():
        chosen, pick, n_tied = d10_without_gbm(log, hz)
        parts = None
        for m in ["ML_Blend_v1.3", "ML_GBM_v1.3", "ML_ChronosGBM_v1.3", "ML_Chronos_v1.3"]:
            p = pred[m][pred[m].horizon_h == h][key + ["actual_Wh", "predicted_Wh"]].rename(
                columns={"predicted_Wh": m})
            parts = p if parts is None else parts.merge(p.drop(columns="actual_Wh"), on=key, how="inner")
        parts = parts.dropna(subset=["actual_Wh", "ML_Blend_v1.3", "ML_GBM_v1.3",
                                     "ML_ChronosGBM_v1.3", "ML_Chronos_v1.3"])
        recon = (chosen.w_gbm * parts["ML_GBM_v1.3"] + chosen.w_hybrid * parts["ML_ChronosGBM_v1.3"]
                 + chosen.w_chronos * parts["ML_Chronos_v1.3"])
        recon_err = float((recon - parts["ML_Blend_v1.3"]).abs().max())
        parts["Blend_without_GBM"] = (pick.w_hybrid * parts["ML_ChronosGBM_v1.3"]
                                      + pick.w_chronos * parts["ML_Chronos_v1.3"])

        # official Task 6 mask: hours with a forecast from all nine models and a valid actual
        official = None
        for m in NINE:
            p = pred[m][pred[m].horizon_h == h][key + ["actual_Wh", "predicted_Wh"]]
            p = p.dropna().drop(columns=["actual_Wh", "predicted_Wh"])
            official = p if official is None else official.merge(p, on=key, how="inner")

        masks = {"blend_valid": parts,
                 "task6_official": parts.merge(official, on=key, how="inner")}
        for mask, sub in masks.items():
            seed += 1
            met, pairs = t6.evaluate(sub.reset_index(drop=True), ["ML_Blend_v1.3", "Blend_without_GBM"], seed)
            mae = met.set_index("model").MAE_Wh
            pr = pairs.iloc[0]
            rows.append({
                "horizon": hz, "mask": mask, "circuit_hours": len(sub),
                "chosen_w_gbm": chosen.w_gbm, "chosen_w_hybrid": chosen.w_hybrid, "chosen_w_chronos": chosen.w_chronos,
                "chosen_val_scaled_MAE": round(chosen.mean_scaled_MAE, 4),
                "chosen_val_scaled_RMSE": round(chosen.mean_scaled_RMSE, 4),
                "noGBM_w_hybrid": pick.w_hybrid, "noGBM_w_chronos": pick.w_chronos,
                "noGBM_tied_mixes": n_tied,
                "noGBM_val_scaled_MAE": round(pick.mean_scaled_MAE, 4),
                "noGBM_val_scaled_RMSE": round(pick.mean_scaled_RMSE, 4),
                "test_MAE_blend_Wh": round(mae["ML_Blend_v1.3"], 3),
                "test_MAE_without_GBM_Wh": round(mae["Blend_without_GBM"], 3),
                "diff_blend_minus_noGBM_Wh": round(pr.MAE_A_minus_B, 3),
                "diff_lo": round(pr.diff_lo, 3), "diff_hi": round(pr.diff_hi, 3),
                "significant": bool(pr.significant),
                "blend_reconstruction_max_abs_err_Wh": recon_err,
            })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "gbm_contribution_test.csv", index=False)
    return out


def part_b():
    cfg = json.loads((V13 / "models" / "task8_frozen_config_v1.3.json").read_text())
    scale = pd.Series(json.loads((V13 / "models" / "chronos_frozen_config_v1.3.json").read_text())
                      ["horizons"]["+1h"]["scale_Wh"])
    p = pd.read_parquet(V13 / "results" / "task8_validation_predictions_v1.3.parquet")
    p = p[(p.model == "ML_GBM") & p.series_id.isin(cfg["training_series"])].dropna(subset=["y_true", "y_pred"])
    rows = []
    for hz in HORIZONS:
        g = p[p.horizon == hz]
        mae = (g.y_true - g.y_pred).abs().groupby(g.series_id).mean()
        score = float((mae / scale[mae.index]).mean())
        frozen = cfg["horizons"][hz]["validation_score"]
        rows.append({"horizon": hz, "circuits": len(mae), "rows": len(g),
                     "recomputed_scaled_MAE": round(score, 4), "frozen_scaled_MAE": round(frozen, 4),
                     "difference": round(score - frozen, 4)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "gbm_validation_recompute.csv", index=False)
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    a = part_a()
    print("\nA. Blend with and without GBM (test)\n" + a.to_string(index=False))
    b = part_b()
    print("\nB. GBM v1.3 validation recomputation\n" + b.to_string(index=False))
