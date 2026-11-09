"""Task 7 — simple baseline forecasts (S12, S15, S16, S17 + scoring helpers).

    from task7_baselines import *
    h     = load_derived("derived/Storey1_hourly_v1.0.parquet")       # checks SHA-256 against _META.json
    tasks = forecast_tasks(h, "day-ahead", "validation")              # S12
    b1    = baseline_last_week(h, tasks)                              # S16
    b2    = baseline_weekday_hour_median(h, tasks)                    # S17
    res   = score(pd.concat([b1, b2]), ...)                           # MAE/RMSE on the common mask
    append_results(res, "results/task7_results.csv")                  # S15

Time conventions
- hour_utc is the START of an hour. An hour is known at issue time tau if it starts before tau.
- Lead L means the target hour starts (L-1) h after tau. "+1h" = lead 1, "+6h" = lead 6 (issued every hour),
  "day-ahead" = leads 1–24 issued at 00:00 Europe/Madrid (team decision 18 Oct).
- Split boundaries are UTC (Task 6). A target hour is scored in the split its hour belongs to.

Leakage rule (protocol §9, reworded 18 Oct): inputs may only come from hours known at the issue time, including
validation/test hours; validation/test data are never used to fit anything. Both rules are asserted in code.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from task7_pipeline import mae, rmse, sha256_file

H = pd.Timedelta(hours=1)
KEY = ["horizon", "split", "series_id", "issue_time", "target_time", "lead"]   # one forecast


# ----------------------------------------------------------------- loading
def load_derived(path=C.DERIVED_PATH, verify=True) -> pd.DataFrame:
    """Load the derived hourly dataset (S09 output), verified against derived_sha256 in its _META.json.

    energy_Wh is already NaN for every invalid hour (too few rows, catch-up after an outage, pre-outage hour),
    so it is used directly as target and input.
    """
    path = Path(path)
    if verify:
        meta = json.loads(path.with_name(path.stem + "_META.json").read_text())
        got = sha256_file(path)
        if got != meta["derived_sha256"]:
            raise ValueError(f"derived dataset checksum mismatch: {got} != {meta['derived_sha256']}")
    return pd.read_parquet(path).sort_values(["series_id", "hour_utc"]).reset_index(drop=True)


def eligible_series(path=C.ELIGIBILITY_FILE, which: str = "training") -> list[str]:
    """Circuits from the S10 Excel (so no script hard-codes a circuit list).

    which = "training": circuits used to FIT models (v1.2 D4; on v1.1 files = the eligible ones)
            "all":      every circuit with 2025 data (all are forecast and scored in v1.2)
            "high_coverage": >= 90 % valid hours in validation and test (reporting only)
    The core-8 table (D5) is the 8 NE/NW circuits of Sprint 2/3: use CORE_8 in config.py."""
    el = pd.read_excel(path, sheet_name="all_series")
    if which == "all":
        return sorted(el["series_id"])
    col = "in_training" if which == "training" and "in_training" in el else "eligible"
    return sorted(el.loc[el[col].astype(bool), "series_id"])


# ----------------------------------------------------------------- S12
def forecast_tasks(h: pd.DataFrame, horizon: str, split: str, series=None) -> pd.DataFrame:
    """S12 — all (series_id, issue_time, target_time, lead) to forecast for one horizon and split.

    Only target hours inside `split` are returned. Issue times may lie before the split (e.g. the forecast
    issued at 00:00 Madrid on 22 Sep = 21 Sep 22:00 UTC) — that is fine, only targets are restricted.
    """
    leads = C.HORIZONS[horizon]
    split_hours = pd.DatetimeIndex(sorted(h.loc[h["split"] == split, "hour_utc"].unique()))
    if horizon == "day-ahead":
        loc = split_hours.tz_convert(C.ISSUE_TZ_DAY_AHEAD)
        days = pd.date_range(loc.min().normalize().tz_localize(None) - pd.Timedelta(days=1),
                             loc.max().normalize().tz_localize(None), freq="D")
        issues = days.tz_localize(C.ISSUE_TZ_DAY_AHEAD).tz_convert("UTC")      # DST-safe local midnights
        t = pd.DataFrame([(i, i + (L - 1) * H, L) for i in issues for L in leads],
                         columns=["issue_time", "target_time", "lead"])
        # a local day can have 23/25 h at DST changes: keep only targets that belong to the issue's local day
        same_day = (t["target_time"].dt.tz_convert(C.ISSUE_TZ_DAY_AHEAD).dt.normalize()
                    == t["issue_time"].dt.tz_convert(C.ISSUE_TZ_DAY_AHEAD).dt.normalize())
        t = t[same_day]
    else:
        (L,) = leads
        t = pd.DataFrame({"target_time": split_hours, "lead": L})
        t["issue_time"] = t["target_time"] - (L - 1) * H
    t = t[t["target_time"].isin(split_hours)]
    sids = sorted(h["series_id"].unique()) if series is None else list(series)
    t = t.merge(pd.DataFrame({"series_id": sids}), how="cross")
    t["horizon"], t["split"] = horizon, split
    assert (t["target_time"] >= t["issue_time"]).all()
    return t[["series_id", "issue_time", "target_time", "lead", "horizon", "split"]].reset_index(drop=True)


def _attach_truth(h, tasks, target):
    y = h.set_index(["series_id", "hour_utc"])[target]
    idx = pd.MultiIndex.from_arrays([tasks["series_id"], tasks["target_time"]])
    return tasks.assign(y_true=y.reindex(idx).to_numpy())


# ----------------------------------------------------------------- S16
def baseline_last_week(h: pd.DataFrame, tasks: pd.DataFrame, target="energy_Wh", lag_h=C.SEASONAL_LAG_H) -> pd.DataFrame:
    """S16 — Baseline 1: y_hat(T) = y(T − 168 h). NaN if that hour is missing/invalid (never filled)."""
    t = _attach_truth(h, tasks, target)
    t["input_hour"] = t["target_time"] - lag_h * H
    assert (t["input_hour"] < t["issue_time"]).all(), "leakage: input hour not known at issue time"
    y = h.set_index(["series_id", "hour_utc"])[target]
    t["y_pred"] = y.reindex(pd.MultiIndex.from_arrays([t["series_id"], t["input_hour"]])).to_numpy()
    t["model"] = "B1_last_week"
    return t


# ----------------------------------------------------------------- S17
def fit_weekday_hour_median(h: pd.DataFrame, before, target="energy_Wh") -> pd.Series:
    """Weekday × hour (Madrid local) medians per series from TRAINING rows that start before `before`.

    `before` = earliest issue time of the forecasts, so no fitted value contains data after any issue time.
    """
    tr = h[(h["split"] == "train") & (h["hour_utc"] < before)]
    assert (tr["split"] == "train").all()
    return tr.groupby(["series_id", "weekday", "hour"])[target].median()          # NaNs are skipped


def baseline_weekday_hour_median(h: pd.DataFrame, tasks: pd.DataFrame, target="energy_Wh") -> pd.DataFrame:
    """S17 — Baseline 2: y_hat(T) = median of training values with the same local weekday and hour."""
    cutoff = tasks["issue_time"].min()
    med = fit_weekday_hour_median(h, cutoff, target)
    t = _attach_truth(h, tasks, target)
    loc = t["target_time"].dt.tz_convert(C.TZ_LOCAL)
    t["input_hour"] = pd.NaT
    t["y_pred"] = med.reindex(pd.MultiIndex.from_arrays([t["series_id"], loc.dt.weekday, loc.dt.hour])).to_numpy()
    t["model"] = "B2_weekday_hour_median"
    t.attrs["fit_cutoff"] = cutoff
    return t


# ----------------------------------------------------------------- scoring
def common_mask(preds: pd.DataFrame, models=None) -> pd.Series:
    """True for forecast rows where y_true and EVERY model's prediction exist (protocol §8: same hours).

    Pass the model list explicitly when adding the Task 8 model, so all three are scored on one mask.
    """
    models = sorted(preds["model"].unique()) if models is None else list(models)
    p = preds[preds["model"].isin(models)]
    ok = p.assign(ok=p["y_true"].notna() & p["y_pred"].notna()).groupby(KEY)["ok"].agg(["all", "size"])
    ok = ok["all"] & (ok["size"] == len(models))
    m = preds.set_index(KEY).index.map(ok).fillna(False).astype(bool)
    return pd.Series(np.asarray(m), index=preds.index, name="in_mask")


def score(preds: pd.DataFrame, target_name: str, dataset_version=C.DERIVED_VERSION, models=None) -> pd.DataFrame:
    """MAE/RMSE per (horizon, split, model, series) on the common mask + coverage of each model on its own."""
    preds = preds.copy()
    preds["in_mask"] = common_mask(preds, models)
    rows = []
    for (hz, sp, m, s), g in preds.groupby(["horizon", "split", "model", "series_id"]):
        valid_t = g["y_true"].notna()
        own = valid_t & g["y_pred"].notna()
        k = g[g["in_mask"]]
        r = dict(target=target_name, horizon=hz, model=m, series_id=s, split=sp, regime=C.REGIME,
                 mask="common", dataset_version=dataset_version,
                 n_targets=int(valid_t.sum()), coverage=round(own.sum() / max(valid_t.sum(), 1), 4))
        if len(k):
            r["MAE"], r["n_valid"] = mae(k["y_true"], k["y_pred"])
            r["RMSE"], _ = rmse(k["y_true"], k["y_pred"])
            r["mean_obs"] = float(k["y_true"].mean())
        else:
            r.update(MAE=np.nan, RMSE=np.nan, n_valid=0, mean_obs=np.nan)
        rows.append(r)
    out = pd.DataFrame(rows)
    out["MAE_rel"] = out["MAE"] / out["mean_obs"]           # MAE as share of average consumption (not MAPE)
    return out[RESULT_COLS]


# ----------------------------------------------------------------- S15
RESULT_COLS = ["target", "horizon", "model", "series_id", "split", "MAE", "RMSE", "n_valid", "mean_obs",
               "MAE_rel", "n_targets", "coverage", "regime", "mask", "dataset_version"]
RESULT_KEY = ["target", "horizon", "model", "series_id", "split", "mask", "dataset_version"]


def append_results(rows: pd.DataFrame, path) -> pd.DataFrame:
    """S15 — add rows to the shared results CSV. A row with the same key replaces the old one (re-runs are
    idempotent, never duplicated). Task 8 appends its model to the same file."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    rows = rows[RESULT_COLS].astype({"dataset_version": str})
    if path.exists():
        old = pd.read_csv(path, dtype={"dataset_version": str, "lead": "Int64"})
        merged = old.merge(rows[RESULT_KEY], on=RESULT_KEY, how="left", indicator=True)
        old = old[(merged["_merge"] == "left_only").to_numpy()]
        rows = pd.concat([old, rows], ignore_index=True)
    rows = rows.sort_values(RESULT_KEY).reset_index(drop=True)
    assert not rows.duplicated(RESULT_KEY).any()
    rows.to_csv(path, index=False)
    return rows


def comparison_table(res: pd.DataFrame) -> pd.DataFrame:
    """Wide table: one row per (target, split, horizon, series), MAE/RMSE of each model and the better one."""
    w = res.pivot_table(index=["target", "split", "horizon", "series_id"], columns="model",
                        values=["MAE", "RMSE", "n_valid"], aggfunc="first")
    w.columns = [f"{v}_{m}" for v, m in w.columns]
    w = w.reset_index()
    mae_cols = [c for c in w.columns if c.startswith("MAE_")]
    w["best_by_MAE"] = w[mae_cols].idxmin(axis=1).str.replace("MAE_", "", regex=False)
    if {"MAE_B1_last_week", "MAE_B2_weekday_hour_median"} <= set(w.columns):
        w["B2_vs_B1_MAE_change"] = w["MAE_B2_weekday_hour_median"] / w["MAE_B1_last_week"] - 1
    return w
