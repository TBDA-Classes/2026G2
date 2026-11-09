"""Sprint 3 — pretrained time-series model: Chronos-Bolt (Small), used zero-shot.

    from chronos_model import *
    pipe = load_pipeline()                                      # local weights (checksum checked in run_chronos_test.py)
    P    = chronos_forecasts(pipe, h, tasks, ctx_len=336)       # same rows as forecast_tasks (Task 7 S12)

Nothing is fitted on our data. The model only receives the hourly energy_Wh of ONE circuit for the hours that
started before the issue time (protocol §9 reworded: inputs may use observations from hours that ended before the
issue time, also in validation/test). Invalid hours stay NaN; Chronos treats NaN as missing (it is masked, not 0).

One model call per (circuit, issue time) returns 24 hourly quantiles. The +1h, +6h and day-ahead rows read leads
1, 6 and 1–24 from those calls, so the three horizons use exactly the same machinery.

Point forecast = median (0.5 quantile): the MAE-optimal value of a quantile forecast. 0.1 and 0.9 are kept as a
forecast range (Sprint 3 item 6, anomaly detection). Negative values are clipped to 0 like the GBM.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from task7_baselines import _attach_truth

H = pd.Timedelta(hours=1)
MODEL = "ML_Chronos"
WEIGHTS_DIR = Path("weights/chronos-bolt-small")
QUANTILES = [0.1, 0.5, 0.9]
PRED_LEN = 24                       # covers every lead used in the project (1, 6, 1–24)
CTX_GRID = [168, 336, 504, 672]     # 1–4 weeks; all are available for every validation AND test issue time
BATCH = 64


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_pipeline(weights_dir=WEIGHTS_DIR):
    import torch
    from chronos import BaseChronosPipeline
    torch.manual_seed(C.SEED)
    return BaseChronosPipeline.from_pretrained(str(weights_dir), device_map="cpu", torch_dtype=torch.float32)


# ----------------------------------------------------------------- contexts
def series_grid(h: pd.DataFrame, target="energy_Wh") -> dict[str, pd.Series]:
    """Complete hourly grid per circuit (missing / invalid hours = NaN). hour_utc = hour START."""
    out = {}
    for sid, d in h.groupby("series_id", sort=True):
        y = d.set_index("hour_utc")[target].sort_index()
        out[sid] = y.reindex(pd.date_range(y.index.min(), y.index.max(), freq="h"))
    return out


def context(grid: pd.Series, issue_time: pd.Timestamp, ctx_len: int) -> np.ndarray:
    """The ctx_len hours that START before the issue time (= known at the issue time), oldest first."""
    past = grid[grid.index < issue_time]
    assert len(past) == 0 or past.index.max() < issue_time, "leakage: context hour not known at issue time"
    return past.to_numpy(dtype="float32")[-ctx_len:]


# ----------------------------------------------------------------- forecasting
def _predict(pipe, ctxs: list[np.ndarray]) -> np.ndarray:
    """Quantiles [n, PRED_LEN, len(QUANTILES)] for a list of 1-D contexts (different lengths allowed)."""
    import torch
    out = []
    for i in range(0, len(ctxs), BATCH):
        batch = [torch.tensor(c) for c in ctxs[i:i + BATCH]]
        with torch.no_grad():
            q, _ = pipe.predict_quantiles(batch, prediction_length=PRED_LEN, quantile_levels=QUANTILES)
        out.append(q.numpy())
    return np.concatenate(out)


def chronos_forecasts(pipe, h: pd.DataFrame, tasks: pd.DataFrame, ctx_len: int, grids=None,
                      target="energy_Wh", model_name=MODEL) -> pd.DataFrame:
    """Forecast rows in the Task 7/8 format (+ q10 / q90) for every row of `tasks`.

    A forecast is NaN if the context has no valid hour at all (nothing to forecast from); this is reported as
    lower coverage, never filled.
    """
    grids = series_grid(h, target) if grids is None else grids
    calls = tasks[["series_id", "issue_time"]].drop_duplicates().reset_index(drop=True)
    ctxs = [context(grids[s], tau, ctx_len) for s, tau in zip(calls["series_id"], calls["issue_time"])]
    ok = np.array([np.isfinite(c).any() for c in ctxs])
    calls["ctx_valid_h"] = [int(np.isfinite(c).sum()) for c in ctxs]     # v1.2: valid hours the forecast was based on
    calls["ctx_avail_h"] = [len(c) for c in ctxs]                        # hours available (< ctx_len early in the data)
    q = np.full((len(calls), PRED_LEN, len(QUANTILES)), np.nan, dtype="float32")
    if ok.any():
        q[ok] = _predict(pipe, [c for c, k in zip(ctxs, ok) if k])
    q = np.clip(q, 0, None)                                             # energy cannot be negative
    calls["call"] = np.arange(len(calls))
    t = _attach_truth(h, tasks, target).merge(calls, on=["series_id", "issue_time"], how="left")
    li = t["lead"].to_numpy() - 1
    assert (li >= 0).all() and (li < PRED_LEN).all()
    ci = t["call"].to_numpy()
    t["y_pred"] = q[ci, li, QUANTILES.index(0.5)]
    t["q10"] = q[ci, li, QUANTILES.index(0.1)]
    t["q90"] = q[ci, li, QUANTILES.index(0.9)]
    t["model"] = model_name
    t["ctx_len"] = ctx_len
    return t.drop(columns="call")


# ----------------------------------------------------------------- range diagnostics
def range_stats(P: pd.DataFrame, scale: pd.Series) -> pd.DataFrame:
    """Share of actual values inside the 10–90 % range (target 80 %) and its average width (scaled)."""
    k = P[P["y_true"].notna() & P["q10"].notna()].copy()
    k["inside"] = (k["y_true"] >= k["q10"]) & (k["y_true"] <= k["q90"])
    k["width_scaled"] = (k["q90"] - k["q10"]) / k["series_id"].map(scale)
    k["below"], k["above"] = k["y_true"] < k["q10"], k["y_true"] > k["q90"]
    return (k.groupby(["split", "horizon", "series_id"])
             .agg(hours=("inside", "size"), inside_10_90=("inside", "mean"), below_q10=("below", "mean"),
                  above_q90=("above", "mean"), mean_width_scaled=("width_scaled", "mean")).reset_index())
