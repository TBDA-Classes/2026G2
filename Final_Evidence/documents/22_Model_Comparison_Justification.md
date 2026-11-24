# Model comparison (Task 6) — how the 11 models were compared, checked and how robust the result is

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 24 Nov 2026
**Authors:** Edoardo (main author; built the Task 6 comparison) · Claude (co-author)
**Sources:** `Task6_rev0_03-11/` (`README.md`, `RESULTS.md`, `task6_compare.py`, `results/`), `TBDA_v1.3_ChronosGBM_29-10/models/blend_frozen_config_v1.3.json`, `model_choice_v1.3.json`, `PROTOCOL_NOTE_v1.2.md`, `DECISIONS_v1.2.md`
**New evidence:** `Final_Evidence/scripts/model_comparison_checks.py` → `Final_Evidence/analysis/model_comparison/`
**Related:** `14_Evaluation_Protocol_Justification.md` (split, horizons, metrics, baselines, rule D10), `17_Model_Justification_Blend_v1.3.pdf` (the final model), `12a_Cleaning_Checks.md`, `10_Evidence_Map.md`

> **Reading note.** Document 14 already justifies the evaluation protocol (E1–E9), and document 17 the choice of Blend v1.3. This document covers only what is specific to the **comparison itself**: how 11 models built on two dataset versions were made comparable, how every forecast was checked, and how robust the conclusions are. The robustness checks in §4 are new. They re-score stored forecasts only; nothing is refitted or re-chosen.

## 1. Summary

- **11 models compared on exactly the same hours.**
  - **Models:** B1, B2, B3, Linear Regression, Random Forest, GBM v1.0, GBM v1.3, Chronos-Bolt v1.1, Chronos-Bolt v1.3, ChronosGBM v1.3 and Blend v1.3.
  - **Hours scored:** 1,911 circuit-hours per horizon on 16 circuits (71% of 2,688), and 1,318 on the 8 NE/NW circuits.
- **Every forecast was regenerated from the frozen models** and matches its owner's numbers. The full Task 6 folder reruns identically.
- **Result.** Blend v1.3 has a test MAE of 22.2 / 34.7 / 34.2 Wh (+1 h / +6 h / day-ahead). It is the best model or tied with the best at every horizon. It beats Baseline B everywhere, and persistence only at +6 h.
- **Robustness (new).**
  - **These results hold for every bootstrap block length, every seed and a second test (Diebold–Mariano):** Blend vs Baseline B at every horizon, Blend vs persistence at +6 h, and Blend vs GBM, ChronosGBM and Random Forest at +1 h.
  - **Three results are borderline and must not be presented as wins:** Blend vs persistence day-ahead, Blend vs Chronos-Bolt day-ahead, and Blend vs GBM at +6 h.
- **Main weakness.** There is one test week. The day-ahead ranking of the ML models changes a lot between validation and test (rank correlation 0.14). The blend weights chosen on validation rank only 59th / 113th / 143rd of 231 possible weight sets on test.

## 2. Verification: is the comparison correct?

Re-checked on 17 and 24 Nov 2026 (`analysis/model_comparison/verification_checks.csv`).

| Check | Result |
|---|---|
| Full rerun of `run_task6_all.sh` from a clean copy | OK: all 60 result CSVs identical |
| 22 prediction files: 16 (or 8) circuits × 168 h × 3 horizons, no duplicates | OK |
| Target hours inside the right split (test 29 Sep – 5 Oct, validation 22 – 28 Sep, UTC) | OK |
| No information from the future: issue time before target hour, lead consistent, day-ahead issued 00:00 Madrid | OK |
| Same actual values in every file where both are valid | OK |
| No negative forecasts | OK |
| Blend = frozen weighted average of its three parts | OK: max. difference 2.3 × 10⁻¹³ Wh |
| Numbers in `RESULTS.md` = result CSVs (9 models × 3 horizons) | OK |
| Each owner's numbers reproduced (`Task6_rev0_03-11/README.md`, *Checks*) | OK: B1–B3 and GBM v1.0 validation 66.7 / 54.2 / 31.3 / 33.3 Wh; Linear 0.340 / 0.392 / 0.395; Chronos v1.1 and v1.3 identical; GBM, ChronosGBM, Blend v1.3 equal to the 3rd–4th decimal; Chronos v1.3 test vs Emily's file < 10⁻¹² Wh |

## 3. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### C1 — One set of hours for models built on two dataset versions

