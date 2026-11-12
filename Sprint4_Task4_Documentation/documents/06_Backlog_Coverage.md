# Backlog Coverage and Traceability — Product Backlog (Refined, 8 Oct 2026)

**Version:** 12 Nov 2026 · **Source:** `TBDA_Group2_CeDInt_Refined_October_8.pdf`
**Status legend:** **Covered** = delivered and evidenced · **Partly** = delivered with a stated gap · **Team** = belongs to another part of the project, evidence is in the repository · **Pending** = still to do before 30 Nov 2026

Evidence paths are relative to the repository root. `DOC/` stands for `Sprint4_Task4_Documentation/` (documents, CSV evidence, analysis scripts) and `APP/` for `Sprint4_UX_EnergyWatch/` (dashboard and its source).

---

## Operational context and energy scope

| PB | Requirement (short) | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-01 | Defined historical-data analysis environment | Covered | `DOC/documents/01_Technical_Documentation.md` §1 |
| PB-02 | Decision-support, no automatic control | Covered | same; Overview and rail footer state it |
| PB-03 | User roles defined | Covered | same §1; `DOC/documents/05` §8 |
| PB-04 | Deployment and handover context | Covered | `DOC/documents/05_Deployment_and_Handover_Plan.md` |
| PB-05 | Explicit exclusions | Covered | `DOC/documents/05` §2 |
| PB-06 | Load categories and circuit mapping documented | Partly | Categories documented (`DOC/documents/01` §4.5). **Gap:** formal validation of the circuit-to-load mapping by the data owner. |
| PB-07 | Lighting by zone and time | Covered | Load filter, Alerts, Waste patterns |
| PB-08 | Emergency lighting distinguishable | Covered | Separate load type "Emergency lighting" |
| PB-09 | Plug/socket loads by circuit | Covered | Load filter; Savings by circuit |
| PB-10 | Only monitored HVAC loads | Covered | HVAC exists for NW, NE, SE only; none inferred for SW |
| PB-11 | Hand dryers and other validated loads | Covered | NW and SW hand dryers kept separate |
| PB-12 | Included/excluded categories visible | Partly | Documented in `DOC/documents/01` §4.5. **Gap:** validation of the data dictionary mapping (see PB-06). |

## Data foundation and context

| PB | Requirement | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-13 | Consistent analytical dataset, traceable | Team | Hourly dataset v1.2 with META and checksums (`TBDA_v1.3_ChronosGBM_29-10/derived/`, `PROTOCOL_NOTE_v1.2.md`) |
| PB-14 | Data dictionary (variables, units, zones, circuits) | Partly | `Storey1_data_dictionary_missing_anomalies_EN.xlsx`. **Gap:** units of `W` and `I` are "assumed". |
| PB-15 | Time representation, 2020–23 vs 2025 | Team | Regime treatment in `DECISIONS_v1.2.md`, `Modelling Problem Specification`; only 2025 minute data are modelled |
| PB-16 | Europe/Madrid, daylight saving | Partly | UTC storage, Madrid display (`DOC/documents/01` §4.3). No DST change in the window, so the DST case is not exercised by the data. |
| PB-17 | Missing, corrected, flagged observations | Covered | Quality flags D1–D5; Alerts → Data issues shows each with its reason |
| PB-18 | Data-readiness summary | Covered | Reliability & data screen; `DOC/documents/01` §4.4 |
| PB-19 | Night, weekend, holiday consumption | Covered | Waste patterns (out-of-hours shading, always-on baseline); 60 % of energy out of hours |
| PB-20 | Standby/baseline | Covered | `DOC/analysis/standby_baseline_by_circuit.csv`; Waste patterns → Always-on baseline |
| PB-21 | Weather and calendar effects | Team | Calendar features; temperature tested in Sprint 4 Task 2 and not adopted |
| PB-22 | Structural breaks, training window | Partly | Protocol note and regime decision exist. **Gap:** a dedicated structural-break analysis is not found in the repository. |

## Forecasting

| PB | Requirement | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-23 | Variables documented, no leakage | Team | `README_parameters.md` §3a; assertions in `task8_model.py` |
| PB-24 | Forecast per supported zone | Team | Blend v1.3 for all 16 circuits; zone view in the dashboard |
| PB-25 | Normal consumption by load type / circuit | Covered | Actual vs expected by circuit and load |
| PB-26 | At least two baselines | Team | B1, B2, B3 (`Task6_rev0_03-11/RESULTS.md`) |
| PB-27 | Candidate models compared on unseen periods | Team | Task 6: 11 models, same hours, bootstrap CIs |
| PB-28 | Time-series alternative such as Prophet | Partly | Chronos-Bolt (pretrained time-series model) is the time-series alternative. **Prophet itself was not tested.** |
| PB-29 | MAE, MAPE, CV(RMSE) on unseen periods | Covered | MAE official in Task 6; MAPE, CV(RMSE), WAPE in `DOC/analysis/accuracy_metrics_MAPE_CVRMSE.csv` and the Reliability screen |
| PB-30 | Prediction band, coverage checked | Covered | Chronos-Bolt q10–q90; 82 % observed against 80 % nominal |
| PB-31 | Experiment log | Covered | `DOC/documents/03_Experiment_Log.md` (reconstructed from the repository) |
| PB-32 | Deep learning vs ML baseline | Team | Chronos-Bolt (transformer, zero-shot) compared with GBM and Blend under the same protocol |

