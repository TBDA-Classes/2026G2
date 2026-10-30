"""v1.3: grid sizes, rule D10 and the 9-quantile Chronos read-out, on toy data.   pytest -q tests/"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
import chronos_v13 as CV
from selection import d10_choose, blend_weight_grid, scaled_scores, require_d10_agreed
from task7_baselines import forecast_tasks
from test_hybrid import toy_hourly


def test_grid_sizes_at_least_100_per_model():
    assert len(C.GBM_GRID_V13) == 128
    assert len({tuple(sorted(p.items())) for p in C.GBM_GRID_V13}) == 128
    assert len(C.CHRONOS_SIZES_V13) * len(C.CTX_GRID_V13) * len(C.CHRONOS_POINTS_V13) == 104
    W = blend_weight_grid()
    assert len(W) == 231 and len(set(W)) == 231
    assert all(abs(sum(w) - 1) < 1e-12 and min(w) >= 0 for w in W)
    assert (1.0, 0.0, 0.0) in W and (0.0, 0.0, 1.0) in W and (0.5, 0.0, 0.5) in W


def test_v13_does_not_change_v12_settings():
    assert C.GBM_GRID[0] == dict(learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=20) and len(C.GBM_GRID) == 8
    assert C.BLEND_WEIGHTS == [0.0, 0.25, 0.5, 0.75, 1.0] and C.TAG == "v1.2"


def test_d10_tie_goes_to_lower_rmse():
    log = pd.DataFrame(dict(mean_scaled_MAE=[0.300, 0.304, 0.320], mean_scaled_RMSE=[0.70, 0.65, 0.50]))
    j, d = d10_choose(log, margin=0.005)
    assert j == 1 and d["d10_tied"].tolist() == [True, True, False]


def test_d10_no_tie_keeps_best_score():
    log = pd.DataFrame(dict(mean_scaled_MAE=[0.300, 0.306], mean_scaled_RMSE=[0.90, 0.10]))
    assert d10_choose(log, margin=0.005)[0] == 0


def test_d10_identical_forecasts_go_to_simpler_model():
    # blend with w_gbm = 0 is identical to Chronos: same score, same RMSE -> Chronos (simpler) is chosen
    log = pd.DataFrame(dict(model=["ML_Chronos", "ML_Blend"], simplicity=[3, 6],
                            mean_scaled_MAE=[0.35, 0.35], mean_scaled_RMSE=[0.72, 0.72]))
    j, d = d10_choose(log, simplicity_col="simplicity", identical_to={1: 0})
    assert d.loc[j, "model"] == "ML_Chronos" and d.loc[1, "d10_replaced_by"] == 0


def test_d10_equal_rmse_goes_to_simpler_model():
    log = pd.DataFrame(dict(simplicity=[5, 3], mean_scaled_MAE=[0.300, 0.303], mean_scaled_RMSE=[0.6, 0.6]))
    assert d10_choose(log, simplicity_col="simplicity")[0] == 1


def test_scaled_scores():
    P = pd.DataFrame(dict(series_id=["A", "A", "B", "B"], y_true=[10.0, 10.0, 2.0, np.nan], y_pred=[12.0, 8.0, 1.0, 5.0]))
    s = scaled_scores(P, pd.Series({"A": 10.0, "B": 2.0}), ["A", "B"])
    assert s["mean_scaled_MAE"] == pytest.approx((0.2 + 0.5) / 2)
    assert s["mean_scaled_RMSE"] == pytest.approx((0.2 + 0.5) / 2)


def test_scripts_refuse_without_agreed_d10(monkeypatch):
    monkeypatch.setattr(C, "D10_AGREED", None)
    with pytest.raises(SystemExit):
        require_d10_agreed()


def test_forecasts9_reads_median_mean_and_range():
    h = toy_hourly()
    t = forecast_tasks(h, "+6h", "validation", ["NE|A"])

    def fake(pipe, ctxs):                          # quantile k = 10*(k+1) at every lead
        q = np.tile(np.arange(10.0, 100.0, 10.0), (len(ctxs), 24, 1))
        return q.astype("float32")

    P9 = CV.forecasts9(None, h, t, 24, predict=fake)
    assert len(P9) == len(t)
    assert np.allclose(P9["q10"], 10) and np.allclose(P9["q50"], 50) and np.allclose(P9["q90"], 90)
    assert np.allclose(P9["pred_mean_q"], 50) and np.allclose(P9["pred_median"], 50)
    assert (P9["ctx_avail_h"] == 24).all()
    assert (CV.with_point(P9, "mean_q", "tiny")["y_pred"] == P9["pred_mean_q"]).all()


def test_baseline_columns_tracked_not_chosen():
    from selection import add_baseline_columns
    log = pd.DataFrame(dict(mean_scaled_MAE=[0.30, 0.37], mean_scaled_RMSE=[0.7, 0.6], sMAE_A=[0.1, 0.5]))
    ref = {"ref_B3_persistence_MAE": 0.36, "best_baseline": "B3_persistence", "best_baseline_MAE": 0.36}
    tab = pd.DataFrame(dict(model=["B3_persistence"], sMAE_A=[0.2]))
    d = add_baseline_columns(log, ref, tab)
    assert d["gap_to_best_baseline"].round(6).tolist() == [-0.06, 0.01]
    assert d["clearly_beats_best_baseline"].tolist() == [True, False]
    assert d["n_circuits_beating_B3"].tolist() == [1, 0]
    assert len(d) == 2                                    # baselines are columns, not extra candidates


def test_d10_decision_recorded():
    assert C.D10_AGREED and C.D10_INCLUDE_BASELINES is False and C.D10_TIE_MARGIN == 0.005
