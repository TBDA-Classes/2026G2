# Task 6 — Results: which model is best

**Short answer:** the final model **Blend v1.3** (`ML_Blend_v1.3`) is the best model, or tied with the best, at every horizon. On the test week (16 circuits) its MAE is **22.2 Wh at +1 h, 34.7 Wh at +6 h and 34.2 Wh day-ahead**. That is 49%, 21% and 22% below Baseline B, and every one of these differences is significant. It beats persistence significantly only at +6 h; at +1 h and day-ahead it is lower than persistence, but tied.

Test week 29 Sep – 5 Oct 2025. Every model is scored on the same hours: 1,911 per horizon on the 16 circuits and 1,318 on the 8 NE/NW circuits. MAE is in Wh, and lower is better. A model counts as better only when the 95% CI of the MAE difference excludes 0.

![Test MAE with 95% CI, 16 circuits](figures/task6_test_mae_16circuits.png)

## 1. Test, all 16 circuits

| Model | MAE +1 h | MAE +6 h | MAE day-ahead | RMSE +1 h | RMSE +6 h | RMSE day-ahead | scaled MAE day-ahead |
|---|---|---|---|---|---|---|---|
| **Blend v1.3 (final model)** | 22.2 | 34.7 | **34.2** | 93.5 | 135.5 | 139.0 | **0.498** |
| Chronos-Bolt v1.3 | **21.5** | 36.9 | 36.2 | **87.6** | 139.3 | 148.5 | 0.506 |
| ChronosGBM v1.3 | 24.7 | **34.2** | 35.9 | 105.6 | 139.6 | 147.0 | 0.521 |
| Gradient boosting v1.3 | 26.3 | 37.1 | 35.7 | 113.3 | 148.7 | 143.9 | 0.514 |
| Random Forest | 27.7 | 37.4 | 37.4 | 108.9 | 140.5 | 141.4 | 0.551 |
| Linear Regression | 25.1 | 39.4 | 39.7 | 95.5 | 135.9 | **138.0** | 0.642 |
| Baseline C (persistence) | 24.0 | 57.8 | 41.5 | 98.5 | 208.0 | 167.6 | 0.536 |
| Baseline B (weekday × hour) | 43.7 | 43.7 | 43.7 | 165.5 | 165.5 | 165.5 | 0.596 |
| Baseline A (last week) | 59.1 | 59.1 | 59.1 | 204.1 | 204.1 | 204.1 | 0.697 |

95% CIs for every value: `results/task6_test_16circuits/metrics_with_CI.csv`.

## 2. Best model per horizon

| Horizon | Lowest test MAE | Blend v1.3 vs best | Blend v1.3 vs Baseline B | Blend v1.3 vs persistence |
|---|---|---|---|---|
| +1 h | Chronos-Bolt v1.3 (21.5) | +0.6 Wh, tie | −21.6 Wh (CI −26.9 to −16.7), **better** | −1.8 Wh (CI −4.7 to +2.6), tie |
| +6 h | ChronosGBM v1.3 (34.2) | +0.5 Wh, tie | −9.0 Wh (CI −12.4 to −4.9), **better** | −23.1 Wh (CI −31.8 to −15.7), **better** |
| day-ahead | **Blend v1.3** (34.2) | — | −9.6 Wh (CI −14.9 to −4.2), **better** | −7.3 Wh (CI −16.8 to +0.1), tie (significant in scaled MAE) |

- Blend v1.3 beats Baseline B on 16, 14 and 14 of the 16 circuits (+1 h, +6 h, day-ahead).
- **At +1 h** the Blend is significantly better than gradient boosting v1.3 and Random Forest. **At +6 h and day-ahead** it is significantly better than Chronos-Bolt v1.3 alone. The other day-ahead differences between ML models are ties.
- **At +1 h** no model is significantly better than persistence. The closest is Chronos-Bolt v1.3: −2.4 Wh, CI −4.5 to +0.1.
- **Without the NE|HVAC event of 3 Oct**, the conclusions are the same (`results/task6_test_16circuits_without_events/`).
- **On the SE/SW circuits**, which are not or barely in training, persistence has the lowest MAE at +6 h and day-ahead.

## 3. The 8 NE/NW circuits (continuity with Sprints 2 and 3)

