# Linear regression (Model 1) — how it was built, and why it is not the final model

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 23 Nov 2026
**Authors:** Mert (model owner, main author) · Claude (co-author)
**Model package:** `model1_LinearRegression_all16/` (rework 2 Nov 2026): `README_Task1_linear_all16.md`, `task1_linear_all16.py`, `task1_linear_all16_config.json`, `task1_linear_all16_tuning_log.csv`, `task1_linear_all16_test_per_circuit.csv`, `PARAMETERS.md`
**Comparison:** `Task6_rev0_03-11/RESULTS.md`, `results/task6_test_16circuits/pairwise_differences.csv`
**Related:** `15_Random_Forest_Justification.md` (same design), `12a_Cleaning_Checks.md`, `14_Evaluation_Protocol_Justification.md`, `09c_ASHRAE14_All_Models.md`, `analysis/rf_d10_style_check.csv`

> **Reading note.** The linear model was frozen on dataset **v1.1** and run on the test week on 2 Nov, after the final choice (D10, 29 Oct). It is not part of the final model. Its role is the simple, transparent reference among the ML models. Test numbers in Wh are the official Task 6 numbers (same 1,911 circuit-hours for every model).

## 1. Summary

- One **pooled median (LAD) regression** per horizon (+1 h, +6 h, day-ahead), trained on the 8 NE/NW circuits, forecasting all 16. Same inputs as the GBM and Random Forest.
- Settings chosen on validation: 2 designs × 9 settings × 3 horizons = 54 runs. Test week run once.
- Test MAE (16 circuits): **25.1 / 39.4 / 39.7 Wh** against **22.2 / 34.7 / 34.2 Wh** for Blend v1.3. **Tied with the Blend in Wh at every horizon**, but significantly worse in scaled MAE at +6 h and day-ahead. Lowest day-ahead RMSE of all models (138.0 Wh).
- It was not a D10 candidate. Had it been, it would not have been chosen: on validation it is 0.07–0.09 above the best model in scaled MAE (§4).

## 2. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### L1 — Train on the 8 NE/NW circuits, forecast all 16

- **Decision.** Fit on NE and NW only. SE and SW are forecast from their own recent values.
- **Why.** Same reason as the RF (R1): in v1.1, NE/NW had 99.4–100 % valid hours, SE/SW 34–89 %. The data owner required all 16 circuits.
- **Evidence.** `task1_linear_all16_config.json` (`training_circuits`, `predicted_circuits`).
- **Alternative rejected.** Training on all 16 with the v1.1 rules.
- **Weakness.** This is where the model loses: on SE/SW it is significantly worse than the Blend (+5.1 / +16.1 / +14.0 Wh) and than persistence (+4.1 / +16.6 / +14.6 Wh) at every horizon.

### L2 — One pooled model without circuit identity (design B), each circuit scaled by its training mean

- **Decision.** No circuit dummies. Target and value inputs are divided by the circuit's own training mean.
- **Why.** A per-circuit model cannot forecast a circuit it never saw. Scaling makes a hand dryer and a plug circuit comparable. Same design as Model 3.
- **Evidence.** Best validation score per design, 16 circuits (`task1_linear_all16_tuning_log.csv`): A 0.341 vs B 0.340 (+1 h), 0.409 vs 0.392 (+6 h), 0.413 vs 0.395 (day-ahead). On the 8 unseen circuits the gap is larger (0.459 vs 0.416 at +6 h).
- **Alternative rejected.** Design A (with dummies); per-circuit models (used in the 21 Oct version, see L8).
- **Weakness.** At +1 h, A and B are tied (0.0009 apart, below the 0.005 tie margin).

### L3 — Same inputs as the GBM and Random Forest

- **Decision.** The 12 numeric inputs of `task8_model.FEATURES` (standardised), plus hour and weekday one-hot. `is_weekend` is dropped because weekday already implies it.
- **Why.** So that differences between models come from the algorithm, not from the inputs.
- **Alternative rejected.** Weather or the UPM calendar. Adding them to one model only would break the like-for-like comparison.
- **Weakness.** A linear model cannot learn interactions (for example hour × weekday) unless they are built by hand.

### L4 — LAD (median regression) instead of least squares