- **Decision.** Score only hours that are valid in dataset v1.1 **and** v1.2 and forecast by every model.
- **Why.** Linear Regression, Random Forest, GBM v1.0 and Chronos v1.1 were built on v1.1 (THRESHOLD = 30). The v1.3 models and the baselines were built on v1.2 (gap rule and energy/power check, D1–D2). The two versions mark different hours as invalid. Scoring each model on its own hours would let a model look better just by skipping the hard hours.
- **Evidence.** Where both versions are valid, the actual values are 100% identical (`alignment_checks.csv` in every results folder).
- **Alternative rejected.** Each model on its own valid hours: not comparable. Rebuilding every model on v1.2: correct, but the team voted not to rebuild.
- **Weakness.** 29% of the hours are lost, mostly SE/SW. For example, SE|Plugs & Sockets keeps 63 of 168 hours. Numbers differ slightly from the owners' own reports (Chronos v1.1 +1 h: 29.0 Wh here, 30.9 Wh on 1,336 hours in Sprint 3).

### C2 — Regenerate every forecast from the frozen models and check it

- **Decision.** No forecast was taken on trust. Every one was rebuilt from the saved `.joblib` models and frozen configs, then compared with its owner's numbers.
- **Why.** The comparison must evaluate each model exactly as it was chosen, and files passed between people can be wrong (the Linear CSV had `zone` and `circuit_zone` swapped).
- **Evidence.** Section 2. The GBM v1.0 and B1–B3 test MAE per circuit match `task1_rf_test_comparison.csv` on 96 of 96 values.
- **Alternative rejected.** Collect each owner's CSV as delivered: faster, but unchecked.
- **Weakness.** Without pyarrow in our environment, Parquet files were read with a small reader we wrote ourselves (`minipq.py`). It was checked indirectly: every value it read reproduces the owners' numbers.

### C3 — v1.3 test run once, after the final choice

- **Decision.**
  - GBM v1.3, ChronosGBM v1.3 and Blend v1.3 were run on the test week once, on 3 Nov, from the frozen models and weights.
  - The Chronos-Bolt v1.3 test forecasts were produced by Emily, who had the model weights.
