"""v1.3 linear grid: size, clipping fitted on training rows only, and the clip leaves indicators/one-hot alone.
   pytest -q tests/test_linear_v13.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
import run_v13_linear_tune as L


def test_grid_at_least_100_configurations_per_horizon():
    assert len(L.GRID_V13) == 66
    assert len({tuple(sorted(p.items())) for p in L.GRID_V13}) == 66          # no duplicate configuration
    assert len(L.GRID_V13) * len(C.MODEL_MODES) == 132 >= 100


def test_grid_contains_sprint3_choice_and_extends_it():
    assert dict(loss="lad", alpha=1e-3, clip="none") in L.GRID_V13             # Mert's chosen setting is still tested
    assert max(p["alpha"] for p in L.GRID_V13 if p["loss"] == "lad") > 1e-3    # his open point 1: alpha above 1e-3
    assert {p["clip"] for p in L.GRID_V13} == {"none", "minmax", "p01_p99"}    # his open point 2: clipping


def test_clip_uses_training_bounds_and_spares_extra_columns():
    train = np.array([[0.0, 5.0, 1.0], [1.0, 6.0, 0.0], [2.0, 7.0, 1.0]])
    new = np.array([[10.0, -9.0, 5.0]])                                         # far outside the training range
    c = L.ClipToTraining("minmax", n_cols=2).fit(train)
    out = c.transform(new)
    assert out.tolist() == [[2.0, 5.0, 5.0]]                                    # first 2 columns clipped, 3rd untouched
    assert L.ClipToTraining("none", n_cols=2).fit(train).transform(new).tolist() == new.tolist()
    # bounds come from the training rows only: refitting on other data would change them
    c2 = L.ClipToTraining("minmax", n_cols=2).fit(new)
    assert c2.lo_.tolist() == c2.hi_.tolist()


def test_p01_p99_is_narrower_than_minmax():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(1000, 2))
    a, b = L.ClipToTraining("minmax", 2).fit(X), L.ClipToTraining("p01_p99", 2).fit(X)
    assert (b.lo_ > a.lo_).all() and (b.hi_ < a.hi_).all()
