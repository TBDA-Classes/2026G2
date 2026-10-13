# -*- coding: utf-8 -*-
"""
Created on Tue Oct 13 15:26:59 2026

@author: lucia
"""

# Task 6 - Train / Validation / Test Strategy
# Tools for Big Data Analysis - CeDInt

from pathlib import Path
import pandas as pd
import numpy as np


# --------------------------------------------------
# 1. Load frozen dataset
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz"

df = pd.read_csv(
    DATA_PATH,
    compression="xz",
    low_memory=False
)


# --------------------------------------------------
# 2. Create time variables
# --------------------------------------------------

df["utc"] = pd.to_datetime(
    df["Timestamp"],
    utc=True
)

CUT = pd.Timestamp(
    "2024-01-01",
    tz="UTC"
)

df["regime"] = np.where(
    df["utc"] < CUT,
    "historical_2020_2023",
    "recent_2025"
)

df["series_id"] = (
    df["zone"] + "|" + df["sensor"]
)


# --------------------------------------------------
# 3. Study recent 2025 coverage
# --------------------------------------------------

recent = df[
    df["regime"] == "recent_2025"
].copy()

recent["hour"] = recent["utc"].dt.floor("h")


# --------------------------------------------------
# 4. Hourly coverage by series
# --------------------------------------------------

hourly = (
    recent
    .groupby(["series_id", "hour"])
    .agg(
        observations=("energy_Wh", "size"),
        valid_energy=("energy_Wh", "count")
    )
    .reset_index()
)


# --------------------------------------------------
# 5. Summary by series
# --------------------------------------------------

summary = (
    hourly
    .groupby("series_id")
    .agg(
        first_hour=("hour", "min"),
        last_hour=("hour", "max"),
        total_hours=("hour", "count"),
        median_obs_per_hour=("observations", "median"),
        min_obs_per_hour=("observations", "min")
    )
    .reset_index()
)

summary["hours_less_than_30_obs"] = (
    hourly["observations"] < 30
).groupby(hourly["series_id"]).sum().values

summary["hours_without_energy"] = (
    hourly["valid_energy"] == 0
).groupby(hourly["series_id"]).sum().values


# --------------------------------------------------
# 6. Print results
# --------------------------------------------------

print("\nRECENT 2025 COVERAGE BY SERIES\n")

print(
    summary.to_string(index=False)
)

# --------------------------------------------------
# 7. Proposed chronological split
# --------------------------------------------------

TRAIN_START = pd.Timestamp("2025-08-19 00:00:00", tz="UTC")
TRAIN_END = pd.Timestamp("2025-09-21 23:00:00", tz="UTC")

VAL_START = pd.Timestamp("2025-09-22 00:00:00", tz="UTC")
VAL_END = pd.Timestamp("2025-09-28 23:00:00", tz="UTC")

TEST_START = pd.Timestamp("2025-09-29 00:00:00", tz="UTC")
TEST_END = pd.Timestamp("2025-10-05 23:00:00", tz="UTC")


def assign_split(timestamp):

    if TRAIN_START <= timestamp <= TRAIN_END:
        return "train"

    elif VAL_START <= timestamp <= VAL_END:
        return "validation"

    elif TEST_START <= timestamp <= TEST_END:
        return "test"

    else:
        return "outside"


hourly["split"] = hourly["hour"].apply(assign_split)


# --------------------------------------------------
# 8. Check hourly coverage in each split
# --------------------------------------------------

split_summary = (
    hourly[hourly["split"] != "outside"]
    .groupby(["series_id", "split"])
    .agg(
        available_hours=("hour", "count"),
        hours_without_energy=("valid_energy",
                              lambda x: (x == 0).sum())
    )
    .reset_index()
)


print("\nCOVERAGE BY SERIES AND SPLIT\n")

print(
    split_summary.to_string(index=False)
)

# --------------------------------------------------
# 9. Historical 2020-2023 coverage
# --------------------------------------------------

historical = df[
    df["regime"] == "historical_2020_2023"
].copy()

historical["hour"] = historical["utc"].dt.floor("h")


historical_hourly = (
    historical
    .groupby(["series_id", "hour"])
    .agg(
        observations=("energy_Wh", "size"),
        valid_energy=("energy_Wh", "count")
    )
    .reset_index()
)


historical_summary = (
    historical_hourly
    .groupby("series_id")
    .agg(
        first_hour=("hour", "min"),
        last_hour=("hour", "max"),
        total_hours=("hour", "count"),
        hours_without_energy=(
            "valid_energy",
            lambda x: (x == 0).sum()
        )
    )
    .reset_index()
)


print("\nHISTORICAL 2020-2023 COVERAGE BY SERIES\n")

print(
    historical_summary.to_string(index=False)
)