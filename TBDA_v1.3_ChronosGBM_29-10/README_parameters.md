# Parameters — everything we can change and test

All settings that influence a result, in one table. Values are those of **dataset v1.2** (28 Oct, `DECISIONS_v1.2.md`). Where v1.1 differed, the old value is
given in the notes. Frozen choices per model are in `models/*_frozen_config_v1.2.json`.

**Type** says what breaks if you change it. **Status** says whether you may.

| Type | Changing it means |
|---|---|
| **Protocol** | Old and new results are no longer comparable. Do not change. |
| **Data** | New derived dataset version (`DERIVED_VERSION`), then re-run S05–S10, all baselines and all models. |
| **Model** | Re-fit and re-score that model on validation only. Test stays untouched. |

| Status | Meaning |
|---|---|
| `frozen` | Fixed by the protocol or by a fact of the data. Not a candidate for testing. |
| `open` | A choice we made but never tested. A candidate for a sensitivity run. |
| `tuned` | Chosen on validation from the grid shown, then frozen in `models/*_frozen_config.json`. |

## 1. Protocol

| Parameter | File | Value | Status | Notes |
|---|---|---|---|---|
| `SPLITS` | config.py | train 19.08–21.09, validation 22.09–28.09, test 29.09–05.10 (2025, `[start, end)`) | frozen | Task 6 §4. 18.08 and after 05.10 = `outside`. |
| `SPLIT_TZ` | config.py | `UTC` | frozen | Same as `task6_split_design.py`. |
| `REGIME_CUT_UTC` / `REGIME` | config.py | 2024-01-01 / `recent_2025` | frozen | Only the 2025 minute-level data is processed. |
| `HORIZONS` | config.py | +1h = lead 1, +6h = lead 6, day-ahead = leads 1–24 | frozen | |
| `ISSUE_TZ_DAY_AHEAD` | config.py | 00:00 `Europe/Madrid` | frozen | Team decision 18.10. |
| Inputs rule | task8_model.py | only hours that start before the issue time | frozen | Asserted in `build_features` and `chronos_model.context`. |
| Fit rule | config.py comment | fit on train only, no refit on train+validation, test used once | frozen | Protocol §4/§8/§9. |
| Metric | task7_pipeline.py (S11) | MAE (main), RMSE (secondary), on the common mask of valid pairs | frozen | |
| `SELECTION_METRIC` | config.py | `mean_scaled_MAE` = mean over the **training circuits** of validation MAE / circuit training mean | frozen | Fixed before tuning (v1.2 D6: training circuits, not all 16, because per-series models cannot forecast cold-start circuits). |
| `BASELINE_TARGETS` | config.py | `energy_Wh` | frozen | |
| B1 `SEASONAL_LAG_H` | config.py | 168 h (same hour last week) | frozen | Baselines are the bar every model is measured against. |
| B2 | task7_baselines.py | median per circuit × weekday × hour over train | frozen | |
| B3 `PERSISTENCE_MAX_AGE_H` | config.py | last valid hour, at most 24 h old | frozen | |
| `SEED` | config.py | 0 | frozen | |
| `EXPECTED_HOURS` | config.py | validation 168, test 168 | frozen | Follows from `SPLITS` (no DST change in the window). |

## 2. Data — changing one means a new dataset version and re-running everything