- **Decision.** `QuantileRegressor(quantile=0.5, solver="highs")`.
- **Why.** MAE is the primary metric, and LAD optimises absolute error. Least squares is pulled by a few huge hours (for example the 3 Oct NE|HVAC run).
- **Evidence.** Best validation score per loss: LAD 0.340 / 0.392 / 0.395 vs ridge 0.402 / 0.497 / 0.501. Ridge is 18–27 % worse.
- **Alternative rejected.** Ridge, alpha 0.01–100.
- **Weakness.** None for the metric; the solver is deterministic, so no seed is needed.

### L5 — Regularisation alpha = 0.001

- **Decision.** Alpha 0.001 at every horizon, from 0 / 0.0001 / 0.001 / 0.01 / 0.1.
- **Evidence.** Day-ahead: 0.3954 (0) · 0.3954 (0.0001) · **0.3949 (0.001)** · 0.4070 (0.01) · 0.5247 (0.1). The grid was extended after 0.001 was at the edge.
- **Weakness.** "Interior optimum" (`PARAMETERS.md` §3) is true, but 0, 0.0001 and 0.001 are within 0.0005 of each other, ten times below the tie margin. The fair statement is: any alpha ≤ 0.001 gives the same model, and 0.01 or more is clearly worse.

### L6 — Missing inputs, clipping

- **Decision.** Missing numeric inputs get the training median plus a 0/1 "was missing" column. Forecasts are clipped at 0 Wh.
- **Why.** A linear model needs complete inputs, and energy cannot be negative.
- **Weakness.** The median fill is a simple choice; it was not compared with alternatives.

### L7 — Selection metric: mean scaled MAE over all 16 circuits

- **Decision.** Settings chosen on the validation week by mean scaled MAE over **all 16** circuits, same definition as Model 3.
- **Weakness.** This is not D10's definition (training circuits only). Scaled MAE is dominated by the tiniest circuits (see L9).

### L8 — History: from 8 circuits (21 Oct) to 16 circuits (2 Nov)

- **Decision.** The Sprint 3 version (21 Oct) used per-circuit +1 h models with dummies on 8 circuits. The 2 Nov rework switched to Model 3's design B and all 16 circuits.
- **Why.** The data owner asked for all 16 circuits, and design B scored best on validation (L2).
- **Weakness, stated openly.** The 21 Oct version had already been scored on the test week (+1 h MAE 32.4 Wh, mainly the NE|HVAC spike of 3 Oct). The rework was chosen on validation, but its authors knew that test result. The rework was then run on the test week again on 2 Nov, on all 16 circuits. The rework was needed because the 21 Oct version only forecast the 8 NE/NW circuits, while the Task 6 comparison scores every model on the same 16 circuits; without it, Model 1 could not be compared like-for-like with the other models.

### L9 — Robustness: the 5 circuits flagged by the cleaning

Same check as `12a_Cleaning_Checks.md` (SW Lighting + NE HVAC, NW Hand Dryer, SE Emerg. Lighting, SW Hand Dryer). The frozen model was refitted from `task1_linear_all16.py` on v1.1 and reproduced the official per-circuit test MAE exactly. Comparison on the model package's own hours and baselines:

- **Selection.** Choosing on the 11 unflagged circuits gives the same design, loss and alpha at +1 h and day-ahead. At +6 h alpha becomes 0, with a gap of 0.00005.
- **Test, in Wh.** The verdicts against B2 and B3 are the same with and without the flagged circuits.
- **Test, in scaled MAE, one result flips.** With 16 circuits, B2 is lower than linear at +6 h and day-ahead (0.77 vs 0.81–0.82). Without the 5 flagged, linear is lower (0.49 vs 0.54). NE HVAC alone has a scaled MAE of 3.3 at +1 h.
- **Retrained without NE HVAC and NW Hand Dryer** (6 training circuits): +6 h and day-ahead get worse by 6–7 Wh, mostly on SE Lighting, SE Plugs and NW Plugs. Keeping them in training is justified.
- **Er/Ea.** The model only uses `energy_Wh`, which the cleaning notebook builds from Er (active energy) with W. The data-dictionary swap had no effect.

## 3. Result

Test week, 16 circuits, same 1,911 hours per horizon (`pairwise_differences.csv`):

