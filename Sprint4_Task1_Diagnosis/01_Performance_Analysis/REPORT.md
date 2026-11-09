# Sprint 4 — Task 1 Part 1: Performance analysis of Blend v1.3

**Authors:** Maria Francesca Casillo and Yasmin Sarbout Atif  
**Status:** Recalculated validation analysis, prepared for team review on 6 November 2026. This revision replaces the unsupported performance tables in the supplied Part 1 draft; the original document is preserved separately.

## Purpose

Identify **where the selected model makes errors** using MAE, RMSE and valid observation counts by zone, circuit and forecasting horizon. The deliverables are complete metric tables and a shortlist of cases requiring further investigation. Temporal patterns belong to Part 2; data conditions and possible explanations belong to Part 3.

## Data and method

Source: `ML_Blend_v1.3_validation_predictions.csv`, the saved Task 6 predictions also used in Part 2. Validation targets run from 22 September 2025 00:00 UTC to 29 September 2025 00:00 UTC, end exclusive. No test data, training or tuning are used here.

The file contains 8,064 rows: 16 circuits × 168 hours × 3 horizons. There are 7,239 valid actual/prediction pairs, 2,413 per horizon; 825 rows are excluded because the actual value is missing. Missing actuals are never replaced by zero. The repeated horizons do not represent independent target hours.

`zone` is the circuit identifier; `circuit_zone` is NE/NW/SE/SW. The inventory contains 2 NE, 6 NW, 4 SE and 4 SW circuits. `horizon_h=24` labels day-ahead, not a fixed lead of 24 hours for every forecast.

- MAE = mean absolute difference between forecast and actual, in Wh.
- RMSE = square root of the mean squared difference, in Wh; large misses receive greater weight.
- Valid-pair percentage = valid actual/prediction pairs divided by the expected circuit-hour rows in this file.
- Absolute-error share = a scope's sum of absolute errors divided by the all-circuit sum at the same horizon. This is not percentage prediction error or the share of the unweighted sum of circuit MAEs.

Zone and overall metrics pool circuit-hour pairs: MAE is weighted by valid counts and RMSE is computed from pooled squared errors. RMSE values must not be averaged directly. These results use Blend's available validation pairs, not Task 6's common mask across competing models and dataset versions. Consequently they do not reproduce the official comparison scores and must not be substituted into that comparison.

## Overall and zone results

| horizon_h | n_expected | n_valid | n_excluded | MAE_Wh | RMSE_Wh |
| --- | --- | --- | --- | --- | --- |
| 1.00 | 2688.00 | 2413.00 | 275.00 | 23.11 | 107.58 |
| 6.00 | 2688.00 | 2413.00 | 275.00 | 35.35 | 144.36 |
| 24.00 | 2688.00 | 2413.00 | 275.00 | 33.77 | 140.95 |

| circuit_zone | horizon_h | n_expected | n_valid | valid_pair_pct | MAE_Wh | RMSE_Wh | absolute_error_share_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NE | 1 | 336 | 334 | 99.40 | 2.90 | 5.04 | 1.73 |
| NE | 6 | 336 | 334 | 99.40 | 2.31 | 4.41 | 0.91 |
| NE | 24 | 336 | 334 | 99.40 | 2.53 | 4.63 | 1.04 |
| NW | 1 | 1008 | 1002 | 99.40 | 37.00 | 143.96 | 66.49 |
| NW | 6 | 1008 | 1002 | 99.40 | 55.45 | 192.25 | 65.15 |
| NW | 24 | 1008 | 1002 | 99.40 | 49.66 | 186.98 | 61.06 |
| SE | 1 | 672 | 534 | 79.46 | 25.61 | 111.38 | 24.52 |
| SE | 6 | 672 | 534 | 79.46 | 43.18 | 152.94 | 27.03 |
| SE | 24 | 672 | 534 | 79.46 | 47.28 | 151.40 | 30.99 |
| SW | 1 | 672 | 543 | 80.80 | 7.44 | 31.17 | 7.25 |
| SW | 6 | 672 | 543 | 80.80 | 10.86 | 37.34 | 6.92 |
| SW | 24 | 672 | 543 | 80.80 | 10.38 | 34.87 | 6.91 |

NW Plugs & Sockets has the largest MAE and RMSE at every horizon, followed by SE Lighting. Their combined shares of pooled absolute error are 76.1% at +1 h, 78.0% at +6 h and 75.9% day-ahead. These are the strongest absolute-error priorities in this sample. SE Plugs & Sockets ranks third by MAE at each horizon, but has only 98 valid observations out of 168. SW Lighting enters the +1 h shortlist through RMSE rather than MAE, indicating that its largest misses deserve inspection. These rankings describe the available validation observations, not future performance.


## Complete circuit results

Circuit names below are rendered with `/` for readability; CSVs preserve the original identifiers containing `|`.

### +1 h

