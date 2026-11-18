# Sprint 4 — Backlog PB-28: Prophet tested under the team protocol

**Question.** The backlog (PB-28) asks for a time-series alternative "such as Prophet". Chronos-Bolt fills that role,
but Prophet itself was never tested: `Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md` marks PB-28
"Partly — Prophet itself was not tested". This folder tests it, so "Why not Prophet?" can be answered with a number.

**Answer.** Prophet does **not** help. On the validation week its best configuration (out of 112) scores 0.47 on every
horizon, against 0.27 / 0.35 / 0.35 for Blend v1.3. It beats the two weekly baselines everywhere, but it loses to
persistence at +1 h and day-ahead. Blend v1.3 stays the final model; nothing in the model choice changes.

## What was done

- **Same rules as every v1.3 model** (`TBDA_v1.3_ChronosGBM_29-10/`). The script reuses the team's code: dataset v1.2
  (checksum verified), forecast tasks (`forecast_tasks`), the circuit training mean as scale (checked against the frozen
  GBM v1.3 config), the selection score (mean scaled MAE over the 15 training circuits, D6) and the tie rule (D10).
- **Validation week only** (22–28 Sep 2025 UTC). No test row is built.
- **Grid of 112 configurations** (the teacher's minimum is 100): trend flexibility `changepoint_prior_scale` (7 values,
  0.001–0.5) × seasonality strength `seasonality_prior_scale` (0.01, 0.1, 1, 10) × additive or multiplicative
  seasonality × one daily profile or separate weekday/weekend profiles. Weekly seasonality on, yearly off (five weeks of
  data). Negative forecasts are clipped to 0, like every model.
- **How Prophet is fitted.** One model per circuit, fitted on that circuit's valid training hours before
  21 Sep 19:00 UTC. That is the earliest fit cut-off of the three horizons, so it is safe for all of them. Prophet is
  **not refitted** during the week, because the protocol forbids fitting on validation hours. It therefore extrapolates
  trend + seasonality and never sees the hours just before the issue time. Its forecast for an hour is the same at
  every horizon; the three scores differ only through each horizon's scale.
- **SE|Plugs & Sockets is left out.** It is not a training circuit (D4), and Prophet cannot forecast a circuit it was
  not fitted on. The score uses the 15 training circuits, like every model.
- **Checks.** The same scoring code reproduces the Blend v1.3 validation scores of `model_choice_v1.3.json` (asserted).
  Two runs on the same machine give identical files. Four unit tests: grid size, training hours only, clipping at 0,
  weekday/weekend profile.

## Result (validation, 15 training circuits, scaled MAE, lower is better)

| Model | +1 h | +6 h | Day-ahead |
|---|---|---|---|
| **Blend v1.3 (final model)** | **0.271** | **0.349** | **0.351** |
| Prophet (best of 112) | 0.473 | 0.472 | 0.472 |
| Baseline C (persistence, B3) | 0.359 | 0.572 | 0.371 |
| Baseline B (weekday × hour median, B2) | 0.522 | 0.521 | 0.522 |
| Baseline A (last week, B1) | 0.552 | 0.551 | 0.551 |

Baseline values are the team's own (`results/baseline_reference_v1.3.csv`). Scaled RMSE is in `results/comparison_validation.csv`.

**Chosen configuration (D10, same at every horizon).** `changepoint_prior_scale` 0.5, `seasonality_prior_scale` 0.1,
multiplicative seasonality, one daily profile. Four configurations are tied within 0.005; D10 picks the lowest scaled RMSE.

**What the grid shows.**
- Multiplicative seasonality is better than additive (best 0.471 against 0.514 at day-ahead).
- One daily profile is slightly better than separate weekday/weekend profiles (0.471 against 0.490).
- A more flexible trend helps up to `changepoint_prior_scale` 0.3 (0.592 at 0.001 → 0.471 at 0.3) and then stops
  (0.472 at 0.5). The optimum is inside the grid, not at its edge.

**Per circuit** (`results/per_circuit_validation.csv`). Prophet is close to Blend on the quiet SW circuits (for example
SW|Lighting 0.33 against 0.36 day-ahead), and far behind it on the circuits whose level moved after training:
SE|Lighting 1.90 against 1.04, NW|Lighting 1.10 against 0.66, and NW|HVAC 0.24 against 0.05.

## Why Prophet loses here

Prophet describes a series as trend + weekly and daily seasonality learnt from training. Under our protocol it cannot
read the last hours before the issue time. The lag-based models (GBM, ChronosGBM) and Chronos-Bolt can, and so can persistence. With five
training weeks, Prophet has little history to learn a seasonality from. And the largest errors of the project come
from level changes after training, which Task 1 documented on NW|Plugs & Sockets and SE|Lighting (SE|Lighting runs at
1.92 times its training mean in the validation week). A model that only extrapolates the training pattern cannot follow those changes. This also matches
the original reason for choosing Chronos-Bolt: it follows each circuit's recent level without being fitted on it.

## Limits

- **One validation week, already used to select Blend v1.3.** The comparison is exploratory, like Sprint 4 Tasks 1 and
  2. Prophet is not a candidate, and the test week was not used.
- **No refit, by protocol.** Refitting Prophet every day would let it use recent data, but it would mean fitting on
  validation hours. The team protocol forbids that for every model.
- **Reproducibility on another machine.** Prophet's optimiser (Stan) can give slightly different numbers on another
  computer or with another version. Expect the same picture, not the same last decimal. Versions used: Prophet 1.5.0,
  cmdstanpy 1.3.2 (recorded in `results/prophet_chosen_config.json`).
- **Suggested backlog update** (for the Task 4 owner): PB-28 → Covered: "Prophet tested on validation under the v1.3
  protocol (112 configurations), not adopted. Chronos-Bolt remains the time-series alternative. `Sprint4_Prophet_PB28/`".

## Files

| File | Content |
|---|---|
| `run_prophet_validation.py` | The only script; writes everything in `results/` |
| `tests/test_prophet_pb28.py` | 4 unit tests on toy data |
| `results/comparison_validation.csv` | Prophet vs Blend v1.3 vs baselines, per horizon |
| `results/per_circuit_validation.csv` | Scaled MAE per circuit: Prophet, Blend v1.3, Baseline B |
| `results/prophet_tuning_log.csv` | All 112 configurations × 3 horizons, with D10 columns |
| `results/prophet_validation_predictions.csv` | Validation forecasts of the chosen configuration |
| `results/prophet_chosen_config.json` | Chosen configuration, cut-offs, training hours, versions |

## How to run

From the repository root, with the team environment plus Prophet (`pip install prophet==1.5.0`):

```
python Sprint4_Prophet_PB28/run_prophet_validation.py      # about 3 minutes
pytest -q Sprint4_Prophet_PB28/tests
```

*Written with the help of Claude (Anthropic) and submitted by Maxime (mlestrat).*
