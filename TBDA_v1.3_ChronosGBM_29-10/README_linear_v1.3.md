# Linear model — extended grid v1.3

Script: `run_v13_linear_tune.py` · test: `tests/test_linear_v13.py` · results: `results/linear_tuning_log_v1.3.csv`,
`results/linear_validation_predictions_v1.3.parquet`, `models/linear_frozen_config_v1.3.json`.

**Protocol.** Same as the other v1.3 models: dataset v1.2, splits of `config.py`, inputs of `task8_model.FEATURES`,
fitted on the 15 training circuits, scored on all validation forecasts, selection = mean scaled validation MAE over the
training circuits (D6), ties inside the grid by rule D10. **The test period is never built or read.** The committed
model choice (`models/model_choice_v1.3.json`) is not changed; the linear model is *not* a D10 candidate there.

**Grid (132 configurations per horizon).** 2 modes (pooled, per_series) x [ridge, 13 alphas 0.001..1000 + LAD, 9 alphas
0..0.1] x 3 clip rules (none, minmax, p01_p99). The clip limits the standardised numeric inputs to the training range
(or its 1st-99th percentile); it does not touch one-hot or "was missing" columns. This answers the two open points in
`README_Task1_linear.md` (best alpha at the edge of the grid; clipping of inputs).

## Result (validation, mean scaled MAE, lower is better)

| Horizon | Linear v1.3 (D10 choice) | Sprint 3 setting (LAD 1e-3, no clip) | ML_Blend (committed choice) | Best baseline |
|---|---|---|---|---|
| +1h | 0.2919 (per_series, LAD 0.01, p01_p99) | 0.3007 | 0.2712 | 0.3586 (B3) |
| +6h | 0.3975 (per_series, LAD 0.01, p01_p99) | 0.4141 | 0.3488 | 0.5211 (B2) |
| day-ahead | 0.3905 (pooled, LAD 0.01, no clip) | 0.3998 | 0.3513 | 0.3708 (B3) |

The "Sprint 3 setting" column is the best of the two modes: per_series at +1h, pooled at +6h and day-ahead.

What it shows:
- **Alpha:** the best LAD alpha moves from 0.001 to 0.003-0.01; alpha 0.1 is worse at every horizon, so the optimum is
  now inside the grid, not at its edge.
- **Clip:** p01_p99 helps at +6h (0.3975 vs 0.4089 without) and slightly at +1h (0.2910 vs 0.2976); at day-ahead it does
  not help (0.3884 vs 0.3871). Gains are small, not systematic.
- **Loss:** LAD beats ridge at every horizon (best 0.291 vs 0.363 at +1h).
- **Versus the committed choice:** the linear model stays 0.02-0.05 behind ML_Blend, far outside the D10 tie margin
  (0.005). At day-ahead it is also behind persistence B3 (0.3708). Validation only: no claim about the test week.

Caveat: scores are on dataset v1.2 / 16 circuits and differ from the Sprint 3 README numbers (v1.1, 8 circuits).

## Status and limits (please read)
- **Reference model, not a candidate.** The linear model is not a D10 candidate (D10a) and `models/model_choice_v1.3.json`
  is unchanged. This grid documents the linear model with the same >= 100 configurations per model as the others (D11).
- **Where the clipping idea comes from.** `README_Task1_linear.md` (Sprint 3, Mert) lists clipping the inputs as a possible
  fix after the NE|HVAC jump of 3 Oct, an event seen in the **test** week. Here clipping is only *evaluated* on validation
  and nothing is tuned on test, but the decision to try it is not independent of the test week. Anyone using this result
  should say so.
- **Not reproduced by a second person yet.** The full run (about 25 min) was done once. A 2-configuration smoke run
  (`python run_v13_linear_tune.py --smoke`, writes to `results/smoke/`) can be used to check the environment.
- **Authorship.** Extends the Sprint 3 linear model (`task1_linear.py`, Mert). This code was written with the help
  of Claude (Anthropic) and submitted by Maxime (mlestrat).