## Anomaly detection

| PB | Requirement | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-33 | Alert with zone/circuit and period | Covered | Alerts screen |
| PB-34 | Out-of-hours alerts, baseline and occupancy rule | Covered | Occupied hours from presence detectors (`DOC/documents/02` §3); filter "Mostly out of hours" |
| PB-35 | Data issues shown separately | Covered | Alerts → Data issues |
| PB-36 | Severity levels and thresholds documented | Covered | `DOC/documents/02` (U7). Thresholds are engineering choices, not yet validated by the sponsor. |
| PB-37 | Excess kWh, €, CO₂ | Covered | Alerts table, detail, Overview, Savings. € and CO₂ are labelled *estimated*. |
| PB-38 | Detection on known events, false-alarm behaviour | Partly | Real known event detected; injected-anomaly test (`DOC/documents/04`). **Gap:** real false-alarm rate needs confirmed real events. |
| PB-39 | Manageable number of alerts, trade-off documented | Covered | Three sensitivities, 4.7 / 5.2 / 5.6 alerts per day; `DOC/documents/04` |

## Dashboard

| PB | Requirement | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-40 | Overview with kWh, €, CO₂, waste, alerts | Covered | Overview |
| PB-41 | Filters by zone, load, period, consistent | Covered | Global filter bar applied to every screen |
| PB-42 | Actual, forecast, band, alert markers on one chart | Covered | Actual vs expected |
| PB-43 | Storey 1 with four selectable zones | Partly | Schematic plan with NE/NW/SE/SW. **Gap:** the repository holds the building plan (`proyectoedificio-planta-1.svg`); using it would be more realistic. |
| PB-44 | Sortable, filterable alert list | Covered | Alerts (time, zone, circuit, severity, kWh, €, CO₂) |
| PB-45 | Alert detail with context and plain reason | Covered | Alert drawer: 24 h either side, reason, checks |
| PB-46 | Recurring waste heatmap | Covered | Waste patterns, day × hour, out-of-hours shaded |
| PB-47 | Monthly € and CO₂ and leading sources | Partly | Savings screen. **Gap:** monthly values are 14 days scaled to 30; a real month needs longer forecasts (data exist to 13 Oct). |
| PB-48 | Consistent normal / warning / high states | Covered | One status vocabulary across screens |
| PB-49 | Usable without code or datasets | Covered | Self-contained page |
| PB-50 | Mock-ups with recorded feedback | Partly | Mock-up and mid-term positive feedback; record in `DOC/documents/02` §8. **Pending:** feedback of the 30 Nov session. |
| PB-51 | Task-based usability test | Team | Performed by the team; report to be attached to the final package |
| PB-52 | Historical demonstration mode | Covered | Replay screen |
| PB-53 | Export alerts and savings | Partly | "Copy as CSV" on Alerts and Savings. A downloadable file is not possible inside a shared web page. |

## Handover

| PB | Requirement | Status | Evidence / remaining gap |
|---|---|---|---|
| PB-54 | Technical documentation | Covered | `DOC/documents/01` plus the model READMEs listed there |
| PB-55 | User guide with screenshots | Team | Prepared by the team; screenshots must come from the frozen final version |
| PB-56 | Deployment and handover plan | Covered | `DOC/documents/05` |
| PB-57 | Reproducible deliverables, code, data dictionary | Covered | `DOC/documents/07`; `python APP/source/run_all.py` verified from a clean clone |
| PB-58 | Final presentation and demonstration | Pending | 30 Nov 2026; the offline `index.html` is the backup demonstration |

## Summary
Of 58 items: **36 covered**, **11 partly covered** with a stated gap (PB-06, PB-12, PB-14, PB-16, PB-22, PB-28, PB-38, PB-43, PB-47, PB-50, PB-53), **10 belong to other parts of the team** with evidence in the repository (PB-13, PB-15, PB-21, PB-23, PB-24, PB-26, PB-27, PB-32, PB-51, PB-55) and **1 pending** (PB-58). Most remaining gaps are confirmations that only UPM or the sponsor can give (circuit mapping, units of W and I, tariff, occupied hours, real events).
