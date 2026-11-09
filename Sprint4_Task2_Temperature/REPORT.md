# Sprint 4 — Task 2: Integration and evaluation of outdoor temperature

**Model:** Blend v1.3 (frozen 29 Oct 2026)
**Evaluation data:** validation week, 22–28 Sep 2025 (UTC). The test week was not used.
**Decision:** temperature is **not added**. Blend v1.3 remains the final model.

## 1. Question

Outdoor temperature can drive heating and cooling demand. Can it help Blend v1.3 anticipate changes in consumption?

## 2. Temperature data

- **Source:** Open-Meteo Previous Runs API, hourly, at the CeDInt coordinates. The nearest grid point is 1.8 km away.
  Details and the reasons for the choice are in `data/temperature_source.md`.
- **Quality:**
  - complete: 1,776 of 1,776 hours, no duplicates;
  - plausible: 8.2–39.3 °C, in °C;
  - already hourly and in UTC, so it aligns with the energy dataset without aggregation;
  - consistent with the Casa de Campo station: daily correlation 0.983, mean difference −0.24 °C.

## 3. Method

**Two temperature inputs**, both known when the forecast is issued:

| Input | Definition | Why it is known at issue time |
|---|---|---|
| `temp_last` | Actual temperature of the last hour before the issue time | Same rule as the existing energy inputs |
| `temp_fc_target` | Forecast of the target hour, made 48 h before that hour | Target hours are at most 23 h after the issue time, so the forecast existed at least 25 h earlier |

The actual temperature of the target hour is **not** used: in real use it would not be known yet.

**Experiments:**

| ID | Description |
|---|---|
| E0 | GBM and ChronosGBM retrained with the frozen v1.3 inputs and parameters, combined with the frozen Chronos forecasts and the frozen Blend weights. This reproduces Blend v1.3. |
| E1 | As E0, plus the two temperature inputs in GBM and ChronosGBM. Same parameters, training rows, seed and Blend weights. |

- Only the GBM parts change. This follows decision D12: Chronos-Bolt cannot use external inputs.
- Parameters and Blend weights were not re-tuned. The validation week has already been used to select Blend v1.3, and
  more tuning on it would favour E1 unfairly.

**Decision rule:** the team's existing rule D10. E1 is adopted for a horizon only if it lowers the selection metric by
more than the tie margin (0.005). Smaller differences count as "no change", and then the simpler model, without
temperature, is kept. The selection metric is the mean scaled MAE over the 15 training circuits.

**Reproduction check:**
- GBM E0 reproduces the frozen forecasts exactly.
- ChronosGBM E0 reproduces +6h exactly. At +1h and day-ahead, retraining on another computer gives slightly different
  trees, although the inputs, parameters and seed are identical. The frozen `.joblib` models reproduce the saved
  forecasts exactly on our inputs.
- The resulting score differences are 0.0007 (+1h) and 0.0018 (day-ahead), below the 0.005 tie margin, so they cannot
  change the conclusion.
- E0 and E1 are trained in the same run, so their comparison is like for like.

## 4. Results

### 4.1 Selection metric (mean scaled MAE, 15 training circuits; lower = better)

| Horizon | Model part | E0 | E1 | Change | Result |
|---|---|---|---|---|---|
| +1h | GBM | 0.2824 | 0.3144 | +0.0319 | worse |
| +1h | ChronosGBM | 0.2658 | 0.2697 | +0.0040 | no clear change |
| +1h | **Blend** | **0.2709** | **0.2778** | **+0.0068** | **worse** |
| +6h | GBM | 0.3975 | 0.4561 | +0.0587 | worse |
| +6h | ChronosGBM | 0.3461 | 0.3696 | +0.0235 | worse |
| +6h | **Blend** | **0.3488** | **0.3568** | **+0.0080** | **worse** |
| day-ahead | GBM | 0.3970 | 0.3915 | −0.0055 | better |
| day-ahead | ChronosGBM | 0.3780 | 0.3738 | −0.0042 | no clear change |
| day-ahead | **Blend** | **0.3519** | **0.3516** | **−0.0003** | **no clear change** |