| Parameter | File | Value | Status | Affects | Notes |
|---|---|---|---|---|---|
| `THRESHOLD` | config.py | 1 (at least one reading) | frozen (D1) | `energy_valid` | v1.1: 30, which excluded all SE + SW. Removed as a rule: `energy_Wh` after a gap covers the gap. |
| `ENERGY_MAX_GAP` | config.py | 15 min | open | `energy_valid` (catch-up guard) | The main validity rule since v1.2. Sensitivity 15 / 20 / 30 in the `gap_sensitivity` sheet of `S10_eligibility_v1.2.xlsx`. |
| `ENERGY_TAIL_MAX` | config.py | 5 min | open | `energy_valid` (pre-outage guard) | Since v1.1. |
| `CONSISTENCY_RATIO`, `CONSISTENCY_TOL_WH` | config.py | 2, 1 Wh | open (D2) | `energy_valid` (S06b) | Hour invalid if energy > 2 × mean power + 1 Wh; checked only where power is valid. Task 3 event definition; 1 Wh = counter resolution. |
| `ZERO_WITH_POWER_W` | config.py | 1 W | open (D3) | report only | Hours with zero energy while power > 1 W are counted, not flagged. |
| `MIN_TRAIN_HOURS`, `MAX_FLAGGED_TRAIN_SHARE` | config.py | 168 h, 0.5 | open (D4) | which circuits are used to FIT models | Same rule for all circuits. v1.2: SE Plugs & Sockets fails both (152 h, 86 % flagged) → forecast as cold-start. |
| `MIN_SCALE_HOURS` | config.py | 24 h | open (D4b) | whether a circuit gets a scale (GBM inputs) | |
| `ELIGIBILITY_SHARE` | config.py | 0.90 of expected hours, in validation **and** test | open (D5) | `high_coverage` column (reporting only) | v1.1: decided which circuits were modelled. |
| `CORE_8` | config.py | the 8 NE/NW circuits of Sprint 2/3 | frozen (D5) | core-8 reporting table | Fixed list so v1.2 stays comparable with Sprint 2/3. |
| Circuit lists | `S10_eligibility_v1.2.xlsx` → `eligible_series(which=…)` | all = 16, training = 15 | derived | every model | No script hard-codes a list any more. |
| `MAX_GAP` | config.py | 5 min | open | `W_mean`, `I_mean` only | Not a model input today, so no effect on current results. |
| `MIN_COVERAGE_MIN` | config.py | 30 min | open | `W_valid`, `I_valid` only | Same: no effect on current results. |
| `HOLIDAY_COUNTRY` / `HOLIDAY_SUBDIV` | config.py | ES / MD | open | `is_holiday` | No holiday in the 2025 window. Madrid city holidays and UPM closing days are not included. |
| `TZ_LOCAL` | config.py | `Europe/Madrid` | frozen | calendar features | A fact, not a choice. |
| `DATASET_VERSION` / `DERIVED_VERSION` | config.py | 1.0 / 1.2 | bookkeeping | file names, META.json | Bump `DERIVED_VERSION` on every data change. |

## 3. Model

### 3a. Inputs shared by GBM and linear model (`task8_model.py`)

| Parameter | Value | Status | Notes |
|---|---|---|---|
| `FEATURES` | `last_val, mean_24, std_24, mean_168, lag_T24, lag_T168, wk_median, last_age_h, n_24, n_168, n_weeks, hour, weekday, is_weekend, lead` | open | Same set for every ML model; never varied. |
| Lags | 24, 168, 336, 504, 672 h | open | `wk_median` = median of the 4 weekly lags. |
| Trailing windows | 24 h, 168 h | open | |
| Scaling | value features ÷ circuit training mean | open | A circuit needs valid training hours to get a scale (`ValueError` otherwise). |
| Output clip | predictions ≥ 0 | frozen | Energy cannot be negative. |

### 3b. Gradient boosting — Task 8 (`config.py`, `task8_model.py`; v1.2: `run_v12_gbm_tune.py`)

| Parameter | Value / grid | Status | Chosen v1.1 (+1h / +6h / day-ahead) | Chosen v1.2 |
|---|---|---|---|---|
| `MODEL_MODES` | pooled, per_series | tuned | pooled / pooled / pooled | pooled / pooled / pooled |
| `learning_rate` | 0.05, 0.1 | tuned | 0.05 / 0.05 / 0.1 | 0.1 / 0.05 / 0.1 |
| `max_leaf_nodes` | 15, 31 | tuned | 15 / 15 / 15 | 31 / 15 / 15 |
| `min_samples_leaf` | 20, 50 | tuned | 50 / 20 / 50 | 50 / 20 / 50 |
| `loss` | `absolute_error` | open | Fixed in `GBM_FIXED`, matches MAE. | same |
| `max_iter` | 300 | open | Not tuned, no early stopping. | same |
| `early_stopping` | False | open | | same |
| `l2_regularization` | 0.0 | open | | same |

