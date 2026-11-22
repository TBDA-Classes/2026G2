# Evidence Map — every claim of the final presentation and the file that proves it

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Jules (main author) · Claude (co-author)

Rule used in the presentation: **a number is shown only if it has a row in this table.** Paths are relative to the repository root (`TBDA-Classes/2026G2`).

## 1. Official numbers and masks

| Topic | Official source | Mask / note |
|---|---|---|
| Forecast accuracy (MAE, RMSE, CIs, significance) | `Task6_rev0_03-11/results/task6_test_16circuits/` | **1,911 circuit-hours per horizon**, hours valid for all nine models |
| ASHRAE 14 by level | `Final_Evidence/analysis/ashrae14_by_level_test.csv` | Same 1,911 hours (script reproduces the official Blend MAE) |
| Detection (injection) | `Sprint4_Task3_UX_Dash/analysis/injection_*_dash.csv` | Dash is the validated dashboard; 321,366 cases; evaluation weeks 22 Sep–6 Oct 2025 |
| Forecast band shown in Dash | `Sprint4_Task3_UX_Dash/README.md` §4 | 90 % level, calibrated on validation, checked on test |

**Numbers to retire or relabel** (they come from another mask or an older tool):

| Old number | Where | Replace by |
|---|---|---|
| Pooled MAE 20.1 / 31.1 / 30.7 Wh, building CV(RMSE) 6.3 / 14.2 / 15.4 % (n = 2,174 and 26 h) | `Sprint4_Task4_Documentation/analysis/accuracy_metrics_MAPE_CVRMSE.csv`, mid-term deck slides on ASHRAE | Official mask: MAE 22.2 / 34.7 / 34.2 Wh; building 6.7 / 17.6 / 19.5 % (n = 12 h) |
| "82 % of values inside the interval" | mid-term deck | Say which band: raw Chronos-Bolt q10–q90 (80 % nominal) → 82 %; **Dash band at 90 % → 89.9 / 91.4 / 90.7 %** (+1 h / +6 h / day-ahead) |
| "About 43,500 spike cases, 66 / 73 / 78 alerts in 14 days" | Energy Watch test | Dash test: 321,366 cases, default setting 4.8 anomalies per day; mention Energy Watch only as the earlier tool |
| Temperature "gain 0.0007–0.0018" | claim 18 below; doc 17, alternatives table | Those are differences from retraining ChronosGBM (audit L2-27). Temperature effect on the Blend: +0.0068 / +0.0080 / −0.0003 scaled MAE (`Sprint4_Task2_Temperature/outputs/experiment_table.csv`) |

## 2. Claim → file

