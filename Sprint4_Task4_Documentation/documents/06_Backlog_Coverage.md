# Backlog Coverage and Traceability — Product Backlog (Refined, 8 Oct 2026), validated Dash

**Version:** 23 Nov 2026 · **Source:** `TBDA_Group2_CeDInt_Refined_October_8.pdf` · **Product assessed:** the validated main dashboard, the **Dash app** (`Sprint4_Task3_UX_Dash/`), with its user guide `dash_guide.pdf` (22 pages, 22 Nov 2026).

The earlier Energy Watch prototype was assessed in `06a_Backlog_Coverage_EnergyWatch_prototype.md` (archive). Its counts do not apply to the Dash.

**Status legend:** **Covered** = delivered and evidenced · **Partly** = delivered with a stated gap · **Team** = belongs to another part of the project, evidence is in the repository · **Pending** = still to do before 30 Nov 2026

Evidence paths are relative to the repository root. `DOC/` is `Sprint4_Task4_Documentation/`, `DASH/` is `Sprint4_Task3_UX_Dash/`, `FE/` is `Final_Evidence/`. "Guide §" refers to `dash_guide.pdf`.

---

## Operational context and energy scope

| PB | Requirement (short) | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-01 | Defined historical-data analysis environment | Covered | Guide §1–2; `DOC/documents/01_Technical_Documentation.md` §1 |
| PB-02 | Decision-support, no automatic control | Covered | Guide §1 ("good to know"); `DASH/README.md`; model frozen, never retrained in the app |
| PB-03 | User roles defined | Covered | Guide §1 (three users and their best pages); `DASH/README.md` §1; `DOC/documents/05` §8 |
| PB-04 | Deployment and handover context | Covered | `DOC/documents/05_Deployment_and_Handover_Plan.md` |
| PB-05 | Explicit exclusions | Covered | `DOC/documents/05` §2; Known limitations page (energy only, no power or current forecast) |
| PB-06 | Load categories and circuit mapping documented | Partly | Consumption-type filter on every page; `DOC/documents/01` §4.5. **Gap:** formal validation of the circuit-to-load mapping by the data owner. |
| PB-07 | Lighting by zone and time | Covered | Filters (zone, consumption type) on Overview, Anomalies, Energy & costs, Forecast replay |
| PB-08 | Emergency lighting distinguishable | Covered | Separate consumption type |
| PB-09 | Plug/socket loads by circuit | Covered | Consumption-type filter; Energy & costs (base load by circuit) |
| PB-10 | Only monitored HVAC loads | Covered | HVAC exists for NW, NE, SE only; none inferred for SW |
| PB-11 | Hand dryers and other validated loads | Covered | NW and SW hand dryers kept separate |
| PB-12 | Included/excluded categories visible | Partly | `DOC/documents/01` §4.5; Known limitations. **Gap:** validation of the data dictionary mapping (see PB-06). |

## Data foundation and context

| PB | Requirement | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-13 | Consistent analytical dataset, traceable | Team | Hourly dataset v1.2 with META and checksums (`TBDA_v1.3_ChronosGBM_29-10/derived/`, `PROTOCOL_NOTE_v1.2.md`); `FE/documents/12_Data_Cleaning_Justification.md` |
| PB-14 | Data dictionary (variables, units, zones, circuits) | Partly | `Storey1_data_dictionary_missing_anomalies_EN.xlsx` (Er and Ea meanings corrected 17 Nov). **Gap:** units of `W` and `I` are "assumed"; Er = active and Ea = apparent energy not yet confirmed by the sponsor. |
| PB-15 | Time representation, 2020–23 vs 2025 | Team | `DECISIONS_v1.2.md`; `FE/documents/08_Scope_Decision_2025_Only.md`, `16_Temporal_Scope_Justification.md`; only 2025 minute data are modelled |
| PB-16 | Europe/Madrid, daylight saving | Partly | UTC storage, Madrid display (Guide: all times in Madrid time). No DST change in the window, so the DST case is not exercised by the data. |
| PB-17 | Missing, corrected, flagged observations | Covered | Anomalies → **Data quality** tab: 647 circuit-hours excluded with reasons, never counted as zero or as anomalies (Guide §4.3) |
| PB-18 | Data-readiness summary | Covered | Data quality tab (valid hours per circuit); Known limitations; `FE/documents/12` |
| PB-19 | Night, weekend, holiday consumption | Covered | Energy & costs → weekly rhythm (weekday × hour); share of each anomaly at night or weekend; off-peak tariff period includes nights, weekends and holidays |
| PB-20 | Standby/baseline | Covered | Energy & costs → base load vs average use (10th percentile), "what if the base load were lower" |
| PB-21 | Weather and calendar effects | Team | Calendar features; temperature tested in `Sprint4_Task2_Temperature/` and **not adopted**: worse at +1 h and +6 h, −0.0003 at day-ahead (decision D12) |
| PB-22 | Structural breaks, training window | Partly | Protocol note, regime decision and `FE/documents/08`, `16`. **Gap:** no dedicated structural-break test; winter and annual behaviour not covered. |

