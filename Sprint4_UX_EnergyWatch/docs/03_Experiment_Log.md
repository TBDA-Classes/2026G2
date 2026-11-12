# Experiment Log — forecasting and detection (reconstructed from the repository)

**Backlog item:** PB-31 (reproduce model experiments; trace how the final model was selected)
**Version:** 12 Nov 2026
**Method:** this log was **reconstructed from the repository** (`TBDA-Classes/2026G2`): Git history (dates and author handles), READMEs, decision files, frozen configuration files and tuning logs. Nothing was added that is not in those files. Where the repository does not record a value, the cell says **not recorded**. Each row gives its source so it can be checked.

Author names are the GitHub handles shown by `git log`.

---

## 1. Fixed protocol (applies to every experiment from v1.2)

| Item | Value | Source |
|---|---|---|
| Target, horizons | `energy_Wh` hourly; +1 h, +6 h, day-ahead (issued 00:00 Madrid) | `README_parameters.md` §1 |
| Split (UTC) | train 19 Aug–21 Sep 2025; validation 22–28 Sep; test 29 Sep–5 Oct | same |
| Fit rule | fit on train only; configuration chosen on validation and frozen; test used once | same |
| Metrics | MAE (primary), RMSE; selection metric = mean scaled MAE (MAE ÷ circuit training mean) over the 15 training circuits | same |
| Seed | 0 | `config.py` |
| Baselines | B1 same hour last week (168 h); B2 weekday × hour median over train; B3 persistence (last valid hour ≤ 24 h) | same |

## 2. Chronological log

