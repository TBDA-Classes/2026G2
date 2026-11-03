"""v1.3 — point 8: forecasts of the FROZEN Chronos v1.3 configuration for the TEST week (29 Sep – 5 Oct 2025).

    python run_v13_chronos_test.py

Runs only after the model choice is frozen (models/model_choice_v1.3.json must exist). Nothing is tuned or chosen
here: size, context length and point forecast per horizon are read from models/chronos_frozen_config_v1.3.json.
The script prints no test scores; scoring is done once in the comparison (Task 6).

Checks before anything is written:
- the Chronos config is the one the frozen ChronosGBM was built on (SHA-256 recorded in hybrid_frozen_config_v1.3.json)
- dataset and existing cache are unchanged (SHA-256 recorded in the frozen configs)
- the weights of every size used are the ones recorded in the Chronos config
- reproduction: the validation forecasts are re-computed and must match the frozen cache

Writes (never overwrites):
- results/chronos_cache_v1.3_test.parquet        frozen cache (train + validation) + the test rows, same columns;
                                                 load with hybrid_model.load_cache(path, allow_test=True)
- results/chronos_test_predictions_v1.3.parquet  Chronos test forecasts in the Task 7/8 format (y_pred = frozen point)
The original results/chronos_cache_v1.3.parquet is not touched (its checksum is part of the frozen hybrid config).
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import chronos_model as CM
import chronos_v13 as CV
from task7_pipeline import sha256_file
from task7_baselines import load_derived, forecast_tasks

KEY = ["series_id", "horizon", "issue_time", "lead"]
OUT_CACHE = Path(f"results/chronos_cache_{C.TAG13}_test.parquet")
OUT_PRED = Path(f"results/chronos_test_predictions_{C.TAG13}.parquet")
REPRO_TOL = 1e-3          # max |difference| of q10/q50/q90 vs the frozen cache, relative to max(1 Wh, |value|)


def main(predict=None, check_validation=True):
    if not Path(f"models/model_choice_{C.TAG13}.json").exists():
        raise SystemExit("models/model_choice_v1.3.json is missing — the model choice must be frozen before the test run.")
    for f in (OUT_CACHE, OUT_PRED):
        if f.exists():
            raise SystemExit(f"{f} exists — the test forecasts were already made. Delete it deliberately to redo.")

    chr_path, hyb_path = Path(C.FROZEN_V13["chronos"]), Path(C.FROZEN_V13["hybrid"])
    cfg, hyb = json.loads(chr_path.read_text()), json.loads(hyb_path.read_text())
    assert hyb["chronos_config"]["sha256"] == sha256_file(chr_path), "Chronos config differs from the frozen one"
    assert cfg["dataset"]["sha256"] == sha256_file(C.DERIVED_PATH), "dataset differs from the frozen one"
    assert hyb["chronos_cache"]["sha256"] == sha256_file(C.CHRONOS_CACHE_V13), "Chronos cache differs from the frozen one"
    cache = pd.read_parquet(C.CHRONOS_CACHE_V13)
    assert not cache["split"].isin(["test"]).any()

    h = load_derived(C.DERIVED_PATH)
    S_all = cfg["series"]
    grids = CM.series_grid(h)
    parts, preds = [], []
    for hz, c in cfg["horizons"].items():
        size, L, point = c["size"], int(c["ctx_len"]), c["point"]
        t0 = time.time()
        if predict is None:
            wd = CV.weights_dir(size)
            assert CM.sha256(wd / "model.safetensors") == cfg["weights"][size]["model_sha256"], f"weights {size} differ"
            pipe = CM.load_pipeline(wd)
        else:
            pipe = None

        if check_validation:                                    # same machinery reproduces the frozen cache
            v = cache[(cache["horizon"] == hz) & (cache["split"] == "validation")]
            PV = CV.forecasts9(pipe, h, forecast_tasks(h, hz, "validation", S_all), L, grids=grids, predict=predict)
            m = PV.merge(v, on=KEY, suffixes=("", "_frozen"), validate="one_to_one")
            assert len(m) == len(v), "validation rows do not match the frozen cache"
            dev = max(float(np.nanmax(np.abs(m[q] - m[q + "_frozen"]) / np.maximum(1.0, np.abs(m[q + "_frozen"]))))
                      for q in ("q10", "q50", "q90"))
            print(f"{hz}: reproduction check on {len(m):,} validation rows, max relative difference {dev:.1e}")
            if dev > REPRO_TOL:
                raise SystemExit(f"{hz}: validation forecasts differ from the frozen cache ({dev:.1e} > {REPRO_TOL}). "
                                 "Nothing was written. Check weights / package versions before the test run.")

        t = forecast_tasks(h, hz, "test", S_all)
        assert (t["split"] == "test").all() and set(t["series_id"]) == set(S_all)
        P = CV.forecasts9(pipe, h, t, L, grids=grids, predict=predict).assign(size=size)
        parts.append(P[cache.columns])
        preds.append(CV.with_point(P, point, size))
        print(f"{hz}: {len(P):,} test rows ({size}, context {L} h, {point}) in {time.time() - t0:.0f}s")
        del pipe

    test = pd.concat(parts, ignore_index=True)
    full = pd.concat([cache, test], ignore_index=True)
    assert full.duplicated(KEY).sum() == 0, "test rows collide with train/validation rows"
    assert test["q50"].notna().mean() > 0.9, "most test forecasts are missing"
    OUT_CACHE.parent.mkdir(exist_ok=True)
    full.to_parquet(OUT_CACHE, index=False)
    P = pd.concat(preds, ignore_index=True)
    P[["series_id", "issue_time", "target_time", "lead", "horizon", "split", "y_true", "y_pred", "model", "size",
       "ctx_len", "point", "q10", "q50", "q90", "pred_median", "pred_mean_q", "ctx_valid_h", "ctx_avail_h"]].to_parquet(
        OUT_PRED, index=False)
    print(f"wrote {OUT_CACHE} ({len(full):,} rows, of which {len(test):,} test; sha256 {sha256_file(OUT_CACHE)[:16]}…)")
    print(f"wrote {OUT_PRED} ({len(P):,} rows)")
    return full, P


if __name__ == "__main__":
    main()
