"""Central settings of the Sprint 4 Task 3 dashboard (paths, labels, flags).

It works with two folder layouts:
  * repository clone:  2026G2/Sprint4_Task3_UX_Dash (this app), 2026G2/TBDA_v1.3_ChronosGBM_29-10, 2026G2/Task6_rev0_03-11
  * minimal package:   <folder>/app (this app), <folder>/model, <folder>/task6_results, <folder>/outputs
Override the root with the environment variable TBDA_REPO if the app folder is moved.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent       # app folder (core/ and engines/ are inside it)
CORE_DIR = APP_DIR / "core"
ENGINES_DIR = APP_DIR / "engines"                        # scripts the app runs in a separate process
REPO = Path(os.environ.get("TBDA_REPO", APP_DIR.parent)).resolve()


def _first(*names: str) -> Path:
    """First folder that exists under REPO (minimal-package name first, repository name second)."""
    for n in names:
        if (REPO / n).exists():
            return REPO / n
    return REPO / names[-1]


# files the app writes (recomputed forecasts, live forecast, new data, detection test)
OUT_DIR = REPO / "outputs" if (REPO / "outputs").exists() else APP_DIR

# --- Final model (Sprint 3 decision D10, confirmed by Sprint 4 Task 2: temperature not adopted) -------------
MODEL_NAME = "Blend v1.3"
MODEL_FILE_TAG = "ML_Blend_v1.3"
MODEL_DIR = _first("model", "TBDA_v1.3_ChronosGBM_29-10")          # frozen components, configs, Chronos caches, dataset v1.2
BLEND_CONFIG = MODEL_DIR / "models" / "blend_frozen_config_v1.3.json"

# --- Stored forecasts and official scores (Task 6, 3 Nov 2026) --------------------------------------------
TASK6 = _first("task6_results", "Task6_rev0_03-11")
PRED_DIR = TASK6 / "results" / "predictions"
METRICS = {
    "test": TASK6 / "results" / "task6_test_16circuits",
    "validation": TASK6 / "results" / "task6_validation_16circuits",
}
EVENTS_FILE = TASK6 / "data" / "task6_events_test.csv"
SCALE_FILE = TASK6 / "data" / "task6_circuit_scale_train_mean_v1.2.csv"

# --- Forecasts recomputed by the app from the frozen model ("Model" page) ---------------------------------
CACHE_DIR = OUT_DIR / "cache"

# --- New measurements (scalability): update_data.py writes the rebuilt hourly dataset here ------------------
LIVE_DATA_DIR = OUT_DIR / "data_live"

# --- Detection test (engines/injection_test.py) ---------------------------------------------------------
VAL_DIR = OUT_DIR / "analysis"          # same folder and file names as the Energy Watch test, + suffix _dash


def current_derived():
    """Hourly dataset used for the live forecast and the data-quality checks: the newest one available."""
    new = LIVE_DATA_DIR / "Storey1_hourly_v1.2.parquet"
    return new if new.exists() else MODEL_DIR / "derived" / "Storey1_hourly_v1.2.parquet"

# --- Prediction intervals ------------------------------------------------------------------------------
# Task 3: "Add prediction intervals if validated by Pole 1". Until Pole 1 signs them off, the interval
# switch is OFF by default and every interval is labelled "experimental". Set to True after validation.
INTERVALS_VALIDATED = False
INTERVAL_LEVEL = 0.90          # nominal coverage of the forecast interval
INTERVAL_METHOD = "cqr"        # "cqr" = Chronos q10-q90 band calibrated per circuit (conformal); "abs" = symmetric
                               # split-conformal around the forecast (used automatically where Chronos quantiles miss)
INTERVAL_MIN_N = 30            # fewer validation residuals for a circuit -> use the horizon-wide quantile

# --- Labels ---------------------------------------------------------------------------------------------
TZ_LOCAL = "Europe/Madrid"
SPLITS = {
    "test": "Test week · 29 Sep – 5 Oct 2025",
    "validation": "Validation week · 22 – 28 Sep 2025",
}
HORIZONS = {1: "+1 h", 6: "+6 h", 24: "Day-ahead"}
HORIZON_KEYS = {1: "+1h", 6: "+6h", 24: "day-ahead"}       # labels used in the Task 6 files
HORIZON_HELP = {
    1: "Forecast made one hour before each hour. Use it for short-term operation.",
    6: "Forecast made six hours before each hour. Use it to plan the rest of the shift.",
    24: "Forecasts for the whole next day, issued every day at 00:00 Madrid time (lead 1–24 h).",
}
ZONES = ["NE", "NW", "SE", "SW"]
ZONE_HELP = {
    "NE": "North-east wing (2 circuits)",
    "NW": "North-west wing (6 circuits)",
    "SE": "South-east wing (4 circuits)",
    "SW": "South-west wing (4 circuits)",
}
LOAD_TYPES = {                 # text after "|" in the circuit name -> label shown in the interface
    "HVAC": "HVAC",
    "Lighting": "Lighting",
    "Plugs & Sockets": "Plugs & sockets",
    "Emerg. Lighting": "Emergency lighting",
    "Hand Dryer": "Hand dryers",
    "RACK": "IT rack",
}

# --- Colours (validated reference palette of the dataviz method, light mode) ------------------------------
COLORS = {
    "actual": "#1f2933",       # ink: measured consumption
    "forecast": "#2a78d6",     # series 1: forecast
    "band": "rgba(42,120,214,0.16)",
    "grid": "#e6e5e0",
    "muted": "#52514e",
    "seq": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
    "good": "#1baf7a",
    "warning": "#eda100",
    "critical": "#e34948",
    "future": "rgba(42,120,214,0.06)",
    "actual_fill": "rgba(31,41,51,0.06)",
}
# One fixed colour per zone (validated categorical slots, light mode; always shown with a text label)
ZONE_COLORS = {"NE": "#1baf7a", "NW": "#eb6834", "SE": "#6250d6", "SW": "#e87ba4"}