| # | Claim | File(s) |
|---|---|---|
| 1 | Target `energy_Wh` is the interval energy from the cumulative counter; bad readings are NaN; gaps spread by power; counter resets handled | `Sensor_data_cleaning_Storey1_v4.ipynb`; `Sprint4_Task4_Documentation/documents/01_Technical_Documentation.md`, `02_Assumptions_and_Decisions.md` |
| 2 | Er (reactive counter) matches W; Ea (apparent) differs by 1/pf | `Sprint4_Task4_Documentation/analysis/W_I_vs_energy.csv`; doc 02 (open point: sponsor confirmation of the column meaning) |
| 3 | Hourly validity rules D1–D5; 21,456 rows = 16 circuits × 1,341 h | `TBDA_v1.3_ChronosGBM_29-10/DECISIONS_v1.2.md`; `derived/Storey1_hourly_v1.2.parquet`, `_META.json` |
| 4 | Split: train 19 Aug–21 Sep, validation 22–28 Sep, test 29 Sep–5 Oct 2025 | `task6_split_design.py`; `Task6_rev0_03-11/README.md` |
| 5 | 2025-only scope, spec requirements, regime differences, exploratory test | `Final_Evidence/documents/08_Scope_Decision_2025_Only.md` + `analysis/regime_comparison_by_circuit.csv`, `profile_model_history_test.csv` |
| 6 | Baselines B1 / B2 / B3 and 11 models | `Task6_rev0_03-11/results/predictions/`; `TBDA_v1.3_ChronosGBM_29-10/run_task7_baselines.py` |
| 7 | Model selection rule D10 (scaled MAE on 15 train circuits, tie 0.005, simpler wins) | `TBDA_v1.3_ChronosGBM_29-10/DECISIONS_v1.2.md`, `selection.py`, `results/blend_tuning_log_v1.3.csv` |
| 8 | Test MAE Blend 22.2 / 34.7 / 34.2 Wh; gains −49 / −21 / −22 % vs B2 | `Task6_rev0_03-11/RESULTS.md` §1–2; `results/task6_test_16circuits/metrics_with_CI.csv` |
| 9 | Significant vs weekday-median baseline at all horizons; vs persistence only at +6 h | `results/task6_test_16circuits/pairwise_differences.csv` (block bootstrap, 24 h blocks, 2,000 resamples) |
| 10 | Blend beats B2 on 16 / 14 / 14 of 16 circuits | `results/task6_test_16circuits/circuit_wins.csv`; `RESULTS.md` §2 |
| 11 | Conclusions hold without the NE HVAC event of 3 Oct | `results/task6_test_16circuits_without_events/`; `data/task6_events_test.csv` |
| 12 | SE/SW circuits (not or barely in training): persistence is lowest at +6 h and day-ahead | `RESULTS.md` §2; `metrics_per_circuit.csv` |
| 13 | Raw Chronos-Bolt q10–q90 coverage 82 % (74 % NW Hand Dryer – 90 % SW Hand Dryer) | `Sprint4_Task4_Documentation/analysis/band_coverage_chronos.csv`, `band_coverage_by_circuit_test.csv` |
| 14 | Dash band 90 %: 89.9 / 91.4 / 90.7 % inside on the test week (calibration on validation only) | `Sprint4_Task3_UX_Dash/README.md` §4; `core/anomalies.py` |
| 15 | ASHRAE 14 by level (circuit, load type, zone, building), teacher targets 7 of 11 | `Final_Evidence/documents/09_ASHRAE14_Assessment.md`; `analysis/ashrae14_by_level_test.csv` |
| 16 | NW Plugs (52.4 %) + SE Lighting (23.5 %) = 75.9 % of day-ahead validation error; SE Lighting 3-day episode | `Sprint4_Task1_Diagnosis/CONCLUSIONS.md`, `01_Performance_Analysis/REPORT.md` |
| 17 | Prophet worse than the final models (scaled MAE 0.47 vs 0.27–0.35) | `Sprint4_Prophet_PB28/README.md`, `results/` |
| 18 | Temperature (Open-Meteo) gain 0.0007–0.0018 < 0.005; worse at +1 h / +6 h; only in GBM parts (D12) | `Sprint4_Task2_Temperature/REPORT.md`; `DECISIONS_v1.2.md` (D12) |
| 19 | Detection test: +100 % spike for 6 h found 45.4 %; circuit switched off 46.1 %; about half the circuits too small or too uncertain | `Sprint4_Task3_UX_Dash/documents/04_Detection_Validation_Dash.md`; `analysis/injection_detection_by_magnitude_duration_dash.csv`, `injection_detection_by_circuit_dash.csv` |
| 20 | Real known event (NE HVAC left on, 3 Oct 11:00–14:00) found at every setting | `Sprint4_Task3_UX_Dash/analysis/injection_known_event_check_dash.csv` |
| 21 | Alerts on unmodified data: 4.8 anomalies per day (default) | `analysis/injection_quiet_data_alerts_dash.csv`; Dash README §4 |
| 22 | Dash vs Energy Watch like-for-like comparison | `Sprint4_Task3_UX_Dash/documents/Injection_Tests_Explained.md` |
| 23 | Backlog coverage: 36 covered, 10 partly, 11 team, 1 pending | `Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md` |
| 26 | GBM v1.3 in the Blend: test MAE of the Blend minus the Blend without GBM = +0.01 / −0.12 / −0.29 Wh (official 1,911-hour mask), all ties; validation scaled RMSE 0.001–0.003 | `Final_Evidence/scripts/gbm_contribution_check.py` → `analysis/gbm_contribution_test.csv`; `TBDA_v1.3_ChronosGBM_29-10/results/blend_tuning_log_v1.3.csv`; doc 18 |
| 27 | GBM v1.3 validation scores reproduce from the stored forecasts within 0.0013 (0.282 / 0.399 / 0.398) | `analysis/gbm_validation_recompute.csv` |
| 28 | Why GBM, ChronosGBM and Chronos-Bolt v1.3 were not chosen alone, and what each adds to the Blend | `documents/18_GBM_Justification.pdf`, `19_ChronosGBM_Justification.pdf`, `20_Chronos_Bolt_Justification.pdf`; `models/model_choice_v1.3.json` |

## 3. Claims that cannot be backed by a file (say them as limits)

| Statement | Why |
|---|---|
| "Old data would not help" | Not tested with the Blend; exploratory test says it might (doc 08) |
| False-alarm rate in real operation | Injection measures **sensitivity**; alerts per day on unmodified data is a workload proxy, not a verified false-alarm rate (PB-38) |
| Monthly ASHRAE criteria, seasonal behaviour, holidays, DST | 8 weeks of data; DST not exercised (PB-16) |
| Column meaning (Er vs Ea), units of W and I, circuit-to-load mapping | Awaiting sponsor confirmation |
| Why 6–13 Oct was left untouched | Not recorded; present it as an untouched reserve |
