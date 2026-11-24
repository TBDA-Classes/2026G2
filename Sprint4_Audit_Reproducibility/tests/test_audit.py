"""Unit tests of the audit helpers, on small made-up data.

Run from the repository root:  python -m pytest -q Sprint4_Audit_Reproducibility/tests
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import compare_tables, same_values, tolerance  # noqa: E402
from check_files import expand, paths_in_document  # noqa: E402
from check_numbers import d10_choice  # noqa: E402


def test_tolerance():
    assert tolerance("exact") == 0.0
    assert tolerance("") == 0.0
    assert tolerance("0.05") == 0.05
    assert tolerance("1e-6 Wh") == 1e-6


def test_same_values():
    assert same_values("22.2", "22.2332", 0.05)
    assert not same_values("22.2", "22.4", 0.05)
    assert same_values("16/14/14", "16/14/14", 0)
    assert not same_values("16/14/14", "16/14", 0)
    assert same_values("True/False", "True/False", 0)


def test_compare_tables(tmp_path):
    old = pd.DataFrame({"circuit": ["a", "b"], "mae": [1.0, 2.0]})
    old.to_csv(tmp_path / "old.csv", index=False)
    old.iloc[::-1].to_csv(tmp_path / "same_other_order.csv", index=False)
    old.assign(mae=[1.0, 2.1]).to_csv(tmp_path / "changed.csv", index=False)
    assert compare_tables(tmp_path / "same_other_order.csv", tmp_path / "old.csv", 0)[0]
    assert not compare_tables(tmp_path / "changed.csv", tmp_path / "old.csv", 0.05)[0]
    assert compare_tables(tmp_path / "changed.csv", tmp_path / "old.csv", 0.2)[0]


def test_compare_tables_empty_text(tmp_path):
    # an empty text cell in both tables is not a difference
    t = pd.DataFrame({"circuit": ["a", "b"], "first_reading": ["2025-08-18", None], "mae": [1.0, 2.0]})
    t.to_csv(tmp_path / "a.csv", index=False)
    t.to_csv(tmp_path / "b.csv", index=False)
    assert compare_tables(tmp_path / "a.csv", tmp_path / "b.csv", 0)[0]


def test_paths_in_document():
    text = "See `Task6/RESULTS.md`, `results/` and `config.D10_AGREED`, run `python a.py`, file `x_{test,val}.csv`."
    assert paths_in_document(text) == ["Task6/RESULTS.md", "results/", "x_{test,val}.csv"]
    assert expand("x_{test,val}.csv") == ["x_test.csv", "x_val.csv"]


def test_d10_choice(tmp_path):
    # B is tied with A (within 0.005) and has the lower RMSE, so B wins; C is far behind.
    rows = []
    for h in ["+1h", "+6h", "day-ahead"]:
        rows += [{"horizon": h, "model": "A", "simplicity": 3, "mean_scaled_MAE": 0.300, "mean_scaled_RMSE": 0.70, "candidate": True},
                 {"horizon": h, "model": "B", "simplicity": 6, "mean_scaled_MAE": 0.304, "mean_scaled_RMSE": 0.65, "candidate": True},
                 {"horizon": h, "model": "C", "simplicity": 4, "mean_scaled_MAE": 0.400, "mean_scaled_RMSE": 0.60, "candidate": True},
                 {"horizon": h, "model": "Base", "simplicity": 0, "mean_scaled_MAE": 0.290, "mean_scaled_RMSE": 0.50, "candidate": False}]
    pd.DataFrame(rows).to_csv(tmp_path / "choice.csv", index=False)
    assert d10_choice(tmp_path / "choice.csv", {}) == "B/B/B"
