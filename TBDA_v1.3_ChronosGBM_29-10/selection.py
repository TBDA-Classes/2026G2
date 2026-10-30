"""v1.3 — selection rule D10 (DECISIONS_v1.2.md) and the scores it needs.

    from selection import scaled_scores, d10_choose, blend_weight_grid

D10, in short:
1. Score = mean over the training circuits of validation MAE / circuit training mean (D6), each candidate on its
   own forecasts.
2. Every candidate within D10_TIE_MARGIN of the best score is tied with it.
3. Among the tied candidates, a candidate whose forecasts are identical to a simpler candidate's is replaced by the
   simpler one (e.g. blend with Chronos weight 1 = Chronos).
4. The tied candidate with the lowest mean scaled RMSE (RMSE / circuit training mean, mean over the training
   circuits) is chosen. Equal RMSE (to 1e-9): the simpler one, then the lower score, then the first in the log.
Inside one grid (configurations of the same model) the same rule applies; all configurations count as equally
simple, so step 3 does not apply there.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import config as C


def scaled_scores(P: pd.DataFrame, scale: pd.Series, select_series) -> dict:
    """Per-circuit scaled MAE / RMSE and their means. P: forecast rows with y_true, y_pred, series_id."""
    k = P[P["y_true"].notna() & P["y_pred"].notna()]
    err = k["y_true"] - k["y_pred"]
    g = err.groupby(k["series_id"])
    smae = g.apply(lambda e: e.abs().mean()) / scale
    srmse = g.apply(lambda e: float(np.sqrt((e ** 2).mean()))) / scale
    smae, srmse = smae.dropna(), srmse.dropna()
    sel = list(select_series)
    return dict(mean_scaled_MAE=float(smae.reindex(sel).mean()), mean_scaled_RMSE=float(srmse.reindex(sel).mean()),
                score_all16=float(smae.mean()), score_core8=float(smae.reindex(C.CORE_8).mean()),
                per_series_MAE=smae, per_series_RMSE=srmse)


def d10_choose(log: pd.DataFrame, score="mean_scaled_MAE", rmse="mean_scaled_RMSE", margin=None,
               simplicity_col=None, identical_to=None) -> tuple[int, pd.DataFrame]:
    """Return (index of the chosen row, the log with D10 columns added).

    simplicity_col: column with a rank (0 = simplest); None inside a grid.
    identical_to:   optional dict {row index: row index of a simpler candidate with identical forecasts}.
    """
    margin = C.D10_TIE_MARGIN if margin is None else margin
    d = log.copy()
    best = d[score].min()
    d["d10_tied"] = d[score] <= best + margin + 1e-12
    d["d10_replaced_by"] = pd.NA
    if identical_to:
        for i, j in identical_to.items():
            if d.at[i, "d10_tied"]:
                d.at[i, "d10_replaced_by"] = j
                d.at[j, "d10_tied"] = True          # identical to a tied candidate = same score, also tied
    cand = d[d["d10_tied"] & d["d10_replaced_by"].isna()].copy()
    cand["_r"] = cand[rmse].round(9)
    cand["_s"] = cand[simplicity_col] if simplicity_col else 0
    cand["_pos"] = np.arange(len(cand))
    chosen = cand.sort_values(["_r", "_s", score, "_pos"]).index[0]
    d["d10_chosen"] = d.index == chosen
    return chosen, d


def blend_weight_grid(step=None) -> list[tuple[float, float, float]]:
    """(w_gbm, w_hybrid, w_chronos) on a `step` grid with sum 1: 231 triples for step 0.05."""
    step = C.BLEND_STEP_V13 if step is None else step
    n = int(round(1 / step))
    return [(a / n, b / n, (n - a - b) / n) for a in range(n + 1) for b in range(n + 1 - a)]


def require_d10_agreed():
    if not C.D10_AGREED:
        raise SystemExit("config.D10_AGREED is None. Agree rule D10 (DECISIONS_v1.2.md) in the team, write the date "
                         "and names into config.D10_AGREED, commit, and only then run the v1.3 scripts.")


# ----------------------------------------------------------------- baselines as reference (D10c)
BASELINES = ["B1_last_week", "B2_weekday_hour_median", "B3_persistence"]


def baseline_preds(h, tasks, frames=None) -> pd.DataFrame:
    """B1–B3 validation forecasts for the given tasks (no parameters, nothing tuned)."""
    from task7_baselines import baseline_last_week, baseline_weekday_hour_median
    from task8_model import baseline_persistence
    return pd.concat([baseline_last_week(h, tasks), baseline_weekday_hour_median(h, tasks),
                      baseline_persistence(h, tasks, frames=frames)], ignore_index=True
                     ).drop(columns=["input_hour"], errors="ignore")


def baseline_reference(B: pd.DataFrame, scale: pd.Series, select_series, horizon: str):
    """(dict of reference columns for every tuning-log row, per-circuit table) from B1–B3 forecasts of ONE horizon.

    Reference columns: ref_<baseline>_MAE / _RMSE (selection circuits), best_baseline, best_baseline_MAE.
    The per-circuit table has one row per baseline with sMAE_<circuit> / sRMSE_<circuit>.
    """
    ref, rows = {}, []
    for b in BASELINES:
        s = scaled_scores(B[B["model"] == b], scale, select_series)
        ref[f"ref_{b}_MAE"], ref[f"ref_{b}_RMSE"] = s["mean_scaled_MAE"], s["mean_scaled_RMSE"]
        rows.append(dict(horizon=horizon, model=b, mean_scaled_MAE=s["mean_scaled_MAE"],
                         mean_scaled_RMSE=s["mean_scaled_RMSE"], score_all16=s["score_all16"],
                         score_core8=s["score_core8"], **{f"sMAE_{k}": v for k, v in s["per_series_MAE"].items()},
                         **{f"sRMSE_{k}": v for k, v in s["per_series_RMSE"].items()}))
    best = min(BASELINES, key=lambda b: ref[f"ref_{b}_MAE"])
    ref["best_baseline"], ref["best_baseline_MAE"] = best, ref[f"ref_{best}_MAE"]
    return ref, pd.DataFrame(rows)


def add_baseline_columns(log: pd.DataFrame, ref: dict, per_series_ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add the baseline reference to every row of a tuning log (tracked only; never used to choose).

    gap_to_best_baseline < 0 = better than the best baseline; clearly_beats_best_baseline = better by more than the
    D10 tie margin; n_circuits_beating_B3 = selection circuits where the row's scaled MAE is below B3's.
    """
    d = log.copy()
    for k, v in ref.items():
        d[k] = v
    d["gap_to_best_baseline"] = d["mean_scaled_MAE"] - ref["best_baseline_MAE"]
    d["clearly_beats_best_baseline"] = d["gap_to_best_baseline"] < -C.D10_TIE_MARGIN
    if per_series_ref is not None:
        b3 = per_series_ref.set_index("model").loc["B3_persistence"]
        cols = [c for c in d.columns if c.startswith("sMAE_") and c in b3.index and pd.notna(b3[c])]
        d["n_circuits_beating_B3"] = (d[cols].to_numpy() < b3[cols].to_numpy(dtype=float)).sum(axis=1)
    return d


def write_baseline_reference(tables: list[pd.DataFrame], path):
    """results/baseline_reference_v1.3.csv — same content from every script (deterministic baselines)."""
    pd.concat(tables, ignore_index=True).to_csv(path, index=False)