| Model | Val +1 h | Val +6 h | Val day-ahead | Test +1 h | Test +6 h | Test day-ahead |
|---|---|---|---|---|---|---|
| Blend v1.3 (final model) | 27.8 | **40.7** | 36.0 | 29.4 | 46.0 | 43.8 |
| Chronos-Bolt v1.3 | 26.4 | 41.6 | **35.0** | **28.5** | 49.1 | 46.9 |
| ChronosGBM v1.3 | 30.2 | 41.3 | 44.8 | 32.3 | 44.3 | **42.7** |
| Gradient boosting v1.3 | 32.6 | 43.6 | 41.9 | 34.6 | 46.8 | 43.5 |
| Chronos-Bolt Small v1.1 | **26.1** | 41.4 | 37.4 | 29.0 | **42.1** | 43.6 |
| Random Forest | 27.6 | 41.9 | 41.5 | 33.0 | 44.2 | 43.7 |
| Linear Regression | 30.0 | 43.4 | 43.5 | 31.4 | 45.5 | 45.6 |
| Gradient boosting v1.0 (Sprint 2) | 33.3 | 46.4 | 48.3 | 35.1 | 48.9 | 47.8 |
| Baseline C (persistence) | 31.3 | 66.8 | 58.2 | 31.5 | 79.7 | 54.8 |
| Baseline B | 54.2 | 54.4 | 54.2 | 47.8 | 47.8 | 47.8 |
| Baseline A | 66.7 | 66.7 | 66.7 | 60.5 | 60.5 | 60.5 |

On these 8 circuits the top models are tied at every horizon.

Compared with the Sprint 2 model (gradient boosting v1.0):
- **Blend v1.3** is significantly better at +1 h (−5.7 Wh, CI −10.9 to −1.5).
- **Gradient boosting v1.3 and Random Forest** are significantly better day-ahead.
- **Random Forest, Linear Regression and Chronos-Bolt Small** are significantly better at +6 h.

## 4. Validation, all 16 circuits (where the final model was chosen)

| Model | +1 h | +6 h | day-ahead |
|---|---|---|---|
| Chronos-Bolt v1.3 | **19.1** | 31.6 | **27.5** |
| Blend v1.3 | 19.7 | **31.3** | 28.8 |
| ChronosGBM v1.3 | 21.4 | **31.3** | 36.5 |
| Linear Regression | 22.9 | 35.7 | 36.2 |
| Gradient boosting v1.3 | 23.3 | 39.0 | 37.7 |
| Random Forest | 23.9 | 39.9 | 39.8 |
| Baseline C (persistence) | 22.8 | 50.6 | 38.5 |
| Baseline B | 48.6 | 48.8 | 48.7 |
| Baseline A | 55.9 | 55.9 | 55.9 |

Rule D10 (scaled MAE, tie margin 0.005, tie-break scaled RMSE) chose Blend v1.3 at every horizon on 29 Oct. The Blend weights (gradient boosting v1.3 / ChronosGBM v1.3 / Chronos-Bolt v1.3) are 0.30/0.20/0.50 at +1 h, 0.10/0.35/0.55 at +6 h and 0.15/0.10/0.75 day-ahead. Chronos-Bolt v1.3 alone was best on validation day-ahead (27.5 Wh) but is weaker on the test week (36.2 Wh). The combination is more stable.

## 5. Where the errors are (test, 16 circuits, day-ahead, Blend v1.3)

- **Hour of day.** The error is 49.4 Wh at 00–05 h, 46.1 at 06–08 h, 24.8 at 09–13 h, 28.5 at 14–18 h and 21.5 at 19–23 h.
  - Between 00:00 and 09:00, 79% of the error comes from **NW|Plugs & Sockets**.
  - Its mean night consumption rises from 514 Wh/h in training to 980 Wh/h in validation and 1,043 Wh/h in test (1,924 Wh/h on the night of 30 Sep).
  - This is a change in operation that should be checked with the data owner.
- **Weekday / weekend.** 41.3 Wh on weekdays vs 19.1 Wh at the weekend.
- **Circuit.** NW|Plugs & Sockets 250.9 Wh, NW|Lighting 49.1, SE|Lighting 40.4, NW|HVAC 28.9, SE|Plugs & Sockets 24.9. All other circuits are below 11 Wh.
- **Hours ahead.** 49.7 Wh (1–3 h), 48.0 (4–6), 35.4 (7–12), 29.6 (13–18), 21.4 (19–24). The error does not grow with the hours ahead. Forecasts are issued at 00:00, so hours ahead equal the clock hour, and this is the same night effect.
- **Events.** Removing the NE|HVAC run of 3 Oct changes MAE by less than 1 Wh (34.2 → 33.7) but almost halves scaled MAE (0.498 → 0.264). The 18 impossible NW|Emerg. Lighting hours are invalid in dataset v1.2 (D2), so they are not scored.

## 6. Limitations

- There is one test week only, so many differences between the best models are ties.
- Two dataset versions are compared (v1.1 and v1.2). Only hours valid in both are scored.
- SE/SW coverage in the test week is low; for example, SE|Plugs & Sockets has 63 of 168 hours scored.
- Power (W) and current (I) were not modelled by any model.