In the Blend, the GBM parts carry 50% (+1h), 45% (+6h) and 25% (day-ahead) of the forecast; Chronos carries the rest.
The changes in the Blend are therefore smaller than in the GBM parts.

### 4.2 Blend, MAE in Wh, all circuits

| Horizon | MAE E0 | MAE E1 | Change |
|---|---|---|---|
| +1h | 23.09 | 23.79 | +3.1% |
| +6h | 35.35 | 35.67 | +0.9% |
| day-ahead | 33.84 | 33.74 | −0.3% |

### 4.3 By zone, load type and circuit

- **Circuits:** E1 is better on 7, 6 and 11 of the 16 circuits at +1h, +6h and day-ahead. The median change is
  +0.3%, +0.3% and −0.2%: small and mixed.
- **Largest losses:** lighting circuits at short horizons.
  - SE Lighting at +1h: MAE +17%.
  - SW Lighting at +6h: MAE +32%.

  Lighting does not depend on temperature. The model is probably using temperature as a stand-in for time of day or
  season.
- **HVAC**, the load type temperature should affect most:
  - MAE +1.3% at +1h, +5.3% at +6h, −1.8% day-ahead.
  - NW HVAC, the most temperature-sensitive circuit (training correlation +0.50): +3.7%, +7.7%, −2.3%.
- **Zones:**
  - NE is better at +1h (−9%), but its errors are only about 3 Wh.
  - SE is worse at +1h (+12%) and SW at +6h (+9%).
  - Day-ahead changes in every zone are within ±2%.
- The two priority circuits from Task 1 hardly change. NW Plugs & Sockets moves between −0.6% and +0.4%; SE Lighting is
  +17% at +1h and within ±0.6% at the other horizons. Their errors are not temperature-related.

Figures: `outputs/fig_mae_change_by_circuit.png`, `outputs/fig_nw_hvac_before_after.png`.

## 5. Why temperature does not help here

1. **The validation week is colder than anything in training.**
   - Training (19 Aug–21 Sep) ranges from 13.2 to 35.2 °C, mean 23.9 °C.
   - Validation ranges from 8.2 to 25.7 °C, mean 16.5 °C.
   - 28% of validation hours are colder than the coldest training hour.

   Tree models cannot extrapolate: every temperature below the training range is treated like the coldest values they
   have seen (`outputs/fig_temperature_train_vs_validation.png`).
2. **Five summer weeks are not enough to learn a temperature response.**
   - NW HVAC drops from 124 Wh/h in training to 34 Wh/h in validation: the cooling is off.
   - Even with temperature, the model still predicts a cooling peak on 22 Sep that does not happen
     (`fig_nw_hvac_before_after.png`). Training never contains a cool afternoon.
3. **Temperature is mixed up with other changes.** August is both the hottest period and the university holidays. The
   model cannot separate the effect of heat from the effect of an empty building.
4. **The existing inputs already adapt.** Recent consumption (`last_val`, `mean_24`) reflects a load change within hours,
   so temperature adds little at short horizons.

## 6. Limitations

- One validation week, already used to select Blend v1.3: the results are indicative, not definitive.
- Only temperature was tested. Other weather variables (solar radiation, humidity) were not.
- The temperature is for a model grid point 1.8 km from the building, not a sensor on site.

## 7. Decision and recommendation

- **Decision:** temperature is **excluded**. E1 does not meet the decision rule: it is worse at +1h and +6h, and the
  day-ahead gain (−0.0003) is far below the 0.005 margin. **Blend v1.3 remains the final model** with no new dependency
  on a weather feed.
- **Recommendation:** retest temperature when the training data include cool and warm periods. Options:
  - more months of 2025–26 data;
  - the 2020–2023 hourly history, keeping the two periods separate as agreed.

  The data source, the two inputs and the script are ready to reuse.

## 8. Sprint 4 Definition of Done (Task 2 items)

| Item | Status |
|---|---|
| Temperature experiment completed, or exclusion justified | Done: completed and exclusion justified |
| Compared with Blend v1.3 on validation data | Done: same hours, same circuits |
| Choice based on quantitative results, no test-set tuning | Done: team rule D10 applied, test not used |
| Reproducible by another team member | Done: one script, saved data, `requirements.txt`, reproduction check |