## Forecasting

| PB | Requirement | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-23 | Variables documented, no leakage | Team | `README_parameters.md` §3a; assertions in `task8_model.py`; Dash → The model |
| PB-24 | Forecast per supported zone | Team | Blend v1.3 for all 16 circuits; Live forecast and Forecast replay by zone |
| PB-25 | Normal consumption by load type / circuit | Covered | Forecast replay and Live forecast (zone, horizon, consumption type) |
| PB-26 | At least two baselines | Team | Three baselines (B1 last week, B2 weekday × hour median, B3 persistence), `Task6_rev0_03-11/RESULTS.md` |
| PB-27 | Candidate models compared on unseen periods | Team | Task 6: nine models scored on the same 1,911 circuit-hours (six models and three baselines; eleven candidate models over four versions), bootstrap CIs |
| PB-28 | Time-series alternative such as Prophet | Team | `Sprint4_Prophet_PB28/`, `FE/documents/13_Prophet_Justification.md`: 112 configurations, validation scaled MAE 0.47 against 0.27 / 0.35 / 0.35 for Blend v1.3. Chronos-Bolt is the pretrained time-series model inside the Blend. |
| PB-29 | MAE, MAPE, CV(RMSE) on unseen periods | Covered | Dash → Performance: MAE, RMSE, scaled MAE, WAPE with 95 % CIs; CV(RMSE) and NMBE by level in `FE/documents/09_ASHRAE14_Assessment.md` |
| PB-30 | Prediction band, coverage checked | Partly | Dash 90 % band, calibrated per circuit on validation (CQR); test-week coverage 89.9 / 91.4 / 90.7 % (raw Chronos-Bolt q10–q90: 82 % for 80 % nominal). **Gap:** intervals are labelled experimental (`INTERVALS_VALIDATED = False`) until Pole 1 validates them; switch off by default. |
| PB-31 | Experiment log | Covered | `DOC/documents/03_Experiment_Log.md`; `TBDA_v1.3_ChronosGBM_29-10/results/blend_tuning_log_v1.3.csv` |
| PB-32 | Deep learning vs ML baseline | Team | Chronos-Bolt (transformer, zero-shot) compared with GBM and Blend under the same protocol |

## Anomaly detection

| PB | Requirement | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-33 | Alert with zone/circuit and period | Covered | Anomalies page (list and deviation map) |
| PB-34 | Out-of-hours alerts, baseline and occupancy rule | Partly | Each anomaly shows its share at night or weekend and the tariff period. **Gap:** detection uses the forecast interval; there is no separate occupancy-based out-of-hours rule. |
| PB-35 | Data issues shown separately | Covered | Anomalies → Data quality tab |
| PB-36 | Severity levels and thresholds documented | Covered | Critical / Moderate / Minor definitions (Guide §4.3); `DASH/documents/04_Detection_Validation_Dash.md`. Thresholds are engineering choices, not validated by the sponsor. |
| PB-37 | Excess kWh, €, CO₂ | Covered | Anomaly list and side panel, Overview, Energy & costs; € and CO₂ are estimates from assumed prices |
| PB-38 | Detection on known events, false-alarm behaviour | Partly | Real known event (NE HVAC, 3 Oct) found at all settings; injection test of 321,366 cases (+100 % spike for 6 h found 45.4 %, circuit switched off 46.1 %). **Gap:** the real false-alarm rate needs confirmed real events; alerts per day on unmodified data is a workload proxy. |
| PB-39 | Manageable number of alerts, trade-off documented | Covered | Default setting 4.79 anomalies per day on the real data (5.71 before interval calibration); trade-off table in `DASH/documents/04_Detection_Validation_Dash.md` |

