"""Task 7 — central parameters.

Every value marked OPEN is a team decision that was not in the material I had
(S01–S04 were not part of the handover). Change it here only, never inside the
functions, so the JSON metadata of S09 always records what was used.
"""
import pandas as pd

TZ_LOCAL = "Europe/Madrid"

# Only the 2025 regime is minute-level (Task 2 cut, see load_frozen_dataset.py).
# The 2020–2023 regime is already hourly and is NOT processed by this pipeline.
REGIME_CUT_UTC = pd.Timestamp("2024-01-01", tz="UTC")

# S06 — an hour's energy is valid if it has at least THRESHOLD minute rows with energy_Wh.
# v1.0/v1.1: 30 (Task 6 coverage analysis). It excluded all SE/SW circuits although energy_Wh after a gap covers
# the gap. v1.2 (DECISIONS_v1.2.md D1): 1 = at least one reading; validity is decided by ENERGY_MAX_GAP instead.
THRESHOLD = 1

# S06 — catch-up guard. After an outage, the first row's energy_Wh contains the energy of the WHOLE gap
# (e.g. 10,229 Wh after a 1,006-min outage on 2025-09-17). An hour containing a row whose preceding gap is
# longer than ENERGY_MAX_GAP minutes is marked invalid. OPEN (addition to the S06 spec, needs team OK).
ENERGY_MAX_GAP = 15
# S06 v1.1 — pre-outage guard. If more than ENERGY_TAIL_MAX minutes at the END of an hour fall inside a gap
# longer than ENERGY_MAX_GAP, that energy is booked in a later catch-up row and the hour's sum is too low ->
# invalid (energy_pre_outage). 5 min = normal spacing between readings (same as MAX_GAP). 96 hours, all in train.
ENERGY_TAIL_MAX = 5
# S06b v1.2 (D2) — hour invalid if energy_Wh > CONSISTENCY_RATIO * W_mean + CONSISTENCY_TOL_WH (only checked where
# W_valid). Ratio 2 = Task 3 event definition; 1 Wh = counter resolution.
CONSISTENCY_RATIO = 2.0
CONSISTENCY_TOL_WH = 1.0
# D3 — hours with energy_Wh == 0 while W_mean > ZERO_WITH_POWER_W are counted, not flagged.
ZERO_WITH_POWER_W = 1.0

# S07 — a W/I reading "holds" until the next reading, but at most MAX_GAP minutes.
# OPEN. 5 min covers ~98 % of the gaps between readings in 2025.
MAX_GAP = 5
# S07 — hourly W/I mean is valid if the readings cover at least this many minutes.
# OPEN. Was set equal to THRESHOLD (30) in v1.0/v1.1; kept at 30 in v1.2 (S06b needs a reliable power mean).
MIN_COVERAGE_MIN = 30

# S08 — split boundaries as agreed in Task 6 (task6.pdf §4, task6_split_design.py), [start, end).
# Interpreted in UTC exactly like task6_split_design.py. 18 Aug (partial day) and everything after
# 5 Oct are "outside". Validation and test = 7 days = 168 hours each.
SPLIT_TZ = "UTC"
SPLITS = {
    "train":      ("2025-08-19 00:00", "2025-09-22 00:00"),
    "validation": ("2025-09-22 00:00", "2025-09-29 00:00"),
    "test":       ("2025-09-29 00:00", "2025-10-06 00:00"),
}
HOLIDAY_COUNTRY = "ES"
HOLIDAY_SUBDIV = "MD"

# S10
# v1.2: ELIGIBILITY_SHARE only marks "core" circuits for reporting (D5); it no longer decides what is modelled.
ELIGIBILITY_SHARE = 0.90
EXPECTED_HOURS = {"validation": 168, "test": 168}
# v1.2 (D4) — a circuit is used for TRAINING if it has >= MIN_TRAIN_HOURS valid training hours and at most
# MAX_FLAGGED_TRAIN_SHARE of its checked training hours flagged by S06b. Every circuit is forecast and scored.
MIN_TRAIN_HOURS = 168
MAX_FLAGGED_TRAIN_SHARE = 0.5
# D5 — the core-8 reporting table = the 8 circuits of Sprint 2/3 (fixed list, so v1.2 stays comparable).
CORE_8 = ["NE|HVAC", "NE|Plugs & Sockets", "NW|Emerg. Lighting", "NW|HVAC", "NW|Hand Dryer", "NW|Lighting",
          "NW|Plugs & Sockets", "NW|RACK"]
# D4b — a circuit needs at least MIN_SCALE_HOURS valid training hours for a scale (GBM/hybrid input).
MIN_SCALE_HOURS = 24

DATASET_VERSION = "1.0"          # frozen input version
DERIVED_VERSION = "1.2"          # derived hourly dataset (S09). 1.1 = pre-outage rule; 1.2 = gap rule + S06b (DECISIONS_v1.2.md)
ELIGIBILITY_FILE = f"derived/S10_eligibility_v{DERIVED_VERSION}.xlsx"

