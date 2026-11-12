# Assumptions, Decisions and Justifications — UX / Dashboard part

**Owner:** Jules (UX / dashboard) · **Version:** 12 Nov 2026 · **Backlog items:** PB-34, PB-36, PB-37, PB-39, PB-50, PB-54

Every choice made for the dashboard is listed here with its reason, its source and how to change it. "Assumption" means a value that is not measured by the project and must be confirmed by UPM.

---

## 1. Choice of tools

### Decision
Calculations in **Python** (pandas, pyarrow). Interface in **HTML + CSS + JavaScript** without a framework, charts with **Plotly.js**. A build script injects the computed data into one self-contained `index.html`. Streamlit was used for the first four prototypes (v1–v4).

### Why not Streamlit for the final version
| Requirement | Streamlit | Chosen solution |
|---|---|---|
| Fluidity (instant filters, animated replay) | Each interaction re-runs the Python script; latency is visible and charts redraw | Everything runs in the browser; filters react immediately |
| Integrated HTML and a polished look | Possible only through workarounds and injected CSS | Full control of layout, themes (light/dark) and phone view |
| Demonstration on 30 Nov | Needs a running Python server and its dependencies | One file, works offline, can be opened on any laptop (backup demo material, backlog §8) |
| Reproducibility | Good | Good: the numbers come from Python scripts, the page is generated |
| Maintenance cost | Low | Higher: JavaScript must be maintained |

### Alternatives considered
- **Dash (Plotly):** same server requirement as Streamlit.
- **Power BI / Tableau:** strong for reporting, but the alert logic (three sensitivities, severity rule, replay) and Git-versioned delivery are not natural there. Power BI remains the right choice if the sponsor wants to embed the results in an existing reporting environment.
- **A web application with a backend (Flask/FastAPI + database):** necessary for live data, but outside the delivered scope (no real-time streaming, PB-05). Described in `05_Deployment_and_Handover_Plan.md`.

### Trade-offs accepted
The dashboard reads frozen historical data. More code (JavaScript) has to be maintained than with Streamlit. Both are consistent with the backlog scope (historical-data decision support).

---

## 2. Decision register

| ID | Decision | Value | Reason | Where to change |
|---|---|---|---|---|
| U1 | Expected consumption | Blend v1.3, day-ahead forecast issued 00:00 Madrid | It is the team's final model (Task 6). Day-ahead is the horizon that supports next-day planning. | `build_data.py`, load of `ML_Blend_v1.3_*` |
| U2 | Normal range | Chronos-Bolt v1.3 q10–q90 band, clipped so expected lies inside | PB-30 requires a documented interval with checked coverage. Observed coverage 82 % (nominal 80 %). | `build_data.py` (`F["hi"]`, `F["lo"]`) |
| U3 | Alert hour | actual > upper limit **and** excess ≥ max(floor, share × circuit mean load) | The band alone would flag tiny absolute differences on small loads; the floor and share keep only differences that matter in energy. | `SENS` in `build_data.py` |
| U4 | Three sensitivities | Strict 20 % / 40 Wh, Balanced 10 % / 20 Wh, Sensitive 5 % / 10 Wh | PB-39: a manageable number of alerts and a documented trade-off between missed events and false alarms. Balanced gives about 5 alerts per day. | Settings screen; `SENS` |
| U5 | Alert grouping | Consecutive alert hours of the same circuit = one alert | A one-hour-per-alert list would flood the user (alert fatigue). | `build_data.py` |
| U6 | Data issues kept apart | Flagged hours never raise alerts; listed with reason | PB-35: a technician should not investigate a sensor fault as waste. | Alerts → Data issues |
| U7 | Severity | High: excess ≥ 1 kWh, or ≥ 6 h, or ≥ 50 % out of hours with ≥ 0.5 kWh. Otherwise Warning. | PB-36 needs documented thresholds. Chosen to separate the few long or large events from routine ones. No sponsor-validated thresholds exist yet. | `HIGH_KWH`, `HIGH_H`, `HIGH_OOH_KWH` |
| U8 | Occupied hours | Non-holiday weekdays 07:00–20:00 Europe/Madrid | Derived from the `Pres` detector (see section 3). To be confirmed with the building manager. | `OCC_START`, `OCC_END` |
| U9 | Excess definition | Only consumption **above** the expected value on alert hours | Prevents counting normal variation as waste. It is a candidate for unnecessary use, not a confirmed loss. | `build_data.py` |
| U10 | Window | 22 Sep – 5 Oct 2025 | The only weeks for which Blend v1.3 forecasts exist (validation + test). | `START`, `END` |
| U11 | Out-of-hours use and baseline | Median hourly use outside occupied hours, per circuit | PB-20: documented baseline to separate necessary background load from potential waste. | `Sprint4_UX_Documentation/analysis/standby_baseline_by_circuit.csv` |
| U12 | Plug-and-socket baseline | Not treated as waste automatically | NW Plugs & Sockets draws about 535 Wh every hour day and night (night/day ratio 0.99). That may be a legitimate permanent load (e.g. IT equipment). It is flagged as a question for UPM. | Waste patterns → Always-on baseline |

