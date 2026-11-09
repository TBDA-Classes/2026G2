"""v1.2 rules (DECISIONS_v1.2.md D1–D4) on toy data.   pytest -q tests/"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C
from task7_pipeline import (aggregate_energy_hourly, hourly_power_current, consistency_check,
                            add_split_and_calendar, eligibility)


def toy(minutes, energy=1.0, W=60.0, sid="SE|HVAC", src="spread", start="2025-09-01 10:00"):
    t = pd.Timestamp(start, tz="UTC") + pd.to_timedelta(list(minutes), unit="min")
    return pd.DataFrame({"series_id": sid, "utc": t, "hour_utc": t.floor("h"),
                         "energy_Wh": energy, "energy_source": src, "W": W, "I": W / 230})


def hourly(df):
    e = aggregate_energy_hourly(df)
    p = hourly_power_current(df)
    return consistency_check(e.merge(p, on=["series_id", "hour_utc"], how="left"))


def test_sparse_hour_without_long_gap_is_valid():
    # D1: readings every 12 min (5 per hour), each carrying 12 min of a 60 W load = 12 Wh -> 60 Wh, complete
    df = toy(range(0, 120, 12), energy=12.0, W=60.0)
    h = hourly(df.assign(W=60.0))
    h10 = h.iloc[0]
    assert h10.energy_n_obs == 5 and h10.energy_valid and h10.energy_Wh == 60.0
    assert C.THRESHOLD <= 5, "the row count must no longer exclude sparse hours"


def test_gap_longer_than_max_gap_still_invalid():
    df = pd.concat([toy(range(0, 30)), toy(range(50, 60))])          # 20-min gap before 10:50
    h = hourly(df.reset_index(drop=True)).iloc[0]
    assert h.energy_catch_up and not h.energy_valid


def test_energy_far_above_power_invalidates_hour():
    # D2: 60 W for an hour (W_mean 60) but energy 3 Wh/min = 180 Wh > 2*60 + 1
    h = hourly(toy(range(60), energy=3.0, W=60.0)).iloc[0]
    assert h.energy_checked and h.energy_inconsistent and not h.energy_valid and np.isnan(h.energy_Wh)


def test_energy_below_power_is_not_flagged():
    # D2 is one-sided: hand-dryer-like (energy far below sampled power) stays valid
    h = hourly(toy(range(60), energy=0.1, W=600.0, sid="NW|Hand Dryer")).iloc[0]
    assert h.energy_checked and not h.energy_inconsistent and h.energy_valid


def test_tolerance_protects_tiny_loads():
    # 0.5 W load, energy rounded up to 1.5 Wh in the hour: 1.5 <= 2*0.5 + 1 -> not flagged
    df = toy(range(60), energy=0.025, W=0.5, sid="NE|HVAC")
    h = hourly(df).iloc[0]
    assert not h.energy_inconsistent


def test_unchecked_when_power_missing():
    df = toy(range(120), energy=10.0, W=60.0)
    df.loc[:59, "W"] = np.nan                                       # no power readings in the first hour
    h = hourly(df).iloc[0]
    assert not h.energy_checked and h.energy_valid                  # kept, but counted as unchecked


def test_zero_with_power_is_counted_not_flagged():
    h = hourly(toy(range(60), energy=0.0, W=50.0)).iloc[0]
    assert h.energy_zero_with_power and h.energy_valid and h.energy_Wh == 0


def test_spread_share():
    df = toy(range(60))
    df.loc[:29, "energy_source"] = "counter"
    h = hourly(df).iloc[0]
    assert abs(h.energy_spread_share - 0.5) < 1e-9


def test_training_rule_drops_circuit_with_mostly_flagged_training_hours():
    # D4: circuit A consistent, circuit B 3x power in every training hour
    start = "2025-08-25 00:00"
    a = toy(range(0, 60 * 200), energy=1.0, W=60.0, sid="NE|A", start=start)
    b = toy(range(0, 60 * 200), energy=3.0, W=60.0, sid="SE|B", start=start)
    h = add_split_and_calendar(hourly(pd.concat([a, b], ignore_index=True)))
    el = eligibility(h).set_index("series_id")
    assert el.loc["NE|A", "in_training"] and el.loc["NE|A", "train_valid_hours"] == 200
    assert not el.loc["SE|B", "in_training"] and el.loc["SE|B", "train_flagged_share"] == 1.0
    assert "inconsistent" in el.loc["SE|B", "training_reason"]
