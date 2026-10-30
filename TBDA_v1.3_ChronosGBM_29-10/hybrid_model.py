"""v1.2 — ChronosGBM hybrid and GBM/Chronos blend (DECISIONS_v1.2.md D7, D7b).

    from hybrid_model import *
    cache = load_cache()                                         # Chronos forecasts, train + validation issue times
    F     = build_features_hybrid(h, tasks, scale, cache)        # Task 8 features + Chronos inputs
    m     = GBMForecaster(mode, params, train_series, features=HYBRID_FEATURES).fit(F)

Why Chronos forecasts may be used as inputs on TRAINING rows: Chronos is not fitted on our data, so its forecast
for a training hour is a genuine out-of-sample forecast made from hours before the issue time (asserted in
chronos_model.context). Two models both fitted on our data would instead need cross-fitting.

Leakage guard: every forecast row must find the Chronos forecast made at the SAME (circuit, horizon, issue time,
lead). A missing match raises instead of silently producing NaN inputs, so a cache built for other issue
times (e.g. shifted by one hour) cannot be joined by mistake.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from task8_model import FEATURES, build_features

CACHE_PATH = Path(f"results/chronos_cache_{C.TAG}.parquet")
CHR_SCALED = ["chr_q10", "chr_q50", "chr_q90", "chr_width"]
HYBRID_FEATURES = FEATURES + CHR_SCALED + ["chr_ctx_h"]
KEY = ["series_id", "horizon", "issue_time", "lead"]


def load_cache(path=CACHE_PATH, allow_test=False) -> pd.DataFrame:
    """Chronos forecast cache. Test issue times are only allowed in the single test run (point 8)."""
    c = pd.read_parquet(path)
    if not allow_test:
        assert not c["split"].isin(["test"]).any(), "cache contains test rows"
    return c


def build_features_hybrid(h: pd.DataFrame, tasks: pd.DataFrame, scale: pd.Series, cache: pd.DataFrame,
                          frames=None) -> pd.DataFrame:
    """Task 8 features + Chronos q10/q50/q90/width (÷ circuit scale) + chr_ctx_h (valid hours in the context)."""
    F = build_features(h, tasks, scale, frames=frames)
    c = cache[KEY + ["target_time", "q10", "q50", "q90", "ctx_valid_h"]]
    out = F.merge(c, on=KEY, how="left", suffixes=("", "_chr"), validate="many_to_one", indicator=True)
    missing = out["_merge"] != "both"
    if missing.any():
        ex = out.loc[missing, KEY].head(3).to_dict("records")
        raise ValueError(f"{int(missing.sum())} forecast rows have no Chronos forecast for the same issue time "
                         f"(cache built for other issue times?). Examples: {ex}")
    assert (out["target_time"] == out["target_time_chr"]).all(), "Chronos lead/target mismatch"
    sc = out["scale"].to_numpy()
    out["chr_q10"], out["chr_q50"], out["chr_q90"] = out["q10"] / sc, out["q50"] / sc, out["q90"] / sc
    out["chr_width"] = (out["q90"] - out["q10"]) / sc
    out["chr_ctx_h"] = out["ctx_valid_h"].astype(float)
    return out.drop(columns=["_merge", "target_time_chr", "q10", "q90", "ctx_valid_h"]).rename(columns={"q50": "chr_q50_Wh"})


def blend(gbm: pd.DataFrame, chronos: pd.DataFrame, w: float, model_name="ML_Blend") -> pd.DataFrame:
    """w × GBM + (1 − w) × Chronos median, on the same forecast rows. NaN where either model has no forecast."""
    k = ["series_id", "horizon", "issue_time", "target_time", "lead"]
    m = gbm[k + ["split", "y_true", "y_pred"]].merge(chronos[k + ["y_pred"]], on=k, suffixes=("_gbm", "_chr"),
                                                      validate="one_to_one")
    m["y_pred"] = w * m["y_pred_gbm"] + (1 - w) * m["y_pred_chr"]
    m["model"], m["w_gbm"] = model_name, w
    return m.drop(columns=["y_pred_gbm", "y_pred_chr"])
