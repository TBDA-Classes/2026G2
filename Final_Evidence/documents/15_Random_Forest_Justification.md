# Random Forest (Model 3) — how it was built, and why it is not the final model

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 18 Nov 2026
**Authors:** Émile (model owner, main author) · Claude (co-author)
**Model package:** `Model3_RandomForest.zip` (commit `0d882d7`, 27 Oct 2026): `README.md`, `PARAMETERS.md`, `RESULTS.md`, `models/task1_rf_final_config.json`, `results/`
**Comparison:** `Task6_rev0_03-11/RESULTS.md`, `results/task6_*_16circuits/`
**New check for this document:** `Final_Evidence/scripts/rf_checks.py` → `analysis/rf_d10_style_check.csv`, `analysis/rf_seed_noise.csv`
**Related:** `13_Prophet_Justification.md`, `14_Evaluation_Protocol_Justification.md`, `TBDA_v1.3_ChronosGBM_29-10/DECISIONS_v1.2.md` (D8, D10)

> **Reading note.** The Random Forest was frozen and tested on 27 Oct on dataset **v1.1**, one day before the v1.2 rules (28 Oct) and two days before the final choice (D10, 29 Oct). It is not part of the final model. This document justifies how it was built and shows why not choosing it was correct. Test numbers in Wh are the official Task 6 numbers (same 1,911 circuit-hours for every model).

## 1. Summary

- One **pooled** random forest per horizon (+1 h, +6 h, day-ahead), trained on the 8 NE/NW circuits, forecasting all 16. Same 15 inputs as the GBM and linear models.
- Settings chosen on validation in 4 stages (grid, seed repeats, one-standard-error rule, rolling-origin folds). Test week run once.
- Test MAE (16 circuits): **27.7 / 37.4 / 37.4 Wh** against **22.2 / 34.7 / 34.2 Wh** for the final Blend v1.3. Significantly worse at +1 h, tied at +6 h and day-ahead (`pairwise_differences.csv`).
- It was not a candidate in the final choice (D10). Had it been, it would not have been chosen at any horizon: on validation it is 0.07–0.10 above the best model in scaled MAE, 14–20 times the tie margin (§4).

## 2. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### R1 — Train on the 8 NE/NW circuits, forecast all 16

- **Decision.** Fit on NE and NW only. SE and SW are forecast from their own recent values, never trained on.
- **Why.** The data owner required forecasts for every circuit but allowed us to choose the training data if the choice is explained. In dataset v1.1, NE/NW had 99.4–100 % valid hours, SE/SW 34–89 %.
- **Evidence.** `README.md` §2; `task1_rf_final_config.json` (`training_circuits`, `predicted_circuits`).
- **Alternative rejected.** Training on all 16 with the v1.1 rules: SE/SW would bring few, gappy hours.
- **Weakness.** This is where the forest loses most (§4): on SE/SW it is significantly worse than the Blend at every horizon (+10.0 / +12.5 / +10.5 Wh). The v1.3 models were trained on 15 circuits including SE/SW (v1.2 rules).

### R2 — One pooled model, without circuit identity (design B), each circuit scaled by its training mean

- **Decision.** One model for all circuits. No circuit dummies. Every value input and the target are divided by the circuit's own training mean, and forecasts are multiplied back.
- **Why.** A model per circuit cannot forecast a circuit it never saw, so with R1 pooling is needed. Scaling makes a 0.9 Wh/h hand dryer and a 563 Wh/h plug circuit comparable.
- **Evidence.** Design A (with dummies) vs B on unseen circuits, validation scaled MAE: 0.3857 vs 0.3835 (+1 h), 0.5351 vs 0.5323 (+6 h), 0.5594 vs 0.5602 (day-ahead) (`results/task1_rf_all16_per_circuit.csv`). A tie, so the simpler design was kept.
- **Alternative rejected.** Design A, and one model per circuit.
- **Weakness.** "Pooled beat per-circuit at every horizon" (`README.md` §2) has no result file in the package.

### R3 — Same 15 inputs as the GBM and linear models

- **Decision.** Use `task8_model.FEATURES`: recent values, 24 h / 168 h means, same hour 24 h and 168 h before, 4-week hourly median, age of last value, counts, hour, weekday, weekend, hours ahead.
- **Why.** So that a difference between models comes from the algorithm, not from the inputs. Only information known at forecast time (assertions in `build_features`, inherited from Task 8).
- **Alternative rejected.** Adding weather or the UPM calendar. Both were in the repository; adding them to one model only would break the like-for-like comparison.
- **Weakness.** No external inputs. (The later temperature test on the GBM gave a gain below the tie margin, D12.)