# ------------------------------------------------------------------ Task 7 baselines (S12–S18, S31)
# Team decisions of 18 Oct 2026:
#  - Day-ahead forecasts are issued at MIDNIGHT MADRID TIME and cover the 24 local hours of that day.
#    Split boundaries stay in UTC (Task 6). Every target hour is scored in the split its hour belongs to.
#  - Protocol §9 reworded: values observed before the issue time may be used as inputs (also from
#    validation/test); validation/test data are never used to fit or tune anything.
DERIVED_PATH = f"derived/Storey1_hourly_v{DERIVED_VERSION}.parquet"
ISSUE_TZ_DAY_AHEAD = "Europe/Madrid"
# horizon name -> leads. Lead L = the hour that starts (L-1) h after the issue time.
# Known at issue time tau: every hour that STARTS before tau (it has ended by tau).
HORIZONS = {"+1h": [1], "+6h": [6], "day-ahead": list(range(1, 25))}
BASELINE_TARGETS = ["energy_Wh"]
SEASONAL_LAG_H = 168                 # Baseline 1: same hour one week earlier
REGIME = "recent_2025"

# ------------------------------------------------------------------ Task 8 first ML model
# Decisions (18 Oct): gradient boosting only; fit on TRAINING data only, no refit on train+validation
# (protocol §4/§8/§9); configuration chosen on validation, then frozen; test used once.
PERSISTENCE_MAX_AGE_H = 24          # B3: last valid hour before the issue time, at most 24 h old
SEED = 0
GBM_FIXED = dict(loss="absolute_error", max_iter=300, early_stopping=False, l2_regularization=0.0)
GBM_GRID = [dict(learning_rate=lr, max_leaf_nodes=nl, min_samples_leaf=ms)
            for lr in (0.05, 0.1) for nl in (15, 31) for ms in (20, 50)]          # 8 configurations
MODEL_MODES = ["pooled", "per_series"]   # one model for all series vs one model per series (Task 5 §6)
# Selection metric, fixed before tuning: mean over series of (validation MAE / series training mean).
SELECTION_METRIC = "mean_scaled_MAE"
# v1.1 frozen configs keep their old names; v1.2 files carry the version.
FROZEN_CONFIG = "models/task8_frozen_config.json" if DERIVED_VERSION == "1.1" else f"models/task8_frozen_config_v{DERIVED_VERSION}.json"
CHRONOS_FROZEN_CONFIG = f"models/chronos_frozen_config_v{DERIVED_VERSION}.json"
HYBRID_FROZEN_CONFIG = f"models/hybrid_frozen_config_v{DERIVED_VERSION}.json"
TAG = f"v{DERIVED_VERSION}"                # suffix for v1.2 result files

# ------------------------------------------------------------------ v1.2 ChronosGBM hybrid (D7, D7b)
BLEND_WEIGHTS = [0.0, 0.25, 0.5, 0.75, 1.0]   # weight of GBM in w*GBM + (1-w)*Chronos q50

# ------------------------------------------------------------------ v1.3 extended grid (DECISIONS_v1.2.md D10, D11)
# Same dataset (v1.2), same splits, features, fixed GBM parameters, seed and selection metric (D6).
# Only the grids grow (teacher: >= 100 parameter combinations per model) and the choice follows rule D10.
TAG13 = "v1.3"
# Set to "YYYY-MM-DD — names" once the team has agreed D10 (and D10 option A/B). Every run_v13_*.py script
# refuses to run while this is None, so D10 is provably fixed before the first v1.3 score exists.
D10_AGREED = "2026-10-29 — Emily Wiesner, Alex (D10a: option B, D10b: 0.005, D10c: baselines tracked)"
D10_TIE_MARGIN = 0.005          # scaled MAE; candidates within this of the best are a tie
D10_IDENTICAL_EPS = 1e-6        # Wh; forecasts closer than this on every row count as identical
D10_INCLUDE_BASELINES = False   # D10a decided 29 Oct: option B — baselines are benchmarks, tracked, never chosen
# Simplicity order for ties (left = simplest). Baselines first, then zero-shot, then fitted, then combinations.
D10_SIMPLICITY = ["B3_persistence", "B1_last_week", "B2_weekday_hour_median",
                  "ML_Chronos", "ML_GBM", "ML_ChronosGBM", "ML_Blend"]

GBM_MODE_V13 = "pooled"         # pooled won every horizon in v1.1 and v1.2 for GBM and hybrid
GBM_GRID_V13 = [dict(learning_rate=lr, max_leaf_nodes=nl, min_samples_leaf=ms, l2_regularization=l2)
                for lr in (0.03, 0.05, 0.1, 0.2) for nl in (7, 15, 31, 63)
                for ms in (10, 20, 50, 100) for l2 in (0.0, 1.0)]                         # 4*4*4*2 = 128
CHRONOS_SIZES_V13 = ["tiny", "mini", "small", "base"]                                     # weights/chronos-bolt-<size>/
CTX_GRID_V13 = [24, 48, 72, 96, 120, 168, 240, 336, 420, 504, 588, 672, 816]              # 13
CHRONOS_POINTS_V13 = ["median", "mean_q"]   # q0.5, or mean of the 9 quantiles 0.1..0.9          -> 13*4*2 = 104
BLEND_STEP_V13 = 0.05                       # weights (GBM, ChronosGBM, Chronos) on a 0.05 grid, sum 1 -> 231
FROZEN_V13 = {m: f"models/{m}_frozen_config_{TAG13}.json" for m in ("task8", "chronos", "hybrid", "blend")}
CHRONOS_CACHE_V13 = f"results/chronos_cache_{TAG13}.parquet"