| # | Date | Owner (handle) | Experiment | Data | Setup | Result | Decision | Source |
|---|---|---|---|---|---|---|---|---|
| E01 | 19 Oct 2026 | akupelian-uni | **Tasks 7 & 8:** baselines B1, B2; first ML model, gradient boosting (GBM v1.0); persistence B3 added | v1.1, 8 NE/NW circuits | GBM grid: mode {pooled, per_series}, learning rate {0.05, 0.1}, max leaf nodes {15, 31}, min samples per leaf {20, 50}; loss absolute error, 300 iterations, no early stopping. Chosen: pooled; lr 0.05 / 0.05 / 0.1; leaves 15 / 15 / 15; min leaf 50 / 20 / 50 | Validation MAE at +1 h on 1,120 hours: B1 66.7, B2 54.2, B3 31.3, GBM 33.3 Wh. ML clearly beats B1/B2 at +1 h (7 of 8 circuits); at +6 h and day-ahead it matches but does not beat B2. B3 is better on validation and about level on test | GBM adopted as first ML model; B3 kept as a reference | `Task7&8_rev0_19-10.zip`, `TBDA_Task7_Task8_Summary.pdf`, `README_parameters.md` §3b |
| E02 | 26 Oct 2026 | akupelian-uni | **Sprint 3 Task 3:** Chronos-Bolt Small, zero-shot (nothing fitted on our data) | v1.1, 8 circuits | Context length grid {168, 336, 504, 672 h}; quantiles 0.1/0.5/0.9; point = median; chosen context 168 / 504 / 504 h | Validation scaled MAE 0.254905 / 0.338586 / 0.322740 (reproduced exactly in Task 6) | Kept as a candidate | `Chronos_rev0_26-10.zip`, `README_parameters.md` §3d, `Task6_rev0_03-11/README.md` |
| E03 | 27 Oct 2026 | emilebeyries2 | **Model 3, Random Forest** (pooled), final Sprint 3 version | v1.1, 8 circuits | Parameters in the technical report | 8-circuit MAE, validation 27.6 / 41.9 / 41.5 Wh; test 33.0 / 44.2 / 43.7 Wh | Kept as a candidate | `Model3_RandomForest.zip`, `Informe Técnico - Modelo Random Forest (Edoardo) (2).pdf`, `Task6_rev0_03-11/RESULTS.md` §3 |
| E04 | Sprint 3 (rebuilt 2 Nov) | Emily (report); mertk1280 (upload) | **Model 1, Linear Regression** | v1.1, 8 circuits (rebuilt for 16) | Mode {pooled, per_series}; ridge α {0.01, 1, 10, 100}; LAD α {0, 1e-4, 1e-3}; chosen LAD α 1e-3 at all horizons (per_series at +1 h, pooled otherwise) | Validation scaled MAE 0.340 / 0.392 / 0.395; 8-circuit MAE validation 30.0 / 43.4 / 43.5 Wh | Kept as a candidate | `Model1_LinearRegression_all16_02-11 (1).zip`, `README_parameters.md` §3c |
| E05 | 28 Oct 2026 | not recorded (v1.2 package) | **Dataset v1.2 and decisions D1–D9**, written *before* any v1.2 score; trigger: teacher feedback (all zones and circuits) | v1.2, 16 circuits | Validity rule changed from ≥ 30 readings to ≥ 1 reading (with a 15-min gap cap); inconsistency rule energy > 2 × power + 1 Wh; 15 training circuits | v1.1 rule had excluded all SE and SW circuits. v1.2 forecasts all 16 | v1.2 adopted; old v1.1 files kept | `DECISIONS_v1.2.md`, `PROTOCOL_NOTE_v1.2.md` |
| E06 | 28 Oct 2026 | not recorded (v1.2 package) | **v1.2 model runs:** GBM, Chronos-Bolt, ChronosGBM hybrid, blend of GBM and Chronos | v1.2 | GBM chosen lr 0.1 / 0.05 / 0.1, leaves 31 / 15 / 15, min leaf 50 / 20 / 50. Chronos context 672 / 504 / 168 h. Hybrid pooled, lr 0.05 / 0.05 / 0.1, leaves 31 / 31 / 31, min leaf 20 / 50 / 20. Blend weight of GBM 0.5 / 0.0 / 0.0 | At day-ahead, persistence (0.3708) was within 0.0047 of Chronos (0.3661) on validation, inside the noise level | Led to the tie rule D10 | `README_parameters.md` §3b–3e, `DECISIONS_v1.2.md` (D10a) |
| E07 | 29 Oct 2026 | Emily Wiesner, Alex (as written in `model_choice_v1.3.json`) | **Rule D10 agreed:** tie margin 0.005 scaled MAE, tie-break by scaled RMSE, identical forecasts → simpler model. Option B: baselines cannot be chosen but are tracked (D10c) | v1.2 | `D10_TIE_MARGIN = 0.005` | Under option A persistence would have been chosen at day-ahead (gap 0.0047) | Option B | `DECISIONS_v1.2.md` addendum, `config.py` |
| E08 | 30 Oct 2026 | emilywiesner | **Extended grids v1.3** (teacher: ≥ 100 combinations per model) and final model per horizon | v1.2 | GBM 128 combinations (lr × leaves × min leaf × L2, pooled); ChronosGBM 128; Chronos-Bolt 104 (size × context × point forecast); Blend 231 (weights on a 0.05 grid). Tuning log rows: GBM 384 and ChronosGBM 384 (128 × 3 horizons), Chronos 312, Blend 693 | See §3 below | **Blend v1.3** chosen at all three horizons, committed before any test forecast | `README_v1.3.md`, `results/*_tuning_log_v1.3.csv`, `models/model_choice_v1.3.json` |
| E09 | 3–4 Nov 2026 | emilywiesner; Edoardo Giuseppe Menegozzo | **Task 6: single test run and final comparison** of 11 models on identical hours; 95 % block-bootstrap CIs (24 h blocks, 2,000 resamples) | v1.1 and v1.2 common hours | Each frozen model run once on the test week. Forecasts regenerated and checked against each owner's numbers (identical to 3–4 decimals, Chronos test forecasts differ < 1e-12 Wh) | Blend v1.3 test MAE 22.2 / 34.7 / 34.2 Wh (+1 h / +6 h / day-ahead); 49 %, 21 %, 22 % below baseline B | Blend v1.3 confirmed | `Task6_rev0_03-11/RESULTS.md` |
| E10 | 2 Nov 2026 | mlestrat | Post-hoc error analysis of the linear model by hour of day (descriptive) | test | — | Descriptive only | None | `docs/linear_error_by_hour/README.md` |
| E11 | 6–9 Nov 2026 | francicas, Krystianmaron (Task 1); luciamate (Task 2) | **Sprint 4 Task 1:** diagnosis of Blend v1.3 errors (performance, temporal, data conditions). **Task 2:** outdoor temperature (E0 reproduces Blend; E1 adds `temp_last` and `temp_fc_target` to GBM and ChronosGBM) | validation week | Same parameters, seed and weights for E0 and E1; decision rule D10 | Task 1: NW Plugs & Sockets and SE Lighting carry 75.9 % of pooled day-ahead absolute error. Task 2: Blend scaled MAE E0 → E1 = 0.2709 → 0.2778 (+1 h, worse), 0.3488 → 0.3568 (+6 h, worse), 0.3519 → 0.3516 (day-ahead, no clear change) | Temperature **not** adopted; Blend v1.3 unchanged | `Sprint4_Task1_Diagnosis/CONCLUSIONS.md`, `Sprint4_Task2_Temperature/REPORT.md` |
| E12 | 12 Nov 2026 | Jules (UX) | **Detection design and impact model** for the dashboard: expected = Blend v1.3 day-ahead, normal range = Chronos-Bolt q10–q90, three sensitivities | validation + test week | See `02_Assumptions_and_Decisions.md` | 66 / 73 / 78 alerts in 14 days; known NE HVAC event detected at all sensitivities | Balanced sensitivity as default | `build_data.py` |
| E13 | 12 Nov 2026 | Jules (UX) | **Injected-anomaly test** of the detector (PB-38) | validation + test week | about 43,500 synthetic cases per sensitivity (43,324–43,724) (4 magnitudes × 3 durations × occupied/out-of-hours × start hours × 16 circuits) | See `04_Detection_Validation.md` | Limits documented | `injection_test.py` |

