"""Run the FROZEN final model (Blend v1.3) and write its forecasts in the Task 6 file format.

Blend v1.3 = w_gbm x GBM v1.3 + w_hybrid x ChronosGBM v1.3 + w_chronos x Chronos-Bolt v1.3 (weights per horizon in
models/blend_frozen_config_v1.3.json). Nothing is fitted or tuned here: the two GBM parts are loaded from their
.joblib files, and the Chronos-Bolt quantiles come from the frozen Chronos caches (so torch is not needed).
Same steps as Task6_rev0_03-11/generation/run_task6_v13_predictions.py, restricted to the final model.

The dashboard calls this script in a separate process (its imports use the model folder's own config.py):
    python model_engine.py test       cache/ML_Blend_v1.3_test_recomputed.csv
    python model_engine.py validation cache/ML_Blend_v1.3_validation_recomputed.csv
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "core"))   # settings, data_layer, anomalies


import json
import os
import sys
import time
from pathlib import Path

import settings as S  # only paths; no module name clashes with the model folder (config, task7_*, task8_model, ...)


def main(split: str, out_path: str) -> None:
    import joblib
    import numpy as np
    import pandas as pd

    t0 = time.time()
    model_dir = S.MODEL_DIR
    os.chdir(model_dir)                       # the model code uses paths relative to its own folder
    sys.path.insert(0, str(model_dir))
    try:                                      # parquet engine: pyarrow if installed, else the team's minipq reader
        import pyarrow  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(S.TASK6))
        import minipq
        pd.read_parquet = lambda p, **k: minipq.read_parquet(p)

    import config as C
    from task7_baselines import load_derived, forecast_tasks
    from task8_model import _series_frames, build_features, predictions_frame
    from hybrid_model import load_cache, build_features_hybrid

    cache_path = C.CHRONOS_CACHE_V13 if split == "validation" else "results/chronos_cache_v1.3_test.parquet"
    h = load_derived()
    fr = _series_frames(h)
    gc = json.load(open(C.FROZEN_V13["task8"]))
    hc = json.load(open(C.FROZEN_V13["hybrid"]))
    cc = json.load(open(C.FROZEN_V13["chronos"]))
    bc = json.load(open(C.FROZEN_V13["blend"]))
    cache = load_cache(cache_path, allow_test=(split == "test"))
    series = hc["series"]

    out = []
    for hz in C.HORIZONS:
        ch = cc["horizons"][hz]
        cz = cache[(cache.horizon == hz) & (cache["size"] == ch["size"]) & (cache.ctx_len == ch["ctx_len"])]
        tasks = forecast_tasks(h, hz, split, series)
        G = build_features(h, tasks, pd.Series(gc["horizons"][hz]["scale_Wh"]), frames=fr)
        p_gbm = joblib.load("models/" + gc["horizons"][hz]["model_file"]).predict(G)
        F = build_features_hybrid(h, tasks, pd.Series(hc["horizons"][hz].get("scale_Wh") or gc["horizons"][hz]["scale_Wh"]),
                                  cz, frames=fr)
        assert (F[["series_id", "target_time"]].values == G[["series_id", "target_time"]].values).all()
        p_hyb = joblib.load("models/" + hc["horizons"][hz]["model_file"]).predict(F)
        col = "pred_median" if ch["point"] == "median" else "pred_mean_q"
        p_chr = np.clip(F.merge(cz[["series_id", "horizon", "issue_time", "lead", col]],
                                on=["series_id", "horizon", "issue_time", "lead"], how="left")[col].to_numpy(), 0, None)
        w = bc["horizons"][hz]
        p_blend = w["w_gbm"] * p_gbm + w["w_hybrid"] * p_hyb + w["w_chronos"] * p_chr
        out.append(predictions_frame(G, p_blend, "Blend_v1.3"))

    P = pd.concat(out, ignore_index=True)
    P["horizon_h"] = P.horizon.map({"+1h": 1, "+6h": 6, "day-ahead": 24})
    P["zone"] = P.series_id
    P["circuit_zone"] = P.series_id.str.split("|").str[0]
    P = P.rename(columns={"target_time": "target_hour", "y_true": "actual_Wh", "y_pred": "predicted_Wh", "lead": "lead_h"})
    P["model"] = "ML_Blend_v1.3"
    cols = ["model", "zone", "circuit_zone", "horizon_h", "target_hour", "actual_Wh", "predicted_Wh", "lead_h", "issue_time"]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    P[cols].to_csv(out_path, index=False)
    print(json.dumps({"rows": int(len(P)), "seconds": round(time.time() - t0, 1), "split": split}))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("test", "validation"):
        sys.exit("usage: python model_engine.py {test|validation} OUTPUT.csv")
    main(sys.argv[1], str(Path(sys.argv[2]).resolve()))
