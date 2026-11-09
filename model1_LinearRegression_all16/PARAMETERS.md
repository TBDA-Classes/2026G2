# Parameter table — Model 1, linear regression (all 16 circuits)

Same structure as Model 3's `PARAMETERS.md` (random forest). Types: **protocol** (defines the
experiment), **data** (decides which rows exist), **model** (my own hyperparameters).
Status: **frozen** · **open** · **tuned** · **spent**.

---

## 1. Protocol — never change

| Parameter | Value | Where | Status | If changed |
|---|---|---|---|---|
| `SPLITS.train` | 19 Aug – 22 Sep 2025 (end exclusive, so last day 21 Sep) | `config.py` | frozen | All models refit |
| `SPLITS.validation` | 22 – 29 Sep 2025 (last day 28 Sep) | `config.py` | frozen | All selection decisions void |
| `SPLITS.test` | 29 Sep – 6 Oct 2025 (last day 5 Oct) | `config.py` | frozen | All final numbers void |
| `SPLIT_TZ` | UTC | `config.py` | frozen | Every split boundary moves |
| `HORIZONS` | +1h, +6h, day-ahead (24 leads) | `config.py` | frozen | Results not comparable |
| `ISSUE_TZ_DAY_AHEAD` | Europe/Madrid, 00:00 local | `config.py` | frozen | Changes which hours day-ahead covers |
| Target | `energy_Wh` per hour | Task 5 spec | frozen | A different problem |
| Primary metric | MAE (RMSE secondary) | Sprint 3 plan | frozen | A different winner is possible |
| Selection metric | mean over **all 16** circuits of validation MAE ÷ circuit training mean | `task1_linear_all16.py` | **open** | Same definition as Model 3. Task 3 should fix one definition for everyone |
| Test-week use | once, after freezing | Sprint rule 3 | **spent 2 Nov** | `results/task1_linear_all16_TEST_ALREADY_RUN.txt` guards the script |
| `REGIME` | recent_2025 | `config.py` | frozen | 2020–2023 is a separate regime, not used |

## 2. Data — changing one means a new dataset version

Current dataset: `Storey1_hourly_v1.1` (sha256 `363dfdfa…66e8db8b`), built from frozen source `v1.0`.
Identical to the one used by the GBM (Task 8) and the random forest (Model 3).

| Parameter | Value | Where | Status | What it controls |
|---|---|---|---|---|
| `THRESHOLD` | 30 readings/hour | `config.py` | **open** | Minimum minute-readings for a valid hour. Decides that SE/SW are not trained on |
| `ELIGIBILITY_SHARE` | 0.90 | `config.py` | **open** | Share of valid hours needed to be a training circuit |
| `ENERGY_MAX_GAP` | 15 min | `config.py` | frozen | Outage catch-up guard |
| `ENERGY_TAIL_MAX` | 5 min | `config.py` | frozen | Pre-outage guard |
| `DERIVED_VERSION` | 1.1 | `config.py` | frozen | Bump on any change above |
| Weather variables | not used | `S1-B2 Data *.csv` | **open** | Same as all other models |
| UPM academic calendar | not used | `upm_calendar.xlsx` | **open** | Same as all other models |

## 3. Model — tuned on validation

Chosen 2 November, scoring **all 16 circuits** on the validation week. 2 designs × 9 settings × 3
horizons = 54 runs, all in `results/task1_linear_all16_tuning_log.csv`.

| Parameter | Searched | Chosen | Status | Notes |
|---|---|---|---|---|
| Loss | ridge (least squares + L2), LAD (median regression) | **LAD** at every horizon | tuned | LAD optimises absolute error, which is the metric. Ridge is pulled by a few huge hours |
| `alpha` (ridge) | 0.01, 1, 10, 100 | — | tuned | Lost to LAD everywhere |
| `alpha` (LAD) | 0, 0.0001, 0.001, **0.01, 0.1** (last two new) | **0.001** at every horizon | tuned | Now an interior optimum: 0.01 is worse at every horizon (e.g. day-ahead 0.395 → 0.407). Closes the "alpha at edge of grid" open point |
| Design / circuit identity | A: pooled with circuit dummies · B: pooled without | **B, without identity** | tuned | Wins at every horizon. Same choice as Model 3 |
| Mode | pooled only | pooled | decided | A per-circuit model cannot predict a circuit it never trained on |
| Training set | — | the 8 clean NE/NW circuits | decided 2 Nov | Same as Model 3. Predicts all 16 |
| Scaling | — | each circuit ÷ its own training mean | frozen | SE/SW are predicted from their own past values |
| Missing inputs | — | training median + 0/1 "was missing" column | frozen | Linear models need complete inputs |
| Numeric inputs | — | `last_val`, `mean_24`, `std_24`, `mean_168`, `lag_T24`, `lag_T168`, `wk_median`, `last_age_h`, `n_24`, `n_168`, `n_weeks`, `lead` (standardised) | frozen | From `task8_model.FEATURES`, shared with GBM and RF |
| Categorical inputs | — | `hour`, `weekday` (one-hot). `is_weekend` dropped (implied by weekday) | frozen | |
| Output | — | clipped at 0 Wh | frozen | Energy cannot be negative |
| Solver | — | `QuantileRegressor(quantile=0.5, solver="highs")` | frozen | Deterministic, no seed needed |

### Chosen per horizon

| Horizon | Design | Loss | alpha | Training rows | Fit cut-off (UTC) | Validation score (16 circuits) |
|---|---|---|---|---|---|---|
| +1h | B | LAD | 0.001 | 5,681 | 2025-09-22 00:00 | 0.340 |
| +6h | B | LAD | 0.001 | 5,641 | 2025-09-21 19:00 | 0.392 |
| day-ahead | B | LAD | 0.001 | 5,665 | 2025-09-21 22:00 | 0.395 |

## 4. Open points

- **Selection metric** and **THRESHOLD / ELIGIBILITY_SHARE**: same open decisions as Model 3 §4.
- **Earlier 8-circuit version (21 Oct)** used per-circuit +1h models with circuit dummies. Its
  test-week weakness (NE|HVAC spike on 3 Oct carried forward, +1h MAE 32.4 Wh) is gone in design B:
  NE|HVAC +1h test MAE is now 8.8 Wh. Honest note: the old test result was already known. Design B was picked because it is Model 3's design and it scored best on validation, not by tuning on test.
