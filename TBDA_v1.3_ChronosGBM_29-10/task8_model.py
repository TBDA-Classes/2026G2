"""Task 8 — first ML forecasting model (gradient boosting) + persistence baseline B3.

    from task8_model import *
    h   = load_derived()                                     # dataset v1.1 (Task 7)
    t   = forecast_tasks(h, "+1h", "validation", series)     # Task 7 S12
    X   = build_features(h, t, scale)                        # model inputs, all known at the issue time
    b3  = baseline_persistence(h, t)                         # B3: last valid hour before the issue time

Conventions are those of task7_baselines: hour_utc = hour START; an hour is known at issue time tau if it
starts before tau; lead L = target hour starts (L-1) h after tau.

Leakage rules (protocol §9, reworded 18 Oct), enforced here:
- every input hour used for a forecast starts before its issue time (asserted in build_features)
- fitted quantities (series scale, model) use TRAINING rows whose target hour starts before the earliest
  validation issue time of that horizon (`fit_cutoff`), so the model that is validated is exactly the model
  that is frozen and used on test. Validation/test values are only ever used as past inputs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import config as C
from task7_baselines import forecast_tasks, _attach_truth

H = pd.Timedelta(hours=1)
SCALED_INPUTS = ["last_val", "mean_24", "std_24", "mean_168", "lag_T24", "lag_T168", "wk_median"]
FEATURES = SCALED_INPUTS + ["last_age_h", "n_24", "n_168", "n_weeks", "hour", "weekday", "is_weekend", "lead"]


# ----------------------------------------------------------------- helpers on the complete hourly grid
def _series_frames(h: pd.DataFrame, target="energy_Wh") -> pd.DataFrame:
    """Per (series_id, hour_utc): value plus trailing statistics that END at that hour (inclusive).

    Looking these up at hour tau-1h gives statistics of hours that started before tau, i.e. known at tau.
    """
    g = h[["series_id", "hour_utc", target]].sort_values(["series_id", "hour_utc"]).copy()
    out = []
    for sid, d in g.groupby("series_id", sort=True):
        d = d.set_index("hour_utc")
        full = pd.date_range(d.index.min(), d.index.max(), freq="h")
        y = d[target].reindex(full)
        valid_t = pd.Series(full.where(y.notna()), index=full).ffill()
        f = pd.DataFrame({
            "y": y,
            "last_val": y.ffill(limit=C.PERSISTENCE_MAX_AGE_H - 1),
            "last_age_h": (pd.Series(full, index=full) - valid_t).dt.total_seconds() / 3600 + 1,
            "mean_24": y.rolling(24, min_periods=1).mean(),
            "std_24": y.rolling(24, min_periods=2).std(),
            "n_24": y.rolling(24, min_periods=1).count(),
            "mean_168": y.rolling(168, min_periods=1).mean(),
            "n_168": y.rolling(168, min_periods=1).count(),
        }, index=full)
        f.loc[f["last_val"].isna(), "last_age_h"] = np.nan
        f["series_id"] = sid
        out.append(f.rename_axis("hour_utc").reset_index())
    return pd.concat(out, ignore_index=True).set_index(["series_id", "hour_utc"])


def _lookup(frame: pd.DataFrame, col: str, sids, hours) -> np.ndarray:
    return frame[col].reindex(pd.MultiIndex.from_arrays([sids, hours])).to_numpy()


def series_scale(h: pd.DataFrame, cutoff, target="energy_Wh") -> pd.Series:
    """Mean of each series over TRAINING hours that start before `cutoff` (a fitted quantity)."""
    tr = h[(h["split"] == "train") & (h["hour_utc"] < cutoff)]
    s = tr.groupby("series_id")[target].mean()
    return s.where(s > 0, 1.0)


# ----------------------------------------------------------------- B3
def baseline_persistence(h: pd.DataFrame, tasks: pd.DataFrame, target="energy_Wh", frames=None) -> pd.DataFrame:
    """B3 — last valid hour before the issue time (at most PERSISTENCE_MAX_AGE_H old), for every lead."""
    frames = _series_frames(h, target) if frames is None else frames
    t = _attach_truth(h, tasks, target)
    t["input_hour"] = t["issue_time"] - H
    assert (t["input_hour"] < t["issue_time"]).all()
    t["y_pred"] = _lookup(frames, "last_val", t["series_id"], t["input_hour"])
    t["model"] = "B3_persistence"
    return t


# ----------------------------------------------------------------- features
def build_features(h: pd.DataFrame, tasks: pd.DataFrame, scale: pd.Series, target="energy_Wh",
                   frames=None) -> pd.DataFrame:
    """Model inputs for every forecast row. Value features are divided by the series scale so one pooled model
    sees comparable numbers for a 1 Wh hand dryer and an 800 Wh socket circuit."""
    frames = _series_frames(h, target) if frames is None else frames
    t = _attach_truth(h, tasks, target)
    sid, tau, T = t["series_id"], t["issue_time"], t["target_time"]
    last = tau - H
    X = pd.DataFrame(index=t.index)
    for c in ["last_val", "last_age_h", "mean_24", "std_24", "n_24", "mean_168", "n_168"]:
        X[c] = _lookup(frames, c, sid, last)
    used = {"last": last}
    for k in (24, 168, 336, 504, 672):
        used[f"T{k}"] = T - k * H
        X[f"_lag{k}"] = _lookup(frames, "y", sid, T - k * H)
    for name, hrs in used.items():                                   # leakage check on every input hour
        assert (hrs < tau).all(), f"leakage: input {name} not known at issue time"
    X["lag_T24"], X["lag_T168"] = X["_lag24"], X["_lag168"]
    weeks = X[["_lag168", "_lag336", "_lag504", "_lag672"]]
    X["wk_median"] = weeks.median(axis=1, skipna=True)                # same hour, last 4 weeks
    X["n_weeks"] = weeks.notna().sum(axis=1)
    X = X.drop(columns=[c for c in X.columns if c.startswith("_lag")])
    loc = T.dt.tz_convert(C.TZ_LOCAL)
    X["hour"], X["weekday"] = loc.dt.hour, loc.dt.weekday
    X["is_weekend"] = (X["weekday"] >= 5).astype(int)
    sc = sid.map(scale).to_numpy()
    if np.isnan(sc).any():
        raise ValueError("series without a training scale")
    X[SCALED_INPUTS] = X[SCALED_INPUTS].div(sc, axis=0)
    out = pd.concat([t, X], axis=1)
    out["scale"] = sc
    out["y_scaled"] = out["y_true"] / sc
    return out


# ----------------------------------------------------------------- model
class GBMForecaster:
    """Pooled (one model, series_id as categorical input) or per-series gradient boosting on scaled targets."""

    def __init__(self, mode: str, params: dict, series: list[str], seed: int = C.SEED, features=None):
        assert mode in C.MODEL_MODES
        self.mode, self.params, self.series, self.seed = mode, dict(params), list(series), seed
        self.features = list(FEATURES if features is None else features)     # v1.2: the hybrid adds Chronos inputs
        self.codes = {s: i for i, s in enumerate(self.series)}               # a circuit not in `series` -> NaN code
        self.models: dict = {}

    @property
    def _features(self):
        return getattr(self, "features", FEATURES)          # models pickled before v1.2 have no .features

    def _X(self, F):
        X = F[self._features].astype(float).copy()
        if self.mode == "pooled":
            X["series_code"] = F["series_id"].map(self.codes).astype(float)
        return X

    def _new(self, pooled):
        p = {**C.GBM_FIXED, **self.params, "random_state": self.seed}
        if pooled:
            p["categorical_features"] = [len(self._features)]         # series_code is the last column
        return HistGradientBoostingRegressor(**p)

    def fit(self, F: pd.DataFrame):
        F = F[F["y_scaled"].notna()]                                    # missing targets are never filled
        if self.mode == "pooled":
            self.models["ALL"] = self._new(True).fit(self._X(F), F["y_scaled"])
        else:
            for s in self.series:
                g = F[F["series_id"] == s]
                self.models[s] = self._new(False).fit(self._X(g), g["y_scaled"])
        return self

    def predict(self, F: pd.DataFrame) -> np.ndarray:
        out = np.full(len(F), np.nan)
        if self.mode == "pooled":
            out[:] = self.models["ALL"].predict(self._X(F))
        else:
            for s in self.series:
                m = (F["series_id"] == s).to_numpy()
                if m.any():
                    out[m] = self.models[s].predict(self._X(F[m]))
        return np.clip(out, 0, None) * F["scale"].to_numpy()          # energy cannot be negative


def training_frame(h, horizon, series, cutoff, frames=None) -> tuple[pd.DataFrame, pd.Series]:
    """Training rows of one horizon: targets in the train split that start before `cutoff`."""
    scale = series_scale(h[h["series_id"].isin(series)], cutoff)
    t = forecast_tasks(h, horizon, "train", series)
    t = t[t["target_time"] < cutoff].reset_index(drop=True)
    F = build_features(h, t, scale, frames=frames)
    assert (F["target_time"] < cutoff).all() and (F["split"] == "train").all()
    return F, scale


def fit_cutoff(h, horizon, series) -> pd.Timestamp:
    """Earliest validation issue time of the horizon: nothing fitted may use hours from that time on."""
    return forecast_tasks(h, horizon, "validation", series)["issue_time"].min()


def predictions_frame(F: pd.DataFrame, y_pred: np.ndarray, model_name: str) -> pd.DataFrame:
    cols = ["series_id", "issue_time", "target_time", "lead", "horizon", "split", "y_true"]
    out = F[cols].copy()
    out["y_pred"], out["model"] = y_pred, model_name
    return out


def scaled_mae_by_series(P: pd.DataFrame, scale: pd.Series) -> pd.Series:
    """Selection metric pieces: per series MAE / training mean, on hours with a valid target."""
    k = P[P["y_true"].notna() & P["y_pred"].notna()]
    return (k["y_true"] - k["y_pred"]).abs().groupby(k["series_id"]).mean() / scale