## 3. Occupancy rule evidence
The rule uses the presence (motion) detector column `Pres` of the frozen data, which the team calls "Bsens": 1 means presence, 0 none.

| Zone | Detector | Use |
|---|---|---|
| NW | clean daily curve | used as evidence |
| SE | clean daily curve | used as evidence |
| NE | none | rule applied by analogy |
| SW | stuck near 1 | not usable |

The 07:00–20:00 weekday window captures 85–91 % of the hours with detected presence; weekends show almost no presence. Files: `Sprint4_UX_Documentation/analysis/occupancy_profile_by_hour.csv`.

## 4. Cost and CO₂ assumptions

> The Modelling Specification (§5) forbids claiming money saved, carbon avoided or confirmed waste without tariff and emissions information and validation. Every € and CO₂ figure in the tool is therefore labelled **estimated** and recomputes when the user changes the values in Settings.

| Parameter | Central | Range | Source / status |
|---|---|---|---|
| CO₂ factor | 0.27 kg/kWh | 0 – 0.28 | MITECO carbon-footprint inventory 2024, Table 9: 0.265–0.275 kg CO₂/kWh for non-renewable supply, 0 with a guarantee of origin. Published source. |
| Price | 0.18 €/kWh excl. VAT | 0.12 – 0.25 | **Assumption.** No UPM invoice is available. The upper bound is the 2026 household price including taxes (0.2509 €/kWh, euenergyprices.eu, H1 2026). Business tariffs are normally lower. |

**Action for UPM:** replace the price with the real contracted tariff and confirm whether the electricity has a renewable guarantee of origin.

Impact formulas: cost = excess kWh × price; CO₂ = excess kWh × factor. Monthly figures = the 14 days of forecasts scaled to 30 days (extrapolation). A real monthly report needs at least one full month of forecasts.

## 5. Why W (power) and I (current) are not forecast
The Modelling Specification makes `energy_Wh` the primary target and `W` secondary, with `I` exploratory and to be dropped if the added value is insufficient.

| Evidence | Result |
|---|---|
| Correlation between hourly W and energy | median ≈ 0.87 |
| Correlation between I and W | median ≈ 0.92 |
| Units | listed as "assumed" in the data dictionary (W, A) and not confirmed |
| Coverage | uneven between circuits |

**Decision:** alerts are based on energy only. Power and current add little independent information, and their semantics are unconfirmed. They remain an option for a later version (demand peaks). Evidence: `Sprint4_UX_Documentation/analysis/W_I_vs_energy.csv`.

## 6. Reliability figures
- Accuracy of the final model: Task 6 (official) and `Sprint4_UX_Documentation/analysis/accuracy_metrics_MAPE_CVRMSE.csv` (dashboard recomputation; different hour mask, so values differ slightly).
- Band coverage: `Sprint4_UX_Documentation/analysis/band_coverage_chronos.csv`, `Sprint4_UX_Documentation/analysis/band_coverage_by_circuit_test.csv`.
- Detection test on injected anomalies: `04_Detection_Validation.md`.

## 7. Open points for UPM and the sponsor
1. Confirm the circuit-to-load mapping (PB-06, PB-12).
2. Provide the electricity tariff and the CO₂ treatment (guarantee of origin).
3. Confirm occupied hours and the academic calendar (holidays, closures).
4. Confirm whether the NW plug-and-socket baseline of about 535 Wh/h is an intended permanent load.
5. Provide real known events (equipment left on, faults) to measure false alarms (PB-38).
6. Validate severity thresholds (PB-36).

## 8. Sponsor feedback record (PB-50)
| Date | Feedback | Action |
|---|---|---|
| Mid-term review | Sponsor was satisfied with the mock-up. | Structure kept: Overview, Actual vs Expected, Floor/Zone, Alerts, Heatmap, Savings, Demo mode. |
| 30 Nov 2026 | Final presentation | To be recorded after the session. |
