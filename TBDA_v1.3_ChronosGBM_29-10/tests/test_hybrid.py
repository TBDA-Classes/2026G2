"""Hybrid input join (leakage guard) and blend, on toy data.   pytest -q tests/"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
from task7_pipeline import add_split_and_calendar
from task7_baselines import forecast_tasks
from task8_model import series_scale, fit_cutoff, GBMForecaster
from hybrid_model import build_features_hybrid, blend, HYBRID_FEATURES


def toy_hourly():
    hours = pd.date_range("2025-08-18 18:00", "2025-10-06 00:00", freq="h", tz="UTC")
    rows = []
    for sid, lvl in [("NE|A", 10.0), ("SE|B", 50.0)]:
        y = lvl * (1 + 0.5 * np.sin(np.arange(len(hours)) * 2 * np.pi / 24))
        rows.append(pd.DataFrame({"series_id": sid, "hour_utc": hours, "energy_Wh": y}))
    return add_split_and_calendar(pd.concat(rows, ignore_index=True))


def fake_cache(h, tasks, shift_h=0):
    c = tasks.copy()
    c["issue_time"] = c["issue_time"] + pd.Timedelta(hours=shift_h)
    c["q10"], c["q50"], c["q90"], c["ctx_valid_h"] = 1.0, 2.0, 3.0, 168
    return c


def test_join_uses_same_issue_time_and_scales():
    h = toy_hourly()
    t = forecast_tasks(h, "+6h", "validation", ["NE|A", "SE|B"])
    scale = series_scale(h, fit_cutoff(h, "+6h", ["NE|A", "SE|B"]))
    F = build_features_hybrid(h, t, scale, fake_cache(h, t))
    assert len(F) == len(t) and set(HYBRID_FEATURES) <= set(F.columns)
    assert np.allclose(F["chr_q50"] * F["scale"], 2.0) and np.allclose(F["chr_width"] * F["scale"], 2.0)


def test_shifted_cache_is_refused():
    h = toy_hourly()
    t = forecast_tasks(h, "+1h", "validation", ["NE|A"])
    scale = series_scale(h, fit_cutoff(h, "+1h", ["NE|A"]))
    with pytest.raises(ValueError, match="no Chronos forecast for the same issue time"):
        build_features_hybrid(h, t, scale, fake_cache(h, t, shift_h=-1))


def test_pooled_model_forecasts_unseen_circuit_per_series_does_not():
    h = toy_hourly()
    S = ["NE|A", "SE|B"]
    cut = fit_cutoff(h, "+1h", S)
    scale = series_scale(h, cut)
    tr = forecast_tasks(h, "+1h", "train", S)
    tr = tr[tr["target_time"] < cut]
    va = forecast_tasks(h, "+1h", "validation", S)
    F = build_features_hybrid(h, tr, scale, fake_cache(h, tr))
    V = build_features_hybrid(h, va, scale, fake_cache(h, va))
    F = F[F["series_id"] == "NE|A"]                                  # SE|B not in training
    params = dict(learning_rate=0.1, max_leaf_nodes=15, min_samples_leaf=20)
    pooled = GBMForecaster("pooled", params, ["NE|A"], features=HYBRID_FEATURES).fit(F).predict(V)
    per = GBMForecaster("per_series", params, ["NE|A"], features=HYBRID_FEATURES).fit(F).predict(V)
    unseen = (V["series_id"] == "SE|B").to_numpy()
    assert np.isfinite(pooled[unseen]).all() and np.isnan(per[unseen]).all()


def test_blend_weights():
    k = dict(series_id=["A"], horizon=["+1h"], issue_time=[pd.Timestamp("2025-09-22", tz="UTC")],
             target_time=[pd.Timestamp("2025-09-22", tz="UTC")], lead=[1])
    g = pd.DataFrame({**k, "split": ["validation"], "y_true": [5.0], "y_pred": [10.0]})
    c = pd.DataFrame({**k, "y_pred": [2.0]})
    assert blend(g, c, 1.0)["y_pred"].iat[0] == 10.0 and blend(g, c, 0.0)["y_pred"].iat[0] == 2.0
    assert blend(g, c, 0.25)["y_pred"].iat[0] == 0.25 * 10 + 0.75 * 2
