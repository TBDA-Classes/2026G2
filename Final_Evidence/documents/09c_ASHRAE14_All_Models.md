# ASHRAE Guideline 14: all nine models compared

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 19 Nov 2026
**Author:** Lucía (written with the help of Claude, Anthropic)
**Script:** `Final_Evidence/scripts/ashrae14_all_models.py` · **Outputs:** `Final_Evidence/analysis/ashrae14_all_models_{test,validation}.csv` and `ashrae14_all_models_by_circuit_{test,validation}.csv`
**Slide:** `ASHRAE14_all_models_slide.pptx` (one slide, with speaker notes)

## 1. Question

`09_ASHRAE14_Assessment.md` checks **Blend v1.3 only**. Does Blend v1.3 also do better than the other models against ASHRAE 14?

## 2. Method (same as document 09)

- The script **imports the functions of `ashrae14_by_level.py`**, so the hours and the formulas are exactly the same as in document 09.
- Hours: the Task 6 common hours, valid for all nine models (1,911 circuit-hours per horizon on the test week).
- CV(RMSE) = 100 × RMSE / mean of the measurements.
- NMBE (ASHRAE sign) = 100 × Σ(measured − forecast) / Σ measured. Positive means the forecast is below the measurement.
- Hourly limits: CV(RMSE) ≤ 30 % and |NMBE| ≤ 10 %.
- Building total: the 16 circuits summed per hour, using only the hours where all 16 are valid.
- Check: the script gives the official Blend MAE again (22.15 / 34.73 / 34.16 Wh).
- **This is a report only. No model was chosen or tuned with it.** The model was fixed on validation on 29 Oct (rule D10).

## 3. Results, test week (29 Sep–5 Oct 2025)

Building total, CV(RMSE) % / NMBE %. **Bold** means the model fails at least one limit.

| Model | +1 h | +6 h | Day-ahead | Circuits passing (of 16) |
|---|---|---|---|---|
| **Blend v1.3** | 6.7 / −3.7 | 17.6 / −0.2 | 19.5 / −9.4 | 8 / 7 / 8 |
| Chronos-Bolt | 7.6 / −6.1 | 16.8 / −0.9 | **21.0 / −12.1** | 8 / 8 / 8 |
| ChronosGBM | 8.9 / −3.0 | 18.4 / 1.1 | 21.5 / −4.0 | 7 / 7 / 6 |
| GBM | 9.7 / −0.3 | 21.6 / −1.1 | 20.6 / 0.4 | 6 / 6 / 7 |
| Random forest | 8.7 / −3.5 | 22.8 / −0.7 | 22.5 / 0.5 | 6 / 7 / 7 |
| Linear regression | 7.8 / −4.4 | **23.2 / −11.7** | **23.4 / −11.7** | 6 / 7 / 6 |
| Baseline: persistence | 6.8 / −2.5 | **32.1 / −7.4** | 21.1 / 7.9 | 7 / 7 / 7 |
| Baseline: weekday median | **32.6 / 4.5** | **32.6 / 4.5** | **32.6 / 4.5** | 6 / 6 / 6 |
| Baseline: last week | **54.0 / −31.7** | **54.0 / −31.7** | **54.0 / −31.7** | 5 / 5 / 5 |

**Validation week (22–28 Sep), building total:** Blend v1.3 passes at all three horizons again (8.3 / −0.8, 18.7 / −0.2, 9.1 / 5.5). Chronos-Bolt and linear regression also pass on validation. GBM, random forest and ChronosGBM miss NMBE at some horizons (11.5 to 13.5 %). All values are in `ashrae14_all_models_validation.csv`.

## 4. What it shows

1. **Building: ASHRAE 14 is a reference check, not a ranking.** On the test week, Blend v1.3, ChronosGBM, GBM and random forest pass both limits at all three horizons; Chronos-Bolt misses NMBE at day-ahead, linear regression at +6 h and day-ahead, persistence misses CV(RMSE) at +6 h, and baselines B1 and B2 fail. On the validation week Blend v1.3 passes at all three horizons, but it was also the week used to choose it, so that is not independent evidence.
2. **Circuits: the models are close.** Between 5 and 8 of 16 circuits pass. Blend v1.3 and Chronos-Bolt are the best (8 of 16 at day-ahead). Small, spiky circuits (hand dryers, low-use lighting) fail for every model: their mean is a few Wh, so CV(RMSE) becomes very large.

## 5. Limits

- The building total uses only **12 hours** on the test week (10–11 on validation), because few hours have all 16 circuits valid. It is indicative, not statistically solid.
- ASHRAE 14 is written for **calibrating building energy models**. We use it as a reference, not a certification.
- The monthly criteria (15 % / 5 %) cannot be checked: one test week, about 8 weeks of data.

## 6. Proposed rows for the Evidence Map (`10_Evidence_Map.md`, section 2)

| # | Claim | File(s) |
|---|---|---|
| 24 | ASHRAE 14, all nine models, building total: Blend v1.3 passes both hourly limits at +1 h, +6 h and day-ahead; so do ChronosGBM, GBM and random forest on the test week (12 building hours: indicative). It is a reference check, not a ranking. | `Final_Evidence/documents/09c_ASHRAE14_All_Models.md`; `analysis/ashrae14_all_models_test.csv`, `ashrae14_all_models_validation.csv` |
| 25 | ASHRAE 14 by circuit, all nine models: 5 to 8 of 16 circuits pass; Blend v1.3 and Chronos-Bolt 8 of 16 at day-ahead | `analysis/ashrae14_all_models_test.csv`; `analysis/ashrae14_all_models_by_circuit_test.csv` |