### R4 — `absolute_error` split criterion

- **Decision.** Trees split on absolute error, not squared error.
- **Why.** MAE is the primary metric; the model optimises what it is scored on, and it is less pulled by spikes.
- **Evidence.** Best grid score per criterion (`results/step3_stage1_grid.csv`): 0.314 vs 0.353 (+1 h), 0.420 vs 0.490 (+6 h), 0.424 vs 0.493 (day-ahead). Squared error is 12–17 % worse.
- **Alternative rejected.** `squared_error` (scikit-learn default).
- **Weakness.** Slower to fit.

### R5 — How the settings were chosen

- **Decision.** (1) Grid: 60 configurations per horizon (criterion × depth 4/6/8/12/none × min leaf 10/30/60 × max features 0.5/1.0), scored on all 16 circuits. (2) 5 seeds on the 6 leaders. (3) One-standard-error rule: among configurations within 1 SE of the best, the simplest. (4) Three rolling-origin folds inside the training period. Min leaf extended past the grid edge (60 won) up to 1,400 until the score turned. Search at 100 trees, final models at 300.
- **Why.** One validation week is a small sample, and NW HVAC was on standby all that week. Seeds separate real differences from noise; folds check that the choice does not depend on that one week.
- **Evidence.** `RESULTS.md` §4, `results/step3_*.csv`. Final: +1 h depth 12, leaf 100, all features; +6 h and day-ahead depth 4, leaf 250, half the features. Min leaf 250 is an interior optimum at the long horizons (0.409 at 250 vs 0.422 at 400 and 0.415 at 100, +6 h).
- **A trap the folds caught.** The folds first reversed the ranking at +6 h and day-ahead. Cause: min leaf is a count, and the folds train on 2,000–4,550 rows against 5,650. With min leaf as a share of training rows, folds and official week agreed at every horizon (`step3_rolling_fractional.csv`).
- **Alternative rejected.** Choosing on the validation week alone; random search.
- **Weakness.** Seed noise is larger than the README says (§5). After seed averaging, the top 6 are only 0.4–0.5 % apart at +1 h and +6 h, so the choice among them is close to arbitrary. The 1-SE rule handles this, but it should be said.

### R6 — No persistence fallback at day-ahead

- **Decision.** Keep the forest alone, even for unseen circuits at day-ahead.
- **Why.** Keep the model pure and the comparison clean.
- **Evidence.** On validation, persistence beat the forest on unseen circuits at day-ahead (0.341 vs 0.484). On the test week, the forest won there (0.363 vs 0.427) (`RESULTS.md` §1–2).
- **Weakness.** Decided before the test, so no bias, but the validation evidence pointed the other way.

### R7 — Eligibility rule left unchanged (`THRESHOLD = 30`)

- **Decision.** Do not change the data rule inside Model 3, even though our measurements showed it was wrong.
- **Why.** It is a data parameter. Changing it rebuilds the dataset and forces every frozen model to re-run, so it is a team decision, not a model decision (`PARAMETERS.md` §0).
- **Evidence.** SE/SW fail the reading count because they sample more slowly, not because energy is missing: their longest gap in failing hours is 12–13 min (median), against 90 min for real NE/NW outages. A gap-based rule would move SE from 76.3 % to 90.1 % valid hours and SW from 74.7 % to 89.0 % (`PARAMETERS.md` §4).
- **What happened next.** v1.2 rule D1 (28 Oct) dropped the reading count with the same reason: "SE/SW were excluded by the row count, not by missing energy". D1 does not cite the RF finding, so say "same conclusion, one day later", not "caused by".

## 3. Result

Test week, 16 circuits, same 1,911 hours per horizon (`Task6_rev0_03-11/RESULTS.md` §1, `pairwise_differences.csv`):

| MAE (Wh) | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| **Blend v1.3 (final model)** | **22.2** | **34.7** | **34.2** |
| GBM v1.3 | 26.3 | 37.1 | 35.7 |
| Random Forest | 27.7 | 37.4 | 37.4 |
| B3 persistence | 24.0 | 57.8 | 41.5 |
| B2 weekday × hour median | 43.7 | 43.7 | 43.7 |
| RF − Blend (95 % CI) | +5.6 (+3.8 to +7.5) **worse** | +2.6 (−0.8 to +5.6) tie | +3.2 (−2.2 to +7.5) tie* |

\* Significant in scaled MAE.

- **Strengths.** Beats B2 significantly at every horizon, and persistence at +6 h. Tied with GBM v1.3 in Wh at every horizon. On the 8 NE/NW circuits it is tied with the Blend at +6 h and day-ahead.
- **Where it loses.** SE/SW (never trained on) and +1 h, where it is also significantly worse than persistence (+3.8 Wh).