## Dashboard

| PB | Requirement | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-40 | Overview with kWh, €, CO₂, waste, alerts | Covered | Overview (forecast health, key figures, anomalies) |
| PB-41 | Filters by zone, load, period, consistent | Covered | Zone and consumption-type filters; Settings panel applies to every page |
| PB-42 | Actual, forecast, band, alert markers on one chart | Covered | Forecast replay and Live forecast |
| PB-43 | Storey 1 with four selectable zones | Covered | Energy & costs → "Where the energy goes": block map of the floor, click a zone to filter the page. Note: a block map, not the architectural plan (`proyectoedificio-planta-1.svg`). |
| PB-44 | Sortable, filterable alert list | Covered | Anomaly list (sort, filter, pages, CSV download) |
| PB-45 | Alert detail with context and plain reason | Covered | Side panel: story in words, kWh and € by tariff period, day before and after, where to start |
| PB-46 | Recurring waste heatmap | Covered | Energy & costs → weekly rhythm (weekday × hour, average use or extra in spikes); Anomalies → deviation map |
| PB-47 | Monthly € and CO₂ and leading sources | Partly | Projected monthly bill and CO₂ and "where the energy goes". **Gap:** the monthly values are projected from the period shown, not from a measured month. |
| PB-48 | Consistent normal / warning / high states | Covered | One colour legend and Critical / Moderate / Minor vocabulary (Guide §3.1) |
| PB-49 | Usable without code or datasets | Covered | Launchers `Start_dashboard.bat` and `.command`; guide |
| PB-50 | Mock-ups with recorded feedback | Partly | Mock-up (`Mockup - UX - Streamlite.py`) and mid-term feedback; record in `DOC/documents/02` §8. **Gap:** feedback of the 30 Nov session. |
| PB-51 | Task-based usability test | Partly | Done by the team and used to improve the Dash iteratively. **Gap:** there is no written report in the repository (audit check L1-17). |
| PB-52 | Historical demonstration mode | Covered | Forecast replay with hour-by-hour playback |
| PB-53 | Export alerts and savings | Covered | CSV download on the anomaly list and on the Performance tables (Guide §4.3, §4.6) |

## Handover

| PB | Requirement | Status | Dash page / evidence / remaining gap |
|---|---|---|---|
| PB-54 | Technical documentation | Covered | `DASH/README.md`; `DOC/documents/01` (written around Energy Watch, see its status note); model READMEs; `FE/documents/` |
| PB-55 | User guide with screenshots | Covered | `dash_guide.pdf` (22 pages, 22 Nov 2026) for the validated Dash. `dashboard_user_guide.pdf` describes the earlier Streamlit prototype. |
| PB-56 | Deployment and handover plan | Covered | `DOC/documents/05_Deployment_and_Handover_Plan.md` |
| PB-57 | Reproducible deliverables, code, data dictionary | Covered | `DOC/documents/07`; `Sprint4_Audit_Reproducibility/` (64 of 72 automatic checks passed on 18 Nov, open items in `results/audit_summary.md`) |
| PB-58 | Final presentation and demonstration | Pending | 30 Nov 2026; the Dash is the demonstration, Energy Watch `index.html` is the offline backup |

## Summary
Of 58 items: **37 covered**, **11 partly covered** with a stated gap (PB-06, PB-12, PB-14, PB-16, PB-22, PB-30, PB-34, PB-38, PB-47, PB-50, PB-51), **9 belong to other parts of the team** with evidence in the repository (PB-13, PB-15, PB-21, PB-23, PB-24, PB-26, PB-27, PB-28, PB-32) and **1 pending** (PB-58). Most remaining gaps are confirmations that only UPM or the sponsor can give (circuit mapping, units of W and I, tariff, real events, interval validation).