## 3. Outcome of the v1.3 selection (E08), per horizon

Validation scores, selection metric = mean scaled MAE over 15 training circuits (`models/model_choice_v1.3.json`, `models/*_frozen_config_v1.3.json`):

| Horizon | Final model | Validation score | Scaled RMSE | Best baseline | Best baseline score | Gap to baseline | Tied candidates |
|---|---|---|---|---|---|---|---|
| +1 h | Blend | 0.2712 | 0.6078 | B3 persistence | 0.3586 | −0.0874 | ChronosGBM, Blend |
| +6 h | Blend | 0.3488 | 0.7059 | B2 weekday × hour | 0.5211 | −0.1723 | ChronosGBM, Blend |
| day-ahead | Blend | 0.3513 | 0.7027 | B3 persistence | 0.3708 | −0.0195 | Chronos, Blend |

No baseline lies within the tie margin of the chosen model at any horizon (`baselines_within_tie_margin` is empty).

Frozen configurations (v1.3):

| Component | +1 h | +6 h | day-ahead |
|---|---|---|---|
| Blend weights (GBM / ChronosGBM / Chronos) | 0.30 / 0.20 / 0.50 | 0.10 / 0.35 / 0.55 | 0.15 / 0.10 / 0.75 |
| Chronos-Bolt | base, context 588 h, mean of quantiles | tiny, context 24 h, median | base, context 72 h, median |
| GBM grid index (pooled) | 77 | 65 | 34 |
| ChronosGBM grid index (pooled) | 28 | 37 | 15 |
| Training rows (GBM) | 10,145 | 10,070 | 10,115 |

Model files are identified by SHA-256 in the frozen configuration files.

## 4. Lessons recorded in the repository
1. One validation week cannot separate models closer than about 0.005 scaled MAE; hence rule D10 (E06, E07).
2. Persistence is a strong rival at +1 h and day-ahead; no model is significantly better than it at +1 h (E09).
3. Hourly validity rules decide which circuits can be modelled; the v1.1 row-count rule hid SE and SW (E05).
4. Weather did not help in this window (E11).
5. NW Plugs & Sockets and SE Lighting dominate the error (E11).

## 5. What the repository does not record
- Run times and hardware of the individual tuning runs (except the estimates in `README_v1.3.md`: GBM 5–10 min, Chronos 1–2 h, hybrid about 10 min, blend < 1 min, all CPU).
- Seeds other than `SEED = 0`.
- Full parameter lists of the Random Forest (kept in the PDF technical report).
- The exact date of the Linear Regression run (upload dated 2 Nov 2026; the report is a Sprint 3 deliverable).

Sorting out these points with the model owners would complete the log.