Pooled mode passes the circuit as a categorical input (`series_code`).

### 3c. Linear model — Sprint 3 (`task1_linear.py`)

| Parameter | Value / grid | Status | Chosen (+1h / +6h / day-ahead) |
|---|---|---|---|
| Mode | pooled, per_series | tuned | per_series / pooled / pooled |
| `loss` + `alpha` | ridge α ∈ {0.01, 1, 10, 100}; LAD α ∈ {0, 1e-4, 1e-3} | tuned | LAD 1e-3 / LAD 1e-3 / LAD 1e-3 |
| Categorical inputs | hour, weekday (one-hot); + circuit in pooled mode | open | `is_weekend` dropped (implied by weekday). |
| Imputation | median + missing indicator, then `StandardScaler` | open | |

### 3d. Chronos-Bolt — Sprint 3 (`chronos_model.py`)

| Parameter | Value / grid | Status | Chosen (+1h / +6h / day-ahead) |
|---|---|---|---|
| `CTX_GRID` (context length) | 168, 336, 504, 672 h | tuned | v1.1: 168 / 504 / 504; v1.2: 672 / 504 / 168 |
| Weights | `chronos-bolt-small` | open | Larger sizes not tested. Zero-shot: nothing fitted on our data. |
| `QUANTILES` | 0.1, 0.5, 0.9 | open | |
| Point forecast | median (0.5), clipped at 0 | frozen | MAE-optimal for a quantile forecast. |
| `PRED_LEN` | 24 | frozen | Follows from `HORIZONS`. |
| `BATCH` | 64 | — | Speed only, no effect on results. |

### 3e. ChronosGBM hybrid and blend — v1.2 (`hybrid_model.py`, `run_v12_hybrid_tune.py`)

| Parameter | Value / grid | Status | Chosen (+1h / +6h / day-ahead) |
|---|---|---|---|
| Inputs | Task 8 features + `chr_q10`, `chr_q50`, `chr_q90`, `chr_width` (÷ circuit scale) + `chr_ctx_h` | open (D7) | — |
| Chronos context | frozen v1.2 Chronos value per horizon | follows 3d | 672 / 504 / 168 |
| Mode, `learning_rate`, `max_leaf_nodes`, `min_samples_leaf` | same grid as 3b | tuned | pooled, 0.05, 31, 20; pooled, 0.05, 31, 50; pooled, 0.1, 31, 20 |
| Fixed parameters, seed | same as 3b | open | — |
| `BLEND_WEIGHTS` (weight of GBM vs Chronos median) | 0, 0.25, 0.5, 0.75, 1 | tuned (D7b) | 0.5 / 0.0 / 0.0 |

## Where the values live

The values are split over `config.py` (data, protocol, GBM, blend), `task8_model.py` (features),
`hybrid_model.py` (hybrid inputs), `task1_linear.py` (linear grid) and `chronos_model.py` (Chronos grid). The frozen configs in `models/`
record what each run actually used. When you change a value, change it in the code file listed above
and update this table in the same commit.

### 3f. Extended grid v1.3 (`config.py` block "v1.3", `selection.py`, `run_v13_*.py`)

| Model | Parameter | Values | Count |
|---|---|---|---|
| GBM, ChronosGBM | `learning_rate` × `max_leaf_nodes` × `min_samples_leaf` × `l2_regularization` | {0.03, 0.05, 0.1, 0.2} × {7, 15, 31, 63} × {10, 20, 50, 100} × {0, 1}; pooled | 128 each |
| Chronos-Bolt | size × context × point forecast | {tiny, mini, small, base} × {24, 48, 72, 96, 120, 168, 240, 336, 420, 504, 588, 672, 816} × {median, mean of 9 quantiles} | 104 |
| Blend | (w_gbm, w_hybrid, w_chronos) | 0.05 grid, sum 1 | 231 |
| Selection | D10 | tie margin 0.005 scaled MAE, tie-break mean scaled RMSE, identical → simpler | — |
