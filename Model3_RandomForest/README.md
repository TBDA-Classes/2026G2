# Model 3 — Random forest

**Sprint 3, Task 1 · CeDInt Storey 1 energy forecasting · Group 2 · ETSII-UPM**
Owner: Émile. Frozen and tested 27 October 2026.

Forecasts `energy_Wh` for **all 16 circuits** of Storey 1 at +1 hour, +6 hours and day-ahead.

| | |
|---|---|
| Best model in the project at | **+6h and day-ahead** |
| Best machine-learning model at | **+1h** (only persistence is better) |
| Circuits predicted | 16 of 16 |
| Circuits trained on | 8 (NE and NW) |
| Status | frozen, test week spent |

Parameters: `PARAMETERS.md`. That file is also the template for other models.

---

## 1. What the model does

One pooled random forest per horizon. For each circuit and hour it predicts the energy
consumed in that hour, using only information available when the forecast is made.

**Inputs** (15, identical to the gradient boosting and linear models so the comparison is
like-for-like): last valid hour, mean and spread of the last 24 h, mean of the last 168 h, the
same hour 24 h and 168 h earlier, the median of that hour over 4 weeks, how old the last value
is, how many values each window contained, hour of day, weekday, weekend flag, and hours ahead.

Every value feature is divided by that circuit's own training average, so a 0.9 Wh/h hand dryer
and a 563 Wh/h plug circuit look comparable to the model. Predictions are multiplied back.

**Chosen settings**

| Horizon | criterion | max_depth | min_samples_leaf | max_features |
|---|---|---|---|---|
| +1h | absolute_error | 12 | 100 | 1.0 |
| +6h | absolute_error | 4 | 250 | 0.5 |
| day-ahead | absolute_error | 4 | 250 | 0.5 |

Fixed everywhere: 300 trees, bootstrap on, `random_state = 0`.

## 2. Decisions, and why

| Decision | Choice | Reason |
|---|---|---|
| **Train on 8 circuits, predict 16** | NE and NW only for training | The data owner requires forecasts everywhere but allows us to choose what we learn from. NE/NW have 99.4–100 % valid hours; SE/SW have 34–89 %. SE/SW are still forecast, from their own history |
| **No circuit identity** (design B) | model never learns circuit names | Tested against a version with one-hot circuit dummies: identical accuracy on unseen circuits (0.3835 vs 0.3857). Simpler, and nothing special happens when a circuit is added later |
| **absolute_error, not squared_error** | — | MAE is the primary metric; optimising the same quantity you measure wins by 12–16 % at every horizon |
| **Pooled, not one model per circuit** | one model for all | Won at every horizon. Circuits share patterns, and per-circuit models get too little data each |
| **No persistence fallback at day-ahead** | pure forest | Considered before freezing, because on validation persistence beat the forest on untrained circuits (0.341 vs 0.484). Rejected to keep the model pure and the comparison clean. The test week then showed the forest winning there (0.363 vs 0.427), so the decision held |
| **Eligibility rule left unchanged** | `THRESHOLD = 30` kept | Our evidence says it is miscalibrated (see §6), but changing it rebuilds the dataset and forces every frozen model in the project to re-run. Documented as a Sprint 4 recommendation instead |
| **Search at 100 trees, deliver at 300** | — | Identical ranking, scores within 0.15 %, three times faster. Verified, not assumed |

## 3. Assumptions

These are things the model takes as true. If one is wrong, the results move.

1. **The hourly dataset v1.1 is correct.** We inherit Alex's Task 7 pipeline whole: hourly
   aggregation, validity rules, leakage checks, 26 tests.
2. **`energy_Wh` is the right target** and is correctly derived. Verified independently: it
   equals the increment of the `Er` counter to within the stored rounding on 100 % of
   counter-derived rows, in both the 2025 and the 2020–2023 regimes.
3. **A circuit's own past predicts its future**, including for circuits never trained on. This
   is what makes train-8 / predict-16 possible, and it holds in the test week.
4. **The validation week is representative enough to select on.** Partly checked: NW|HVAC was
   on standby all validation week (coefficient of variation 0.03, against 0.69–1.21 in every
   other week), so the week is not typical. Rolling-origin folds were added because of this.
