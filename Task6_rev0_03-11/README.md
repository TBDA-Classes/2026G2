# Task 6 — Final model comparison (Sprint 3)

**Owner:** Edoardo Menegozzo · **Date:** 3 Nov 2026 · **Results:** [RESULTS.md](RESULTS.md)

This task compares every forecasting model of the team on exactly the same hours. It reports MAE and RMSE with 95% confidence intervals and says which model is best for each horizon and zone.

**Main result:** the final model, Blend v1.3, has a test MAE of 22.2 / 34.7 / 34.2 Wh at +1 h / +6 h / day-ahead on all 16 circuits. It is the best model, or tied with the best, at every horizon, and it beats Baseline B everywhere.

![Test MAE with 95% CI](figures/task6_test_mae_16circuits.png)

## What I did

1. **Collected all models.** There are 11:
   - **Baselines** B1, B2 and B3.
   - **Sprint 3 models:** Linear Regression, Random Forest, GBM v1.0 and Chronos-Bolt Small v1.1.
   - **v1.3 models:** GBM v1.3, Chronos-Bolt v1.3, ChronosGBM v1.3 and Blend v1.3.
2. **Regenerated the forecasts from the frozen models** and checked them against each owner's numbers (table below). Nothing was fitted or tuned again.
3. **Rebuilt Model 1 (Linear Regression)** from its `PARAMETERS.md`, because its script was not in the repository. Its test forecasts match the official file within 0.0005 Wh, so I could use its validation forecasts.
4. **Ran the frozen v1.3 models on the test week.** This covers GBM v1.3, ChronosGBM v1.3 and Blend v1.3, using Emily's Chronos v1.3 test forecasts. Each test was run once, after the final model had been chosen on validation (rule D10, 29 Oct).
5. **Built one fair comparison** (`task6_compare.py`):
   - **Same hours.** Only hours that are valid in both dataset versions (v1.1 and v1.2) and forecast by every model are scored. Where both are valid, the actual values are identical.
   - **Metrics.** MAE (primary), RMSE, WAPE, and scaled MAE (MAE ÷ the circuit's training mean).
   - **Confidence intervals.** 95% CIs from a circular block bootstrap: 24-hour blocks, 2,000 resamples, with all circuits of an hour kept together.
   - **Pairwise tests.** Every pair of models is compared. A difference counts as significant only if its CI excludes 0.
   - **Groupings.** All circuits, NE/NW, SE/SW, and each zone.
6. **Ran six comparisons:** test and validation, each on 16 and on 8 circuits, plus the two test runs without the NE|HVAC event of 3 Oct.
7. **Error analysis:** by hour of day, weekday/weekend, date, circuit, and hours ahead.

## Checks

| Model | Check | Result |
|---|---|---|
| B1, B2, B3, GBM v1.0 | validation MAE, 8 circuits, 1,120 h | 66.7 / 54.2 / 31.3 / 33.3 Wh, identical to the Sprint 3 report |
| GBM v1.0, B1–B3 (dataset v1.1) | test MAE per circuit | 96/96 identical to `task1_rf_test_comparison.csv` |
| Linear Regression | rebuilt test forecasts | max. difference 0.0005 Wh |
| Linear Regression | validation scaled MAE | 0.340 / 0.392 / 0.395, identical |
| Chronos-Bolt Small v1.1 | validation scores | 0.254905 / 0.338586 / 0.322740, identical |
| Chronos-Bolt v1.3 | validation scores | identical |
| Chronos-Bolt v1.3 | test forecasts vs Emily's file | difference < 1e-12 Wh |
| GBM v1.3, ChronosGBM v1.3, Blend v1.3 | validation scores | equal to the 3rd–4th decimal |

## Folder

| Path | Content |
|---|---|
| `RESULTS.md` | which model is best, all tables, error analysis |
| `task6_compare.py` | the comparison (same hours, metrics, bootstrap CIs, pairwise tests, error tables) |
| `run_task6_all.sh` | runs all six comparisons and the figure |
| `minipq.py` | small Parquet reader (our environment had no pyarrow) |
| `generation/run_task6_v13_predictions.py` | v1.3 forecasts from the frozen models; run inside the TBDA_v1.3 folder |
| `generation/task6_linear_rebuild.py`, `generation/run_task6_v11_validation.py` | Linear rebuild and v1.1 validation forecasts; run inside Task78_rev0_19-10 |
| `data/` | circuit scales for scaled MAE, list of the test events |
| `results/predictions/` | one CSV per model and split: `<model>_test_predictions.csv`, `<model>_validation_predictions.csv` |
| `results/task6_<split>_<n>circuits[_without_events]/` | `metrics_with_CI.csv`, `pairwise_differences.csv`, `best_model_per_scope.csv`, `metrics_per_circuit.csv`, `circuit_wins.csv`, `error_by_*.csv`, `alignment_checks.csv`, `mae_with_ci.png`, `log.txt` |
| `figures/` | `task6_test_mae_16circuits.png` and the script that makes it |

## How to run

```
pip install pandas numpy matplotlib
bash run_task6_all.sh          # ~1 min, rewrites results/task6_*/ and figures/
```

## Model names in the files

| File name | Model | Dataset | Trained on → forecasts |
|---|---|---|---|
| `B1_last_week` | Baseline A, same hour last week | v1.2 | — → 16 |
| `B2_weekday_hour_median` | Baseline B, training median per weekday × hour | v1.2 | — → 16 |
| `B3_persistence` | Baseline C, last valid hour (≤ 24 h old) | v1.2 | — → 16 |
| `ML_Linear` | Linear Regression, pooled LAD, design B | v1.1 | 8 → 16 |
| `ML_RandomForest` | Random Forest, pooled | v1.1 | 8 → 16 |
| `ML_GBM_v1.0` | Gradient boosting, Sprint 2 | v1.1 | 8 → 8 |
| `ML_GBM_v1.3` | Gradient boosting, v1.3 grid | v1.2 | 15 → 16 |
| `ML_Chronos_v1.1` | Chronos-Bolt Small, zero-shot | v1.1 | — → 8 |
| `ML_Chronos_v1.3` | Chronos-Bolt v1.3 (base/tiny/base) | v1.2 | — → 16 |
| `ML_ChronosGBM_v1.3` | GBM with Chronos inputs | v1.2 | 15 → 16 |
| `ML_Blend_v1.3` | **final model**, weighted average of GBM, ChronosGBM and Chronos v1.3 | v1.2 | 15 → 16 |
