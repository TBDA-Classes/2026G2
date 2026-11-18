# Cleaning checks — do the cleaning's quality flags and energy provenance affect our results?

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Émile (main author) · Claude (co-author)
**Script:** `Final_Evidence/scripts/cleaning_checks.py` · **Outputs:** `Final_Evidence/analysis/cleaning_flags_impact_test.csv`, `cleaning_flags_impact_selection.csv`, `cleaning_energy_source_vs_error.csv`

## Why these checks

The cleaning notebook (`Sensor_data_cleaning_Storey1_v4.ipynb`) writes a quality verdict per sensor (`sensor_quality_<ZONE>.csv` in `CLEAN DATA all zones.zip`) and a provenance label per row (`energy_source`). Nothing downstream read the verdicts: all 16 circuits were trained, selected and scored the same way. These checks measure whether that matters.

Flagged circuits (2025):

| Circuit | Verdict | Reason |
|---|---|---|
| SW Lighting | `counter_biased` | counter runs at 0.707 of the power reading |
| NE HVAC, NW Hand Dryer, SE Emerg. Lighting, SW Hand Dryer | `below_resolution` | median power 1.2–2.8 W, close to the 1 Wh counter step |

## A1 — Test week: conclusions with and without the flagged circuits

Same script (`Task6_rev0_03-11/task6_compare.py`), same hours, same bootstrap. The "all 16" rows reproduce the official `task6_test_16circuits` results exactly.

| Circuits | Horizon | Circuit-hours | Blend MAE (Wh) | Blend scaled MAE | Best model (MAE) | Blend vs B2 | Blend vs B3 |
|---|---|---|---|---|---|---|---|
| all 16 | +1 h | 1,911 | 22.2 | 0.41 | Chronos (tie with Blend) | better, significant | tie |
| | +6 h | 1,911 | 34.7 | 0.52 | ChronosGBM (tie) | better, significant | better, significant |
| | day-ahead | 1,911 | 34.2 | 0.50 | Blend (tie with GBM) | better, significant | tie (CI −16.8 to 0.1) |
| without 5 flagged | +1 h | 1,356 | 29.9 | 0.13 | Chronos (tie) | better, significant | tie |
| | +6 h | 1,356 | 47.3 | 0.21 | ChronosGBM (tie) | better, significant | better, significant |
| | day-ahead | 1,356 | 46.7 | 0.21 | Blend (tie) | better, significant | tie (CI −23.6 to 0.2) |

**Reading.**
1. **The conclusions do not change.** The same model is best at every horizon, and the significance against both baselines is the same (MAE in Wh).
2. **Only one detail moves:** without SW Lighting alone, Blend vs B2 at +6 h is still significant in Wh but no longer in *scaled* MAE (CI upper bound +0.0001). Borderline; worth stating.
3. **The scaled MAE headline is driven by the small circuits.** Without the 5 flagged circuits, Blend scaled MAE drops from 0.41–0.52 to 0.13–0.21. NE HVAC alone (scale 2.6 Wh, scaled MAE 3.7 at +1 h) contributes more than half of the 16-circuit mean at +1 h. MAE in Wh rises instead, because the removed circuits are the smallest ones.

## A2 — Model selection (rule D10) with and without the flagged circuits

D10 recomputed on the v1.3 validation forecasts (mean scaled MAE over the training circuits, tie margin 0.005, then lowest scaled RMSE). Our recomputation matches `model_choice_v1.3.csv` to the 4th decimal at +1 h and +6 h and within 0.0006 at day-ahead.

| Horizon | Official (15 training circuits) | Without the 5 flagged (10 circuits) |
|---|---|---|
| +1 h | Blend | Blend |
| +6 h | Blend | Blend |
| day-ahead | Blend (tied with Chronos, lower RMSE) | **Chronos** (Blend 0.249 vs Chronos 0.241: gap 0.008 > 0.005) |

**Reading.** At day-ahead, the choice of Blend over Chronos depends on including the below-resolution circuits. On the test week the Blend is still better than Chronos at day-ahead in both cases (34.2 vs 36.2 Wh with all 16; 46.7 vs 49.6 Wh without the flagged), so the final choice is not wrong — but the validation margin that selected it is partly made of circuits we had flagged.

Limit: GBM v1.3 is left out of A2 because its validation file did not reproduce the official score; officially it was never tied with the leader.

## B — Does less direct counter data mean worse forecasts?

For each circuit, the share of `energy_Wh` taken straight from one counter difference (`counter`), shared across a gap in proportion to power (`spread`), or estimated as power × time (`power`), on the test week, against the Blend error and the number of valid test hours (`cleaning_energy_source_vs_error.csv`).

| Group | Direct counter share, test week | Valid test hours (of 168) |
|---|---|---|
| NE/NW circuits (except NW Emerg. Lighting, NW Hand Dryer) | 53–100 % | 167 |
| NW Emerg. Lighting, NW Hand Dryer | 0–16 % | 149–167 |
| SE/SW circuits | under 30 % | 56–101 |

| Correlation (Spearman, test week) | 16 circuits | 11 unflagged circuits |
|---|---|---|
| Direct share vs day-ahead scaled MAE | ρ = 0.03 (p = 0.92) | ρ = −0.09 (p = 0.79) |
| Direct share vs valid test hours | ρ = 0.51 (p = 0.04) | ρ = 0.81 (p = 0.002) |

**Reading.** Less direct counter data does **not** make the hours we score less accurate: once energy is shared across a gap, the hourly total is still the counter's own total. The cost shows up as **coverage**: circuits with more gaps lose more hours to the hourly validity rules, so they have fewer usable hours (SE/SW: 56–101 of 168 test hours). This is the mechanism behind the 8-vs-16 circuits issue.

Limit: only valid hours are scored, so circuits with many gaps are scored on their better hours. The test says the scored hours are not worse; it does not say the missing hours would have been forecast as well.

## What to say in the presentation

- The cleaning flagged 5 circuits; we checked that removing them changes **none** of the conclusions.
- We are open about one sensitivity: the day-ahead selection margin of the Blend over Chronos relies on those circuits.
- The scaled-MAE headline is dominated by the smallest circuits; MAE in Wh is the safer headline metric.
- Poor SE/SW data cost **coverage**, not accuracy on the hours we kept.