5. **The 2025 and 2020–2023 regimes must stay separate.** The counters reset between them in
   16 of 17 series, and there is a 2.5-year gap.
6. **Missing means missing.** Never filled with zero, anywhere.
7. **Only information available at the forecast time is used.** Enforced by assertions in
   `build_features`, inherited from Task 8.

## 4. How the parameters were chosen

Four stages. Full detail in `PARAMETERS.md` §5.

1. **Grid** — 60 configurations per horizon, scored on all 16 circuits.
2. **Seed repetition** — 5 seeds on the leaders. Seed noise is 0.1–0.2 % of the score; top-6
   spreads were 0.6–2.7 %. So most differences are real, but not all.
3. **One-standard-error rule** — among configurations within one SE of the best, take the
   simplest.
4. **Rolling-origin folds** — three expanding windows inside the training period, to avoid
   selecting on a single week.

The test week was run **once**, after all of this, and cannot be re-run.

## 5. Results

### Validation week (22–28 Sep), all 16 circuits, scaled MAE

| Horizon | B1 | B2 | B3 | **Forest** |
|---|---|---|---|---|
| +1h | 0.599 | 0.522 | 0.353 | **0.314** |
| +6h | 0.597 | 0.521 | 0.474 | **0.408** |
| day-ahead | 0.598 | 0.522 | **0.360** | 0.408 |

### Test week (29 Sep – 5 Oct), run once

All 16 circuits — only this model covers them:

| Horizon | B1 | B2 | B3 | **Forest** |
|---|---|---|---|---|
| +1h | 0.894 | 0.775 | **0.630** | 0.663 |
| +6h | 0.893 | 0.774 | 1.203 | **0.749** |
| day-ahead | 0.893 | 0.775 | 0.793 | **0.750** |

The 8 circuits every model covers, identical hours — scaled MAE:

| Horizon | B1 | B2 | B3 | GBM | Linear | **Forest** |
|---|---|---|---|---|---|---|
| +1h | 1.266 | 1.166 | **0.930** | 1.032 | 2.080 | 1.023 |
| +6h | 1.266 | 1.166 | 1.884 | 1.174 | 1.275 | **1.144** |
| day-ahead | 1.266 | 1.166 | 1.161 | 1.172 | 1.259 | **1.141** |

Same circuits — WAPE (total error ÷ total energy):

| Horizon | B1 | B2 | B3 | GBM | Linear | **Forest** |
|---|---|---|---|---|---|---|
| +1h | 37.5 % | 30.2 % | **20.4 %** | 22.6 % | 24.6 % | 21.3 % |
| +6h | 37.5 % | 30.2 % | 49.2 % | 30.8 % | 28.1 % | **28.0 %** |
| day-ahead | 37.5 % | 30.2 % | 34.1 % | 30.1 % | 28.1 % | **27.7 %** |

**B1** = same hour last week · **B2** = weekday × hour median · **B3** = last observed hour.
Both metrics agree on every ranking in this document.

## 6. Findings