| MAE (Wh) | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| **Blend v1.3 (final model)** | **22.2** | **34.7** | **34.2** |
| GBM v1.3 | 26.3 | 37.1 | 35.7 |
| Random Forest | 27.7 | 37.4 | 37.4 |
| Linear regression | 25.1 | 39.4 | 39.7 |
| B3 persistence | 24.0 | 57.8 | 41.5 |
| B2 weekday × hour median | 43.7 | 43.7 | 43.7 |
| Linear − Blend (95 % CI) | +3.0 (−1.1 to +5.6) tie | +4.6 (−0.4 to +9.1) tie* | +5.5 (−0.1 to +9.8) tie* |
| Linear − B2 | −18.6 (−27.2 to −11.5) **better** | −4.4 (−10.5 to +1.9) tie | −4.0 (−10.2 to +2.4) tie |
| Linear − B3 | +1.2 (−0.0 to +2.3) tie | −18.5 (−30.4 to −7.6) **better** | −1.8 (−12.8 to +7.0) tie |

\* Significantly worse in scaled MAE.

- **Strengths.** Tied with every ML model in Wh at every horizon, except Chronos at +1 h and ChronosGBM at +6 h. On the 8 NE/NW circuits it is tied with the Blend at every horizon. Lowest day-ahead RMSE (138.0). Simple, deterministic and fully explainable.
- **Where it loses.** SE/SW circuits (L1). At +6 h and day-ahead it does not beat B2 significantly. ASHRAE 14 (`09c`): passes at +1 h, but misses NMBE at +6 h and day-ahead (−11.7 %), so it under-forecasts the building total. It passes on validation.

## 4. Why it is not the final model

1. **It was not a candidate.** D8/D10 (28–29 Oct) chose only among Chronos, GBM, ChronosGBM and Blend. The all-16 linear model was frozen on 2 Nov, after that choice.
2. **Had it been a candidate, D10 would not have picked it.** Validation, scaled MAE, 15 training circuits, same hours (`analysis/rf_d10_style_check.csv`):

| Validation, scaled MAE | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| Best model | 0.209 (ChronosGBM) | 0.285 (ChronosGBM) | 0.282 (Chronos) |
| Blend v1.3 | 0.215 | 0.290 | 0.289 |
| Linear regression | 0.298 | 0.352 | 0.356 |
| Gap linear − best | 0.089 | 0.067 | 0.074 |

   The tie margin is 0.005, so the gap is 13–18 times larger.
3. **The test confirms it.** Never lower than the Blend, and significantly worse in scaled MAE at +6 h and day-ahead.

**Limit.** Same as the RF: v1.1 and 8 training circuits against v1.2 and 15 for the v1.3 models. The honest conclusion is "this linear model is not better than the final model", not "linear models are worse".

## 5. Corrections (numbers to retire)

| Where | Old statement | Correct |
|---|---|---|
| Model 1 README, test table | MAE 24.8 / 38.5 / 39.0 Wh | Model's own hours. For comparisons use Task 6: 25.1 / 39.4 / 39.7 Wh |
| Model 1 README | B2 best at +6 h and day-ahead (scaled MAE) | True with 16 circuits, but caused by the 5 flagged tiny circuits (L9). In Wh: tie with B2 |
| `PARAMETERS.md` §3 | alpha 0.001 "interior optimum" | Interior, but 0 to 0.001 are equivalent (L5) |
| `task6_linear_rebuild.py` header | "original task1_linear_all16.py was not in the repository" | It is now in `model1_LinearRegression_all16/` and reproduces the official test MAE exactly |
| `PROTOCOL_NOTE_v1.2.md` §1, doc 14 | Sprint 3 test-week users: linear on 8 NE/NW circuits | Linear also used the test week on 2 Nov on **all 16 circuits** |

## 6. What the model still gave the project

- **A transparent reference.** It shows how much of the gain comes from simple, explainable structure: it ties the Blend in Wh.
- **Absolute-error loss confirmed.** LAD beat least squares by 18–27 %. The RF found the same with its split criterion.
- **Persistence is hard to beat at +1 h**, confirmed for a third model family.

## 7. Likely questions

| Question | Short answer |
|---|---|
| Why a linear model? | The simplest ML reference: if complex models cannot beat it clearly, that is important to know. |
| Why median regression? | MAE is the metric; LAD was 18–27 % better than ridge on validation. |
| How can it forecast circuits it never saw? | No circuit identity, scaled inputs, so any circuit with history works. |
| It ties the Blend. Why not use it? | Tied in Wh, but worse in scaled MAE, on SE/SW and on validation, and it fails ASHRAE NMBE at +6 h and day-ahead. |
| Do the flagged sensors change anything? | Not in Wh. In scaled MAE they make B2 look better than it is (L9). |
| Is the comparison fair? | Same hours and metric, but not the same training data (v1.1, 8 circuits vs v1.2, 15). We say so. |
