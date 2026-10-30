"""v1.3 — Chronos-Bolt helpers for the extended grid (model size x context length x point forecast).

Same context rule, NaN handling, clipping and output format as chronos_model.py (v1.2 stays untouched).
New: all 9 native Chronos-Bolt quantiles (0.1 … 0.9) are read, so two point forecasts come from ONE model call:
  - "median": the 0.5 quantile (v1.2 choice, MAE-optimal for a quantile forecast)
  - "mean_q": the mean of the 9 quantiles (a robust approximation of the mean; it ignores the tails beyond
    0.1 / 0.9, so it is not the exact mean)
q10 / q50 / q90 are kept for the hybrid inputs (D7) whatever point forecast is frozen.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import config as C
import chronos_model as CM
from task7_baselines import _attach_truth

Q9 = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def weights_dir(size: str) -> Path:
    return Path(f"weights/chronos-bolt-{size}")


def _predict9(pipe, ctxs: list[np.ndarray]) -> np.ndarray:
    """Quantiles [n, PRED_LEN, 9]."""
    import torch
    out = []
    for i in range(0, len(ctxs), CM.BATCH):
        batch = [torch.tensor(c) for c in ctxs[i:i + CM.BATCH]]
        with torch.no_grad():
            q, _ = pipe.predict_quantiles(batch, prediction_length=CM.PRED_LEN, quantile_levels=Q9)
        out.append(q.numpy())
    return np.concatenate(out)


def forecasts9(pipe, h: pd.DataFrame, tasks: pd.DataFrame, ctx_len: int, grids=None, predict=None,
               target="energy_Wh") -> pd.DataFrame:
    """One row per task with q10, q50, q90, pred_median, pred_mean_q, ctx_valid_h, ctx_avail_h (no y_pred yet)."""
    predict = _predict9 if predict is None else predict
    grids = CM.series_grid(h, target) if grids is None else grids
    calls = tasks[["series_id", "issue_time"]].drop_duplicates().reset_index(drop=True)
    ctxs = [CM.context(grids[s], tau, ctx_len) for s, tau in zip(calls["series_id"], calls["issue_time"])]
    ok = np.array([np.isfinite(c).any() for c in ctxs])
    calls["ctx_valid_h"] = [int(np.isfinite(c).sum()) for c in ctxs]
    calls["ctx_avail_h"] = [len(c) for c in ctxs]
    q = np.full((len(calls), CM.PRED_LEN, len(Q9)), np.nan, dtype="float32")
    if ok.any():
        q[ok] = predict(pipe, [c for c, k in zip(ctxs, ok) if k])
    q = np.clip(q, 0, None)
    calls["call"] = np.arange(len(calls))
    t = _attach_truth(h, tasks, target).merge(calls, on=["series_id", "issue_time"], how="left")
    li, ci = t["lead"].to_numpy() - 1, t["call"].to_numpy()
    assert (li >= 0).all() and (li < CM.PRED_LEN).all()
    t["q10"], t["q50"], t["q90"] = q[ci, li, 0], q[ci, li, 4], q[ci, li, 8]
    t["pred_median"] = t["q50"]
    t["pred_mean_q"] = q[ci, li, :].mean(axis=1)
    t["ctx_len"] = ctx_len
    return t.drop(columns="call")


def with_point(P9: pd.DataFrame, point: str, size: str, model_name=CM.MODEL) -> pd.DataFrame:
    """Forecast rows in the Task 7/8 format for one point-forecast choice."""
    assert point in C.CHRONOS_POINTS_V13
    out = P9.copy()
    out["y_pred"] = out[f"pred_{point}"]
    out["model"], out["size"], out["point"] = model_name, size, point
    return out