| zone | n_valid | n_excluded | valid_pair_pct | MAE_Wh | RMSE_Wh | absolute_error_share_pct | MAE_rank | RMSE_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NW / Plugs & Sockets | 167 | 1 | 99.40 | 195.59 | 350.53 | 58.59 | 1 | 1 |
| SE / Lighting | 142 | 26 | 84.52 | 68.60 | 211.22 | 17.47 | 2 | 2 |
| SE / Plugs & Sockets | 98 | 70 | 58.33 | 36.06 | 53.43 | 6.34 | 3 | 4 |
| NW / Lighting | 167 | 1 | 99.40 | 20.00 | 38.01 | 5.99 | 4 | 5 |
| SW / Lighting | 121 | 47 | 72.02 | 15.02 | 59.72 | 3.26 | 5 | 3 |
| SW / Plugs & Sockets | 142 | 26 | 84.52 | 14.35 | 25.94 | 3.65 | 6 | 6 |
| NE / Plugs & Sockets | 167 | 1 | 99.40 | 5.31 | 7.10 | 1.59 | 7 | 8 |
| NW / RACK | 167 | 1 | 99.40 | 2.63 | 3.30 | 0.79 | 8 | 10 |
| NW / HVAC | 167 | 1 | 99.40 | 2.41 | 3.66 | 0.72 | 9 | 9 |
| SE / HVAC | 147 | 21 | 87.50 | 2.21 | 8.42 | 0.58 | 10 | 7 |
| NW / Hand Dryer | 167 | 1 | 99.40 | 0.83 | 1.33 | 0.25 | 11 | 12 |
| SW / Hand Dryer | 133 | 35 | 79.17 | 0.71 | 1.93 | 0.17 | 12 | 11 |
| SW / Emerg. Lighting | 147 | 21 | 87.50 | 0.62 | 0.74 | 0.16 | 13 | 13 |
| NW / Emerg. Lighting | 167 | 1 | 99.40 | 0.53 | 0.63 | 0.16 | 14 | 14 |
| SE / Emerg. Lighting | 147 | 21 | 87.50 | 0.49 | 0.63 | 0.13 | 15 | 15 |
| NE / HVAC | 167 | 1 | 99.40 | 0.49 | 0.59 | 0.15 | 16 | 16 |

### +6 h

| zone | n_valid | n_excluded | valid_pair_pct | MAE_Wh | RMSE_Wh | absolute_error_share_pct | MAE_rank | RMSE_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NW / Plugs & Sockets | 167 | 1 | 99.40 | 290.21 | 467.94 | 56.82 | 1 | 1 |
| SE / Lighting | 142 | 26 | 84.52 | 127.41 | 291.22 | 21.21 | 2 | 2 |
| SE / Plugs & Sockets | 98 | 70 | 58.33 | 47.28 | 66.92 | 5.43 | 3 | 3 |
| NW / Lighting | 167 | 1 | 99.40 | 33.15 | 50.85 | 6.49 | 4 | 5 |
| SW / Plugs & Sockets | 142 | 26 | 84.52 | 26.20 | 41.09 | 4.36 | 5 | 6 |
| SW / Lighting | 121 | 47 | 72.02 | 16.32 | 65.35 | 2.32 | 6 | 4 |
| NW / HVAC | 167 | 1 | 99.40 | 4.86 | 14.05 | 0.95 | 7 | 7 |
| NE / Plugs & Sockets | 167 | 1 | 99.40 | 4.14 | 6.21 | 0.81 | 8 | 9 |
| NW / RACK | 167 | 1 | 99.40 | 2.98 | 4.00 | 0.58 | 9 | 10 |
| SE / HVAC | 147 | 21 | 87.50 | 1.78 | 7.62 | 0.31 | 10 | 8 |
| NW / Hand Dryer | 167 | 1 | 99.40 | 0.93 | 1.41 | 0.18 | 11 | 12 |
| SW / Hand Dryer | 133 | 35 | 79.17 | 0.78 | 1.96 | 0.12 | 12 | 11 |
| SW / Emerg. Lighting | 147 | 21 | 87.50 | 0.67 | 0.81 | 0.12 | 13 | 13 |
| NW / Emerg. Lighting | 167 | 1 | 99.40 | 0.59 | 0.73 | 0.12 | 14 | 14 |
| NE / HVAC | 167 | 1 | 99.40 | 0.49 | 0.59 | 0.10 | 15 | 16 |
| SE / Emerg. Lighting | 147 | 21 | 87.50 | 0.48 | 0.65 | 0.08 | 16 | 15 |

### Day-ahead