- **Why.** Rule D10 fixed the final model on 29 Oct (`model_choice_v1.3.json`). Running the test before that date would have broken document 14 (E3).
- **Evidence.** Blend recomputed from its three parts with the frozen weights: max. difference 2.3 × 10⁻¹³ Wh.
- **Alternative rejected.** Test only the final model (Emily's first understanding). That was not possible: the Blend is 50–75% Chronos-Bolt, so its test needs the Chronos test forecasts anyway, and showing the parts costs nothing.
- **Weakness.** The same test week had been used in Sprint 3 for the v1.1 models (`PROTOCOL_NOTE_v1.2.md` §1; document 14 E3).

### C4 — Rebuild the Linear Regression from its parameter table

- **Decision.** The final linear script (`task1_linear_all16.py`) was not in the repository. Model 1 was rebuilt from its `PARAMETERS.md`: pooled LAD, alpha 0.001, no circuit identity, trained on 8 NE/NW circuits.
- **Why.** The comparison also reports validation results, and only the test CSV of the linear model had been delivered.
- **Evidence.** The rebuilt test forecasts match the official file within 0.0005 Wh, with the same training rows (5,681 / 5,641 / 5,665). Validation scaled MAE matches 0.340 / 0.392 / 0.395.
- **Weakness.** It is a rebuild, not the owner's code. If the original script appears, it should replace it.

### C5 — One fixed scale for the scaled MAE

- **Decision.** Every model is scaled by the same per-circuit training mean (19 Aug – 21 Sep, dataset v1.2; `Task6_rev0_03-11/data/task6_circuit_scale_train_mean_v1.2.csv`).
- **Why.** Each owner used a slightly different scale (cut-off, dataset version). One common scale keeps the comparison fair.
- **Weakness.** Scaled numbers differ slightly from the owners' own. The weight of tiny circuits remains (document 14 E5, `12a_Cleaning_Checks.md`).

### C6 — Confidence intervals: 24-hour block bootstrap, checked two other ways

- **Decision.** Circular moving-block bootstrap: 2,000 resamples of 24-hour blocks, all circuits of an hour kept together, the same resamples for every model (paired).
- **Why.** Errors of consecutive hours are correlated (document 14 E8). Resampling single hours would give intervals that are too narrow.
- **Evidence (new).**
  - We repeated every comparison of the Blend with blocks of 1, 6, 12, 24, 48 and 72 h, with 5 seeds, and with a Diebold–Mariano test (Newey–West variance, lag 24 h) (`robust_block_seed.csv`, `robust_diebold_mariano.csv`).
  - The clear results do not change (§4).
  - With 1-hour blocks, extra "wins" appear, for example Blend vs Linear at +6 h. That is the over-confidence the 24-hour blocks prevent.
- **Alternative rejected.** An i.i.d. bootstrap or a plain t-test on hours: both ignore the correlation.
- **Weakness.** One week is only 7 independent day-blocks, so the intervals are wide and borderline results flip with the seed or block length.

### C7 — "Better" only when the difference is significant

- **Decision.** A model is better only if the 95% CI of its MAE difference excludes 0. Otherwise the two are tied.
- **Why.** With one week, differences of 1–3 Wh are within noise. Ranking by point value alone would over-claim.
- **Weakness.** Many pairs are tested, and no correction for multiple comparisons was made. That is one more reason to present the three borderline cases of §4 as ties.

### C8 — Results with and without the NE|HVAC event

- **Decision.** The official results keep every valid hour. A second run removes the NE|HVAC day of 3 Oct (23 hours per horizon).
- **Why.** On 3 Oct NE|HVAC used 690 / 686 / 266 Wh against about 3 Wh normally. No model can forecast it, and it weighs heavily in scaled MAE. The Sprint 3 report template asks for both views.
- **Evidence.** Without the event, MAE in Wh changes by less than 1 Wh. Scaled MAE roughly halves (Blend day-ahead 0.498 → 0.264). The ranking and every conclusion about the baselines stay the same. The 18 impossible NW|Emerg. Lighting hours are already invalid in v1.2, so they are not scored in either view.
- **Weakness.** Which hours count as an "event" is a judgement. The rule was not written down numerically before the test.

### C9 — Two scopes: 16 circuits (main) and 8 NE/NW circuits

- **Decision.** The 16-circuit comparison is the main one. The 8-circuit comparison is kept for continuity.
- **Why.** The teacher asked for all circuits. Only on the 8 circuits can GBM v1.0 and Chronos v1.1 (built for them only) be compared with the Sprint 2–3 numbers.
- **Weakness.** On the 8 circuits every top model is tied, so that table cannot rank them.

### C10 — Error analysis by hour, day type, date, circuit and hours ahead

- **Decision.** For every model, the errors are broken down along five axes (`error_by_*.csv`, `metrics_per_circuit.csv`).
- **Why.** The report and the dashboard need to say *where* the model fails, not only how much.
- **Evidence.**
  - Day-ahead, the Blend's error is 49.4 Wh at 00–05 h and 21.5 Wh at 19–23 h.
  - Between 00:00 and 09:00, 79% of the error comes from NW|Plugs & Sockets, whose night use rose from 514 Wh/h (training) to 980 (validation) and 1,043 (test).
  - The error is 41.3 Wh on weekdays and 19.1 Wh at weekends.
  - Day-ahead error does not grow with hours ahead, because issue time is 00:00, so hours ahead equal clock hours.
- **Weakness.** These are descriptions on one week, not tested causes. The NW|Plugs change must be confirmed with the data owner.

## 4. How robust is the result for the final model?

Blend v1.3 against every other model on the test week, 16 circuits. Columns 3–5 give the verdict of each check.

| Comparison | Δ MAE (Wh) | Official (24 h blocks) | Block lengths 1–72 h | Diebold–Mariano | Verdict |
|---|---|---|---|---|---|
| vs Baseline B, all horizons | −21.6 / −9.0 / −9.6 | better | better in 18/18 | p < 0.001 | **robust** |
| vs persistence +6 h | −23.1 | better | better 6/6 | p < 0.001 | **robust** |
| vs GBM v1.3 +1 h | −4.2 | better | better 6/6 | p < 0.001 | **robust** |
| vs Random Forest +1 h | −5.6 | better | better 6/6 | p < 0.001 | **robust** |
| vs ChronosGBM +1 h | −2.6 | better | better 6/6 | p < 0.001 | **robust** |
| vs Chronos-Bolt +6 h | −2.2 | better | better 6/6 | p = 0.010 | **robust** |
| vs persistence +1 h | −1.8 | tie | tie 6/6 | p = 0.13 | **tie** |
| vs persistence day-ahead | −7.3 | tie (CI −16.8 to +0.1) | better 5/6 | p = 0.10 | **borderline** |
| vs Chronos-Bolt day-ahead | −2.1 | better (CI edge at 0.0) | better 5/6; ties with 5 seeds | p = 0.07 | **borderline** |
| vs GBM v1.3 +6 h | −2.4 | better (CI edge at 0.0) | tie 5/6 | p = 0.22 | **borderline** |
| vs Linear Regression +1 h / +6 h / day-ahead | −3.0 / −4.7 / −5.5 | tie | mostly better only with short blocks (1–12 h) | p = 0.02 / 0.15 / 0.07 | **tie / borderline** |
| vs Chronos-Bolt +1 h, ChronosGBM +6 h; ChronosGBM, GBM and Random Forest day-ahead | −3.2 to +0.6 | tie | tie | tie | **tie** |

**Days won (Madrid days of the test week).** The Blend has the lower MAE:
- vs Baseline B: 7 / 6 / 6 of 7 days (+1 h / +6 h / day-ahead);
- vs persistence: 6 / 7 / 6 of 7 days;
- vs GBM v1.3 day-ahead: only 4 of 7 days (`robust_days.csv`).

**Blend weights (diagnostic only, nothing re-chosen).** We scored all 231 weight sets on a 0.05 grid (`robust_blend_weights.csv`):

| Horizon | Chosen weights (GBM / ChronosGBM / Chronos) | Rank on validation | Rank on test | Test MAE chosen | Best possible | Equal thirds |
|---|---|---|---|---|---|---|
| +1 h | 0.30 / 0.20 / 0.50 | 65 | 59 | 22.2 | 21.5 | 22.8 |
| +6 h | 0.10 / 0.35 / 0.55 | 44 | 113 | 34.7 | 33.8 | 34.5 |
| day-ahead | 0.15 / 0.10 / 0.75 | 18 | 143 | 34.2 | 33.0 | 33.2 |

**What this table shows.**
- The chosen weights are not the best on validation either. D10 picks by scaled MAE and RMSE, not by MAE in Wh.
- The validation week does not pin the weights down. Simple equal weights would have been about 1 Wh better on test at +6 h and day-ahead.
- Switching now would be choosing on the test week, so it is a lesson, not a change.

**Rank stability (`robust_selection.csv`).**
- The Spearman correlation between validation MAE and test MAE of the 6 ML models is 1.00 at +1 h, 0.83 at +6 h and 0.14 at day-ahead.
- Choosing the lowest validation MAE in Wh per horizon would have given Chronos / ChronosGBM / Chronos, with test MAE 21.5 / 34.2 / 36.2 Wh. That is better than the Blend at +1 h and +6 h, and worse day-ahead.

## 5. If we did it again

1. **Fix one dataset version before any model is built.** This avoids the C1 intersection and keeps 100% of the valid hours.
2. **Keep a shared, checked hand-over format** for forecasts (column names, UTC, issue time, lead), plus a reader for Parquet in everyone's environment.
3. **Several test weeks (rolling origin).** One week cannot separate the top models day-ahead.
4. **Choose blend weights on several weeks, or shrink them toward equal weights.** Equal weights are a strong, simpler default.
5. **Write the event rule** (what counts as a non-forecastable event) **and the few comparisons that matter before the test**, and correct for multiple comparisons on those.

## 6. Likely questions

| Question | Short answer |
|---|---|
| Why not compare each model on its own hours? | Two dataset versions mark different hours invalid. Same hours = same question (C1). |
| How do you know the numbers are right? | Every forecast regenerated from the frozen model and matched to its owner; full rerun identical (§2). |
| Who ran the test week? | Once, on 3 Nov, after D10 (29 Oct): GBM, ChronosGBM and Blend by Edoardo, Chronos-Bolt by Emily (C3). |
| Why 24-hour blocks? | Errors of nearby hours are correlated. Other block lengths and a Diebold–Mariano test give the same clear results (C6, §4). |
| Is the Blend really better than persistence? | At +6 h clearly. At +1 h no. Day-ahead probably, but not proven (§4). |
| Why not take the best model per horizon? | D10 was fixed before the test. A posteriori it would win at +1 h and +6 h and lose day-ahead (§4). |
| Are the blend weights optimal? | No: chosen on one week. Equal weights would have done about as well (§4). |
| Why remove the NE HVAC event? | Only as a check: the official numbers keep it, and the ranking does not change (C8). |

## 7. Files

| File | Content |
|---|---|
| `Final_Evidence/scripts/model_comparison_checks.py` | Recomputes every file below from `Task6_rev0_03-11/` (run from the repository root; needs pandas, numpy, scipy) |
| `Final_Evidence/analysis/model_comparison/verification_checks.csv` | The checks of §2 |
| `.../robust_block_seed.csv` | Verdicts with blocks of 1–72 h and 5 seeds |
| `.../robust_diebold_mariano.csv` | Diebold–Mariano tests |
| `.../robust_blend_weights.csv` | All 231 blend weight sets on validation and test (diagnostic) |
| `.../robust_days.csv` | Test days won by the Blend |
| `.../robust_selection.csv` | Validation → test rank stability; best model per horizon |
| `Task6_rev0_03-11/RESULTS.md`, `results/` | The official comparison |