**Persistence still wins at +1h, and that is about the building, not the model.** On the test
week the last observed hour beats every learned model (0.930 against the forest's 1.023 and the
GBM's 1.032). Alex found the same independently for gradient boosting. Two different
algorithms, one conclusion: one hour ahead, this building is close to a random walk.

**The further ahead the forecast, the simpler the model must be.** At +1h the best forest has
depth 12 and sees every feature per split. At day-ahead it has depth 4 and at least 250 samples
per leaf — roughly 16 leaves over 5,665 training rows. The saved files show it: 1,222 KB at
+1h, 364 KB at day-ahead. With seed noise at 0.1–0.2 %, and the result holding on the official
week and all three folds, this is a measurement of how little learnable structure exists at
that horizon with 35 days of history.

**Difficulty follows circuits, not zones.** In the test week the untrained SE/SW circuits
scored 0.31–0.36 while the trained NE/NW circuits scored 1.02–1.14 — the reverse of validation.
The cause is the NE|HVAC run on 3 Oct and the implausible NW|Emerg. Lighting hours on 5–6 Oct,
both in trained circuits, which account for 69–77 % of the Task 8 test error. The same
conclusion appears in the data: `SE|HVAC` has 0.0 % readings inconsistent with its own power
channel, while `NE|HVAC`, a circuit we kept, has 4.6 %.

**The eligibility rule measures sampling rate, not data integrity.** SE and SW sample more
slowly than NE and NW, and the gap widens during working hours (50 readings/hour in NE/NW all
day; SE drops to 30 at midday, SW to 25). But their gaps stay short — median longest gap
12–13 min, against 90 min for the rare NE/NW failures, which are real outages. Since `Er` is
cumulative, short gaps should not lose energy. A rule on longest gap rather than reading count
moves SE from 76.3 % to 90.1 % valid hours and SW from 74.7 % to 89.0 %.

## 7. Limits

- **Half the floor is predicted but not learned from.** SE/SW forecasts rest on NE/NW patterns
  plus each circuit's own history. They hold up in the test week — that is one week.
- **35 days of training.** Everything at +6h and day-ahead is bounded by this. The 2020–2023
  regime (~25,000 hours per circuit) is the obvious next step, and `energy_Wh` is already
  correctly derived there.
- **The selection metric is distorted.** `NW|Hand Dryer` at 0.9 Wh/h drives 41–44 % of
  `mean_scaled_MAE`. WAPE is reported alongside everywhere and agrees here, but Task 3 should
  still settle one definition.
- **No weather or calendar inputs.** Both sit unused in the repository; the backlog feedback
  called weather a Must, not a Should.
- **Not re-tunable.** The test week is spent.
- **Prediction intervals not implemented.** A forest gives them almost free — the spread across
  its 300 trees — which makes it the natural model for Sprint 3 Task 4.

## 8. Recommendations for Sprint 4

1. Add the 2020–2023 regime as a separate model. Largest single gain available.
2. Replace the reading-count validity rule with a gap-based rule; apply any circuit-level
   exclusion uniformly across all 16, not by zone.
3. Ask the data owner why SE/SW sampling drops during working hours, and about
   `SE|Plugs & Sockets` (13.6 % of readings inconsistent with its own power channel).
4. Add temperature. It is in the repository, covers the modelling window, and is unused.
5. Use this forest for prediction intervals (Task 4) — percentiles across the 300 trees.

## 9. Reproducing

```bash
pip install -r requirements.txt
python task1_random_forest_all16.py   # step 1: all 16 circuits, design A vs B
python step3_tuning.py --stage 1      # grid search
python step3_tuning.py --stage 2      # seed repetition
python step3_rolling.py               # rolling-origin folds
python step3_final.py                 # refit and freeze
python export_model.py                # save the fitted models
# python step4_test.py                # ALREADY RUN — guarded, do not re-run
```

Needs the Task 7&8 package (`task8_model.py`, `task7_baselines.py`, `config.py`) and
`derived/Storey1_hourly_v1.1.parquet` in the same folder.

Using a saved model without refitting:

```python
import joblib
bundle = joblib.load("models/task1_rf_p1h.joblib")
y = bundle["model"].predict(features_frame)   # Wh, already rescaled per circuit
```

## 10. Files

| File | What |
|---|---|
| `PARAMETERS.md` | Every parameter by type, with status and search space. Also the team template |
| `RESULTS.md` | Every result table in readable form, generated from the CSV files |
| `models/task1_rf_p1h.joblib`, `_p6h`, `_day-ahead` | The fitted models, with scaling factors and feature list |
| `models/task1_rf_final_config.json` | Frozen settings, dataset checksum, library versions |
| `models/task1_rf_model_manifest.json` | Checksums and sizes of the saved models |
| `task1_random_forest.py` | Forecaster class |
| `task1_random_forest_all16.py` | Step 1 — all 16 circuits, design A vs B |
| `step3_tuning.py` | Grid search and seed repetition |
| `step3_rolling.py` | Rolling-origin folds |
| `step3_final.py` | Refit and freeze |
| `step4_test.py` | The single test run, guarded |
| `export_model.py` | Saves the fitted models |
| `results/step3_*.csv` | Every configuration tried, at every stage |
| `results/task1_rf_final_*` | Validation results, per circuit and summary |
| `results/task1_rf_test_*` | Test results, per circuit, summary, and the cross-model comparison |
| `results/task1_rf_TEST_ALREADY_RUN.txt` | Guard against a second test run |
