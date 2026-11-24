"""Export the frozen random forest so it can be used without refitting.

    python export_model.py

Refits the frozen configuration from models/task1_rf_final_config.json and saves one fitted
model per horizon. This is NOT re-tuning: the settings, the training rows and the random seed
are all fixed, so the fit is deterministic and identical to the model that was validated and
tested.

Loading one later:

    import joblib, pandas as pd
    from task8_model import build_features
    bundle = joblib.load("models/task1_rf_p1h.joblib")
    y = bundle["model"].predict(features_frame)      # Wh, already rescaled per circuit

The bundle carries the per-circuit scaling factors and the feature list, so a prediction does
not need the training data — only the hourly dataset the features are built from.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

import config as C
import task1_random_forest as rf1
from task7_pipeline import sha256_file
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import FEATURES, _series_frames, series_scale, fit_cutoff, build_features
from task1_random_forest_all16 import Forecaster

if __name__ == "__main__":
    cfg = json.loads(Path("models/task1_rf_final_config.json").read_text())
    h = load_derived(Path(C.DERIVED_PATH))
    trained = eligible_series(Path("derived") / f"S10_eligibility_v{C.DERIVED_VERSION}_THRESHOLD{C.THRESHOLD}.xlsx")
    all_s = sorted(h["series_id"].unique())
    frames = _series_frames(h)
    manifest = {}

    for hz in C.HORIZONS:
        ch = cfg["horizons"][hz]
        cut = fit_cutoff(h, hz, all_s)
        assert str(cut) == ch["fit_cutoff_utc"], f"{hz}: fit cut-off moved"
        scale = series_scale(h, cut)
        tt = forecast_tasks(h, hz, "train", trained)
        tt = tt[tt["target_time"] < cut].reset_index(drop=True)
        F = build_features(h, tt, scale, frames=frames)
        assert int(F["y_scaled"].notna().sum()) == ch["training_rows"], f"{hz}: training rows changed"

        params = dict(criterion=ch["criterion"], max_depth=ch["max_depth"],
                      min_samples_leaf=ch["min_samples_leaf"], max_features=ch["max_features"])
        rf1.RF_FIXED["n_estimators"] = ch["n_estimators"]
        m = Forecaster(params, trained, use_identity=False, seed=C.SEED).fit(F)

        out = Path("models") / f"task1_rf_{hz.replace('+', 'p')}.joblib"
        joblib.dump({"model": m, "horizon": hz, "params": params,
                     "n_estimators": ch["n_estimators"], "seed": C.SEED,
                     "features": FEATURES, "design": "B — no circuit identity",
                     "scale_Wh": {k: float(v) for k, v in scale.items()},
                     "training_circuits": trained, "predicted_circuits": all_s,
                     "fit_cutoff_utc": str(cut), "training_rows": ch["training_rows"],
                     "dataset_sha256": cfg["dataset"]["sha256"]}, out)
        manifest[hz] = dict(file=out.name, sha256=sha256_file(out),
                            size_kb=round(out.stat().st_size / 1024, 1))
        print(f"{hz}: {out}  ({manifest[hz]['size_kb']} KB)", flush=True)

    Path("models/task1_rf_model_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("wrote models/task1_rf_model_manifest.json")