## 4. Why it is not the final model

1. **It was not a candidate.** The v1.2 decisions (28 Oct) list the models carried into the final test (D8: baselines, Chronos, GBM, Blend, ChronosGBM), and D10 chooses only among Chronos, GBM, ChronosGBM and Blend. The forest stayed on v1.1 and was only compared afterwards, in Task 6. **[Émile: reason not written in the repo. Add one line.]**
2. **Had it been a candidate, D10 would not have picked it.** Mean scaled MAE on validation, 15 training circuits, Task 6 common hours (`analysis/rf_d10_style_check.csv`):

| Validation, scaled MAE | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| Best model | 0.209 (ChronosGBM) | 0.285 (ChronosGBM) | 0.282 (Chronos) |
| Blend v1.3 | 0.215 | 0.290 | 0.289 |
| GBM v1.3 | 0.225 | 0.350 | 0.345 |
| Random Forest | 0.281 | 0.385 | 0.385 |
| Gap RF − best | 0.072 | 0.100 | 0.102 |

   The tie margin is 0.005. The forest is also below GBM v1.3, the other tree model with the same inputs, at every horizon. These are not the official D10 scores (0.271 / 0.349 / 0.351 for the Blend), which use each model's own valid hours; here every model is scored on the same hours.
3. **The test confirms it** (§3): never better than the Blend, significantly worse at +1 h.

**Limit of this comparison.** It is not forest vs boosting on equal terms: the forest used v1.1 and 8 training circuits, the v1.3 models v1.2 and 15. A forest retrained on v1.2 was not tested. The honest conclusion is "this forest is not better than the final model", not "random forests are worse".

## 5. Corrections to the model package (numbers to retire)

| Where | Old statement | Correct |
|---|---|---|
| `README.md` header | "Best model in the project at +6h and day-ahead" | Only among Sprint 3 models, 8 circuits, v1.1. Retire: the Blend v1.3 is lower at every horizon |
| `README.md` §2, `PARAMETERS.md` §3 | absolute_error "wins by 12–16 %" | Squared error is 12–17 % worse (0.353 vs 0.314, 0.490 vs 0.420, 0.493 vs 0.424) |
| `README.md` §4, `PARAMETERS.md` §3 | Seed noise "0.1–0.2 % of the score"; top-6 spread "0.6–2.7 %" | Seed sd 0.2–0.7 %; standard error of the 5-seed mean 0.1–0.3 % (`analysis/rf_seed_noise.csv`). 0.6–2.7 % is the single-seed spread; after seed averaging 0.4 / 0.4 / 1.6 % |
| `PARAMETERS.md` §3 | `max_features` searched 0.33, 0.5, 1.0 | The grid file has 0.5 and 1.0 only |
| `README.md` §2, `step3_tuning.py` | "100 vs 300 trees: identical ranking, within 0.15 %" | Plausible, but no result file. Say it as "checked during development" |
| `PROTOCOL_NOTE_v1.2.md` §1, doc 14 (weakness of the test split) | Sprint 3 test-week users: baselines, GBM v1.0, linear, Chronos, on 8 NE/NW circuits | The forest also used the test week, on 27 Oct, on **all 16 circuits** (`task1_rf_TEST_ALREADY_RUN.txt`). SE/SW test scores existed before the v1.2 rules |

## 6. What the model still gave the project

- **Parameter table template** (`PARAMETERS.md`): protocol / data / model parameters, asked for by the data owner on 26 Oct.
- **The eligibility finding** (R7): same conclusion as v1.2 D1.
- **Persistence is hard to beat at +1 h.** The forest and GBM found it independently; Task 6 confirms it for every model.
- **Simple wins at long horizons:** the best day-ahead forest is depth 4, about 16 leaves, close to a lookup table.

## 7. Likely questions

| Question | Short answer |
|---|---|
| Why a random forest? | A standard non-linear model, robust with little tuning, and a tree-based check against the GBM. |
| Why train on 8 circuits only? | In v1.1 only NE/NW had near-complete data. The data owner allowed us to choose. |
| How can it forecast circuits it never saw? | It has no circuit identity and works on scaled recent values, so any circuit with history can be forecast. |
| Why absolute error? | MAE is the metric; it scored 12–17 % better than squared error. |
| Why is the day-ahead model so shallow? | With 5 weeks of data, there is little to learn at that horizon. Deeper trees overfit. |
| Why not use it? | Not better than the Blend on validation or test, and it would not have passed D10. |
| Is the comparison fair? | Same hours and metric, but not the same training data (v1.1, 8 circuits vs v1.2, 15). We say so. |
