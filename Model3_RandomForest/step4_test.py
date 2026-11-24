"""Sprint 3 Task 1 — step 4: the single test-week run.

    python step4_test.py

RUN THIS ONCE. The configuration in models/task1_rf_final_config.json was chosen on the
official validation week and confirmed on three rolling-origin folds. Nothing may be tuned
after this script runs: if the result is disappointing, that is the result (sprint rule 3).

Decisions frozen before this run, all made on validation evidence only:
  - design B, no circuit identity
  - training set: the 8 clean NE/NW circuits; all 16 are predicted
  - per-horizon parameters as recorded in the frozen config
  - NO persistence fallback at day-ahead. The validation numbers show the forest losing to
    persistence on untrained circuits at that horizon (0.484 vs 0.341); the model lead chose
    to keep the model pure and report the limit rather than hybridise. Recorded here so the
    decision is visible as having been taken BEFORE the test week, not after.

The model is refitted on exactly the training rows used during selection — the fit cut-off is
asserted against the frozen config, so the model tested is the model that was validated.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import task1_random_forest as rf1
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median, score)
from task8_model import (_series_frames, series_scale, fit_cutoff, build_features,
                         baseline_persistence, predictions_frame)
from task1_random_forest_all16 import Forecaster, per_circuit_metrics

ML = "ML_RandomForest"
CFG_PATH = Path("models/task1_rf_final_config.json")
GUARD = Path("results/task1_rf_TEST_ALREADY_RUN.txt")


def wape(df):
    k = df[df["y_true"].notna() & df["y_pred"].notna()]
    return float((k["y_true"] - k["y_pred"]).abs().sum() / k["y_true"].sum())


if __name__ == "__main__":
    if GUARD.exists():
        raise SystemExit(f"{GUARD} exists — the test week has already been scored.\n"
                         f"{GUARD.read_text()}\nRe-running would invite tuning against test.")
    cfg = json.loads(CFG_PATH.read_text())
    h = load_derived(Path(C.DERIVED_PATH))
    trained = eligible_series(Path("derived") / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())
    assert trained == cfg["training_circuits"], "training set differs from the frozen config"
    frames = _series_frames(h)

    per_rows, preds, summary = [], [], []
    for hz in C.HORIZONS:
        ch = cfg["horizons"][hz]
        cut = fit_cutoff(h, hz, all_s)
        assert str(cut) == ch["fit_cutoff_utc"], f"{hz}: fit cut-off moved since selection"
        scale = series_scale(h, cut)

        tt = forecast_tasks(h, hz, "train", trained)
        tt = tt[tt["target_time"] < cut].reset_index(drop=True)
        F = build_features(h, tt, scale, frames=frames)
        assert int(F["y_scaled"].notna().sum()) == ch["training_rows"], f"{hz}: training rows changed"

        params = dict(criterion=ch["criterion"], max_depth=ch["max_depth"],
                      min_samples_leaf=ch["min_samples_leaf"], max_features=ch["max_features"])
        rf1.RF_FIXED["n_estimators"] = ch["n_estimators"]
        m = Forecaster(params, trained, use_identity=False, seed=C.SEED).fit(F)

        ttasks = forecast_tasks(h, hz, "test", all_s)          # <-- the only place test is touched
        T = build_features(h, ttasks, scale, frames=frames)
        n_rows = T.groupby("series_id").size()
        P = predictions_frame(T, m.predict(T), ML)
        preds.append(P)

        for name, Q in [(ML, P),
                        ("B1_last_week", baseline_last_week(h, ttasks)),
                        ("B2_weekday_hour_median", baseline_weekday_hour_median(h, ttasks)),
                        ("B3_persistence", baseline_persistence(h, ttasks, frames=frames))]:
            pc = per_circuit_metrics(Q, scale, n_rows)
            pc["horizon"], pc["model"] = hz, name
            pc["in_training"] = pc.series_id.isin(trained)
            per_rows.append(pc)
            summary.append(dict(horizon=hz, model=name,
                                sMAE_all16=float(pc["scaled_MAE"].mean()),
                                sMAE_trained8=float(pc[pc.in_training]["scaled_MAE"].mean()),
                                sMAE_unseen8=float(pc[~pc.in_training]["scaled_MAE"].mean()),
                                WAPE_all16=wape(Q)))
        print(f"{hz}: tested {params}", flush=True)

    R = pd.concat(per_rows, ignore_index=True); R.to_csv("results/task1_rf_test_per_circuit.csv", index=False)
    S = pd.DataFrame(summary); S.to_csv("results/task1_rf_test_summary.csv", index=False)
    TP = pd.concat(preds, ignore_index=True)
    TP.to_parquet("results/task1_rf_test_predictions.parquet", index=False)

    # like-for-like against the other models, on the 8 circuits they cover and the same hours
    parts, names = [TP], [ML]
    for f, ns in [("results/task8_test_predictions.parquet",
                   ["B1_last_week", "B2_weekday_hour_median", "B3_persistence", "ML_GBM"]),
                  ("results/task1_linear_test_predictions.parquet", ["ML_Linear"])]:
        if Path(f).exists():
            parts.append(pd.read_parquet(f)); names += ns
    if len(parts) > 1:
        allp = pd.concat(parts, ignore_index=True)
        score(allp, "energy_Wh", models=names).to_csv("results/task1_rf_test_comparison.csv", index=False)

    GUARD.write_text(f"Test week scored from {CFG_PATH} on {pd.Timestamp.utcnow().isoformat()}.\n"
                     f"Configuration frozen beforehand; no tuning is permitted after this point.\n")

    print("\n" + "=" * 78)
    print("TEST WEEK (29 Sep - 5 Oct 2025) — run once")
    print("=" * 78)
    for col in ["sMAE_all16", "sMAE_trained8", "sMAE_unseen8", "WAPE_all16"]:
        print(f"\n{col}")
        print(S.pivot_table(index="horizon", columns="model", values=col)
               .reindex(["+1h", "+6h", "day-ahead"]).round(4).to_string())
    print("\nwrote results/task1_rf_test_*")
