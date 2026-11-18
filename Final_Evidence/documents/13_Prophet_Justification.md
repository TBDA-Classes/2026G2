# Prophet (backlog PB-28) — why it was tested, how, and why it was not kept

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 18 Nov 2026
**Authors:** Maxime (main author, ran the test) · Claude (co-author)
**Experiment:** `Sprint4_Prophet_PB28/` (`run_prophet_validation.py`, `README.md`, `results/`, 4 unit tests)
**Related:** `10_Evidence_Map.md` row 17, `14_Evaluation_Protocol_Justification.md`, `TBDA_v1.3_ChronosGBM_29-10/DECISIONS_v1.2.md` (D6, D10, D11)

> **Reading note.** All numbers are validation scores (22–28 Sep 2025, 15 training circuits, mean scaled MAE) from `Sprint4_Prophet_PB28/results/comparison_validation.csv`. The test week was never used for Prophet.

## 1. Summary

- The backlog asked for a time-series alternative "such as Prophet" (PB-28). Chronos-Bolt filled that role, but Prophet itself had never been run (`Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md`: "Partly").
- Prophet was tested **under the same rules as the v1.3 models**: same data, tasks, scale, metric (D6) and tie rule (D10), **112 configurations** (teacher minimum 100, D11).
- Best Prophet: **0.473 / 0.472 / 0.472** (+1 h / +6 h / day-ahead) against **0.271 / 0.349 / 0.351** for Blend v1.3. **Not kept.** The model choice is unchanged.

## 2. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### P1 — Test Prophet at all

- **Decision.** Run Prophet as a documented experiment, not as a candidate for the final model.
- **Why.** PB-28 names Prophet explicitly, and "Why not Prophet?" is a predictable question. Without a test, the only honest answer was "not tested".
- **Evidence.** `06_Backlog_Coverage.md` (PB-28 "Partly"). The selection (D10) was already closed on 29 Oct, so Prophet could only be a reference.
- **Alternative rejected.** Answer with Chronos-Bolt only. It is a time-series model too, but not the one the backlog names.
- **Weakness.** Prophet came after the model choice. It cannot change the final model, only confirm that a classic decomposition model would not have been a better choice.

### P2 — Same protocol as every v1.3 model

- **Decision.** Reuse the team code (`forecast_tasks`, `series_scale`, `scaled_scores`, `d10_choose`) instead of writing a new evaluation.
- **Why.** A comparison is only fair if the tasks, hours, scale and metric are identical.
- **Evidence.** The script checks that the circuit scales equal the frozen GBM v1.3 config, and that the same scoring code gives the Blend score stored in `model_choice_v1.3.json` (both asserted). Two runs on the same machine gave byte-identical files, and a run on a second machine gave a byte-identical comparison table.
- **Alternative rejected.** Prophet's own cross-validation tools. They use their own windows and metrics, so the score would not be comparable.
- **Weakness.** Same single validation week as all models (see doc 14).

### P3 — One Prophet per circuit, fitted on training hours only, no refit

- **Decision.** Fit one model per training circuit on its valid training hours before 21 Sep 19:00 UTC (the earliest fit cut-off of the three horizons), then forecast the validation week without refitting.
- **Why.** The protocol forbids fitting on validation or test data (`task6.pdf` §9). Prophet only uses recent values through refitting, so it stays frozen at the end of training.
- **Evidence.** Unit test `test_train_frame_uses_training_hours_before_cutoff_only`. The forecast of an hour is the same at every horizon, which is why the three scores are almost equal (0.473 / 0.472 / 0.472).
- **Alternative rejected.** Daily refits during the week. That would mean fitting on validation hours, forbidden for every model.
- **Weakness.** This is the main reason Prophet loses (section 3). Prophet is used here as the protocol allows, not in its most favourable setting.

### P4 — Grid of 112 configurations

- **Decision.** Trend flexibility `changepoint_prior_scale` (7 values, 0.001–0.5) × seasonality strength `seasonality_prior_scale` (0.01, 0.1, 1, 10) × additive / multiplicative × one daily profile / separate weekday and weekend profiles. Weekly seasonality on, yearly off.
- **Why.** These are the settings that matter for Prophet. Yearly seasonality cannot be learnt from 5 weeks.
- **Evidence.** `results/prophet_tuning_log.csv`. Multiplicative beats additive (0.471 vs 0.514 day-ahead). The best trend setting (0.3) is inside the grid, not at its edge.
- **Alternative rejected.** Holiday effects: the training period has no Madrid public holiday, so there is nothing to learn.
- **Weakness.** No external inputs (temperature, calendar) were tried with Prophet.

### P5 — SE|Plugs & Sockets left out

- **Decision.** Prophet forecasts the 15 training circuits only.
- **Why.** SE|Plugs & Sockets is not a training circuit (D4: 86 % of its training hours flagged). Prophet cannot forecast a circuit it was not fitted on.
- **Evidence.** `DECISIONS_v1.2.md` D4. The selection score uses the same 15 circuits for every model.
- **Weakness.** Prophet has no cold-start answer. Chronos-Bolt does.

## 3. Result and reason

| Validation, mean scaled MAE | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| **Blend v1.3 (final model)** | **0.271** | **0.349** | **0.351** |
| Prophet (best of 112) | 0.473 | 0.472 | 0.472 |
| B3 persistence | 0.359 | 0.572 | 0.371 |
| B2 weekday × hour median | 0.522 | 0.521 | 0.522 |
| B1 same hour last week | 0.552 | 0.551 | 0.551 |

- **Strength.** Prophet beats both weekly baselines at every horizon: its trend and daily/weekly patterns are real information.
- **Why it loses.**
  1. It cannot use the last observed hours, which the lag-based models and Chronos-Bolt use, and so does persistence.
  2. The largest errors of the project come from level changes after training (NW Plugs & Sockets at night, SE Lighting at 1.92 × its training mean in validation: `Sprint4_Task1_Diagnosis`). A model that extrapolates the training pattern cannot follow them.
  3. Five training weeks are little for learning stable seasonal patterns.
- Per circuit (`results/per_circuit_validation.csv`), Prophet is close to the Blend on the quiet SW circuits and far behind it on the circuits whose level moved (SE Lighting 1.90 vs 1.04 day-ahead).

## 4. If we did it again

- Test Prophet in Sprint 3, next to the other candidates, so that it competes in the D10 selection instead of being checked afterwards.
- With a full year of data, try Prophet again with yearly seasonality and the UPM calendar as holidays. Its main strength, long seasonal patterns, cannot show on 8 weeks.
- A hybrid (Prophet profile + a short-term correction from recent hours) would address weakness 1. Not tested.

## 5. Likely questions

| Question | Short answer |
|---|---|
| Why did you test Prophet? | The backlog (PB-28) asked for it and it had not been tested. |
| Is the comparison fair? | Yes: same data, circuits, metric, tie rule, more than 100 configurations, validation only. |
| Why not refit it every day? | That means fitting on validation data, which the protocol forbids for every model. |
| Why the same score at every horizon? | Prophet does not use recent values, so its forecast for an hour does not depend on the horizon. |
| Why is it worse than persistence? | Persistence uses the last hour; Prophet only repeats the patterns it learnt. |