| zone | n_valid | n_excluded | valid_pair_pct | MAE_Wh | RMSE_Wh | absolute_error_share_pct | MAE_rank | RMSE_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NW / Plugs & Sockets | 167 | 1 | 99.40 | 255.74 | 454.91 | 52.41 | 1 | 1 |
| SE / Lighting | 142 | 26 | 84.52 | 134.82 | 286.37 | 23.49 | 2 | 2 |
| SE / Plugs & Sockets | 98 | 70 | 58.33 | 58.91 | 77.41 | 7.08 | 3 | 3 |
| NW / Lighting | 167 | 1 | 99.40 | 30.97 | 50.06 | 6.35 | 4 | 5 |
| SW / Plugs & Sockets | 142 | 26 | 84.52 | 24.86 | 40.10 | 4.33 | 5 | 6 |
| SW / Lighting | 121 | 47 | 72.02 | 15.72 | 59.70 | 2.33 | 6 | 4 |
| NW / HVAC | 167 | 1 | 99.40 | 6.75 | 17.70 | 1.38 | 7 | 7 |
| NE / Plugs & Sockets | 167 | 1 | 99.40 | 4.56 | 6.52 | 0.93 | 8 | 9 |
| NW / RACK | 167 | 1 | 99.40 | 2.97 | 4.04 | 0.61 | 9 | 10 |
| SE / HVAC | 147 | 21 | 87.50 | 1.74 | 7.76 | 0.31 | 10 | 8 |
| NW / Hand Dryer | 167 | 1 | 99.40 | 1.00 | 1.52 | 0.20 | 11 | 12 |
| SW / Hand Dryer | 133 | 35 | 79.17 | 0.77 | 1.94 | 0.13 | 12 | 11 |
| SW / Emerg. Lighting | 147 | 21 | 87.50 | 0.67 | 0.81 | 0.12 | 13 | 13 |
| SE / Emerg. Lighting | 147 | 21 | 87.50 | 0.53 | 0.67 | 0.09 | 14 | 14 |
| NE / HVAC | 167 | 1 | 99.40 | 0.50 | 0.62 | 0.10 | 15 | 16 |
| NW / Emerg. Lighting | 167 | 1 | 99.40 | 0.50 | 0.63 | 0.10 | 16 | 15 |

## Shortlist for further investigation

The exported `worst_cases_validation.csv` includes the three highest-MAE or highest-RMSE circuits at each horizon. Ranking uses unrounded values. High absolute error prioritises investigation; it does not establish a physical cause or intrinsic difficulty independent of circuit consumption scale.

| zone | horizon_h | n_valid | MAE_Wh | RMSE_Wh | absolute_error_share_pct | MAE_rank | RMSE_rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NW / Plugs & Sockets | 1 | 167 | 195.59 | 350.53 | 58.59 | 1 | 1 |
| SE / Lighting | 1 | 142 | 68.60 | 211.22 | 17.47 | 2 | 2 |
| SE / Plugs & Sockets | 1 | 98 | 36.06 | 53.43 | 6.34 | 3 | 4 |
| SW / Lighting | 1 | 121 | 15.02 | 59.72 | 3.26 | 5 | 3 |
| NW / Plugs & Sockets | 6 | 167 | 290.21 | 467.94 | 56.82 | 1 | 1 |
| SE / Lighting | 6 | 142 | 127.41 | 291.22 | 21.21 | 2 | 2 |
| SE / Plugs & Sockets | 6 | 98 | 47.28 | 66.92 | 5.43 | 3 | 3 |
| NW / Plugs & Sockets | 24 | 167 | 255.74 | 454.91 | 52.41 | 1 | 1 |
| SE / Lighting | 24 | 142 | 134.82 | 286.37 | 23.49 | 2 | 2 |
| SE / Plugs & Sockets | 24 | 98 | 58.91 | 77.41 | 7.08 | 3 | 3 |

### Handover to the other contributions

- **NW Plugs & Sockets:** compare its performance rank and error share with Part 2's night and episode analysis, then Part 3's training/validation level checks. Do not infer equipment changes from error metrics alone.
- **SE Lighting:** connect its MAE/RMSE to Part 2's 22 and 24 September afternoon cases. Part 3 should check measurement provenance and missing power readings before attributing the events to operations.
- **Other ranked cases:** retain the shortlist at every horizon rather than assuming that day-ahead rankings apply to +1 h and +6 h.
- **SE Plugs & Sockets:** interpret its metrics with its valid count and exclusion rate. Part 3's much smaller common-comparison sample answers a different question; do not mix the two counts.

## Limits

This is one validation week already used during model selection. The diagnosis is exploratory and does not provide an independent estimate of future generalisation. Availability differs across circuits and may change which operating conditions are scored. Absolute metrics depend on consumption scale; no training-mean-normalised metric is calculated from this file alone. No confidence intervals, significance tests, baseline rankings, physical causes or numerical improvement promises are inferred here. A lower zone MAE does not establish generalisation to unseen circuits.

## Reproduction and checks

Keep the script and input CSV together, then run:

```bash
python -m pip install pandas numpy
python performance_analysis.py
```

The script regenerates this report and four CSV tables in `outputs/`, plus a JSON record of input hash and checks. It validates the split, horizons, duplicate keys and finite values, and reconciles circuit-level metrics with directly pooled overall MAE/RMSE and error shares. Rerunning overwrites these generated files. It does not execute forecasting or modify the frozen model.
