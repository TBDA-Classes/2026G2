"""PB-28 Prophet test: grid size, training rows only, clipping, horizon-free forecast.
   pytest -q Sprint4_Prophet_PB28/tests/test_prophet_pb28.py      (from the repository root)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_prophet_validation as R


def toy_hours():
    t = pd.date_range("2025-08-19", "2025-09-29", freq="h", tz="UTC", inclusive="left")
    y = 100 + 50 * np.sin(2 * np.pi * t.hour / 24) + 30 * (t.weekday < 5)
    split = np.where(t < pd.Timestamp("2025-09-22", tz="UTC"), "train", "validation")
    h = pd.DataFrame({"series_id": "A", "hour_utc": t, "energy_Wh": y, "split": split})
    h.loc[h.index[::50], "energy_Wh"] = np.nan                                 # invalid hours stay missing
    return h


def test_grid_has_at_least_100_unique_configurations():
    assert len(R.GRID) == 112 >= 100
    assert len({tuple(sorted(p.items())) for p in R.GRID}) == 112


def test_train_frame_uses_training_hours_before_cutoff_only():
    h = toy_hours()
    cut = pd.Timestamp("2025-09-21 22:00", tz="UTC")
    f = R.train_frame(h, "A", cut)
    last_ok = h[(h["split"] == "train") & (h["hour_utc"] < cut) & h["energy_Wh"].notna()]
    assert len(f) == len(last_ok)                                             # no validation hour, no missing value
    assert f["ds"].max() < R.local_naive(pd.Series([cut]))[0]
    assert f["y"].notna().all() and set(f.columns) == {"ds", "y", "is_weekday", "is_weekend"}


def test_forecast_is_clipped_at_zero_and_finite():
    h = toy_hours()
    h["energy_Wh"] = h["energy_Wh"] - 160                                     # many negative training values
    cut = pd.Timestamp("2025-09-22", tz="UTC")
    tgt = pd.Series(pd.date_range("2025-09-22", periods=48, freq="h", tz="UTC"))
    y = R.prophet_forecast(R.train_frame(h, "A", cut), tgt, R.GRID[0])
    assert len(y) == 48 and np.isfinite(y).all() and (y >= 0).all()


def test_weekday_weekend_daily_profile_is_learnt():
    h = toy_hours()
    cut = pd.Timestamp("2025-09-22", tz="UTC")
    p = dict(changepoint_prior_scale=0.05, seasonality_prior_scale=10.0, seasonality_mode="additive",
             daily="weekday_weekend")
    tgt = pd.Series(pd.to_datetime(["2025-09-24 10:00", "2025-09-27 10:00"]).tz_localize("UTC"))   # Wed, Sat
    wed, sat = R.prophet_forecast(R.train_frame(h, "A", cut), tgt, p)
    assert wed - sat > 20                                                     # toy data: +30 Wh on weekdays
