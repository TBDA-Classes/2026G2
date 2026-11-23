"""Sprint 3 Task 1 — step 3, stage 4: refit the chosen configuration and record it.

    python step3_final.py

The parameters below were chosen on the official validation week AND confirmed on three
rolling-origin folds inside the training period. They are frozen here: refitted at the full
tree budget, scored on all 16 circuits against the baselines, and written to
models/task1_rf_final_config.json.

The test week is still untouched. Running it is step 4 of the plan and happens once.
"""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

import config as C
import task1_random_forest as rf1
from task7_pipeline import sha256_file
from task7_baselines import (load_derived, eligible_series, forecast_tasks, baseline_last_week,
                             baseline_weekday_hour_median, score)
from task8_model import (FEATURES, _series_frames, series_scale, fit_cutoff, build_features,
                         baseline_persistence, predictions_frame)
from task1_random_forest_all16 import Forecaster, per_circuit_metrics

FINAL_TREES = 300
TRAIN_ROWS_REFERENCE = 5653          # leaf sizes are quoted both absolutely and as a share of this

CHOSEN = {
    "+1h":       dict(criterion="absolute_error", max_depth=12, min_samples_leaf=100, max_features=1.0),
    "+6h":       dict(criterion="absolute_error", max_depth=4,  min_samples_leaf=250, max_features=0.5),
    "day-ahead": dict(criterion="absolute_error", max_depth=4,  min_samples_leaf=250, max_features=0.5),
}

if __name__ == "__main__":
    Path("models").mkdir(exist_ok=True); Path("results").mkdir(exist_ok=True)
    h = load_derived(Path(C.DERIVED_PATH))
    trained = eligible_series(Path("derived") / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())
    frames = _series_frames(h)

    per_rows, preds, summary, cfg_out = [], [], [], {}
    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, all_s)
        scale = series_scale(h, cut)
        tt = forecast_tasks(h, hz, "train", trained)
        tt = tt[tt["target_time"] < cut].reset_index(drop=True)
        F = build_features(h, tt, scale, frames=frames)
        vtasks = forecast_tasks(h, hz, "validation", all_s)
        V = build_features(h, vtasks, scale, frames=frames)
        n_rows = V.groupby("series_id").size()

        rf1.RF_FIXED["n_estimators"] = FINAL_TREES
        m = Forecaster(CHOSEN[hz], trained, use_identity=False, seed=C.SEED).fit(F)
        P = predictions_frame(V, m.predict(V), "ML_RandomForest")
        preds.append(P)

        for name, Q in [("ML_RandomForest", P),
                        ("B1_last_week", baseline_last_week(h, vtasks)),
                        ("B2_weekday_hour_median", baseline_weekday_hour_median(h, vtasks)),
                        ("B3_persistence", baseline_persistence(h, vtasks, frames=frames))]:
            pc = per_circuit_metrics(Q, scale, n_rows)
            pc["horizon"], pc["model"] = hz, name
            pc["in_training"] = pc.series_id.isin(trained)
            per_rows.append(pc)
            k = Q[Q["y_true"].notna() & Q["y_pred"].notna()]
            summary.append(dict(horizon=hz, model=name,
                                sMAE_all16=float(pc["scaled_MAE"].mean()),
                                sMAE_trained8=float(pc[pc.in_training]["scaled_MAE"].mean()),
                                sMAE_unseen8=float(pc[~pc.in_training]["scaled_MAE"].mean()),
                                WAPE_all16=float((k["y_true"] - k["y_pred"]).abs().sum() / k["y_true"].sum())))

        p = CHOSEN[hz]
        cfg_out[hz] = dict(**{k: v for k, v in p.items()},
                           min_samples_leaf_as_share=round(p["min_samples_leaf"] / TRAIN_ROWS_REFERENCE, 5),
                           n_estimators=FINAL_TREES, training_rows=int(F["y_scaled"].notna().sum()),
                           fit_cutoff_utc=str(cut))
        print(f"{hz}: {p} -> refitted on {int(F['y_scaled'].notna().sum())} rows", flush=True)

    R = pd.concat(per_rows, ignore_index=True)
    R.to_csv("results/task1_rf_final_per_circuit.csv", index=False)
    S = pd.DataFrame(summary)
    S.to_csv("results/task1_rf_final_summary.csv", index=False)
    pd.concat(preds, ignore_index=True).to_parquet("results/task1_rf_final_validation_predictions.parquet", index=False)

    meta = json.loads(Path(C.DERIVED_PATH).with_name(Path(C.DERIVED_PATH).stem + "_META.json").read_text())
    Path("models/task1_rf_final_config.json").write_text(json.dumps(dict(
        model="ML_RandomForest", version="final-step3",
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        design="B — no circuit identity; every circuit scaled by its own training mean",
        training_circuits=trained, predicted_circuits=all_s,
        selection=("Chosen on the official validation week scoring all 16 circuits, then confirmed on "
                   "three expanding-window rolling-origin folds inside the training period. Seed "
                   "repetition (5 seeds) used to separate real differences from run-to-run noise; the "
                   "one-standard-error rule used to prefer the simpler model on ties. Test not used."),
        dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION,
                     sha256=sha256_file(Path(C.DERIVED_PATH)), source_sha256=meta["source_sha256_file"]),
        splits_utc=C.SPLITS, features=FEATURES,
        fixed=dict(n_estimators=FINAL_TREES, bootstrap=True, random_state=C.SEED),
        horizons=cfg_out,
        versions=dict(python=platform.python_version(), sklearn=sklearn.__version__,
                      pandas=pd.__version__, numpy=np.__version__)), indent=2))

    print("\n" + "=" * 78)
    print("VALIDATION WEEK — final model vs baselines, all 16 circuits")
    print("=" * 78)
    for col in ["sMAE_all16", "sMAE_trained8", "sMAE_unseen8", "WAPE_all16"]:
        print(f"\n{col}")
        print(S.pivot_table(index="horizon", columns="model", values=col)
               .reindex(["+1h", "+6h", "day-ahead"]).round(4).to_string())
    print("\nwrote models/task1_rf_final_config.json and results/task1_rf_final_*")
