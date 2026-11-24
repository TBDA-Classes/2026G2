# Dash dashboard — every design decision, with reason, evidence, alternative and weakness

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 24 Nov 2026
**Authors:** Edoardo (main author; built the Dash dashboard) · Claude (co-author). User guide `dash_guide.pdf` by Kristian.
**Sources:** `Sprint4_Task3_UX_Dash/` (`README.md`, `core/settings.py`, `core/anomalies.py`, `core/data_layer.py`, `engines/*.py`), `Sprint4_Task3_UX_Dash/documents/04_Detection_Validation_Dash.md`, `Injection_Tests_Explained.md`, `analysis/injection_*_dash.csv`, `dash_guide.pdf` (22 Nov), `Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md`
**Detailed decision register:** `Sprint4_Task3_UX_Dash/documents/02_Assumptions_and_Decisions_Dash.md` (17 Nov, D1–D22). This document is its evidence-pack version, updated with the checks of 23 Nov.
**Related:** `11_Deliverables_Index_Dash.md` (Dash is the main dashboard), `10_Evidence_Map.md`, `14_Evaluation_Protocol_Justification.md`, `17_Model_Justification_Blend_v1.3.pdf`, `22_Model_Comparison_Justification.md`

> **Reading note.** This document justifies choices that already exist in the Dash app. It adds no new result. Each number comes from the file named next to it. Section 3 lists the errors found when the app and the user guide were checked against each other on 23 Nov. They should be fixed before 30 Nov.

## 1. Summary

- **What it is.** A local web app built with Dash. It shows the forecasts of the frozen Blend v1.3 for the 16 circuits, compares them with the measurements, and turns the difference into **anomalies**, **costs and base load** and **trust indicators**. It has 8 pages, for 3 kinds of user.
- **The model is never retrained.** The app reads the frozen Task 6 forecasts, can recompute them identically (max. difference 5.7 × 10⁻¹⁴ Wh), and can forecast new data with the same frozen model.
- **Anomaly detection rule.** An anomaly is a run of hours outside a 90% forecast interval *and* at least 25 Wh from the forecast. Measured on the evaluation weeks:
  - **interval calibration on test:** 89.9 / 91.4 / 90.7% inside (+1 h / +6 h / day-ahead);
  - **alert load:** 4.8 anomalies a day on the real data;
  - **injection test (321,366 cases):** 45% of +100% spikes lasting 6 h found, 46% of 6-hour switch-offs found;
  - **the one known real event** (NE|HVAC, 3 Oct) is found at every setting.
- **Chosen over Energy Watch** as the main dashboard (doc 11):
  - it detects switch-offs, which Energy Watch cannot;
  - at the same number of alerts it finds spikes as well as Energy Watch;
  - it gives fewer alerts at the default setting;
  - its interval is better calibrated at 90%.
- **Main weaknesses.**
  - It runs locally (Python 3.11, about 1 GB of packages).
  - About half of the circuits are too small or too variable to be watched.
  - Costs and CO₂ rest on placeholder assumptions.
  - Intervals are still "experimental" until Pole 1 validates them.
  - Only one confirmed real event exists.

## 2. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### D1 — Dash (Python) as the main dashboard, Energy Watch as backup

- **Decision.** The validated dashboard is the Dash app in `Sprint4_Task3_UX_Dash/`. Energy Watch (`index.html`) stays as an offline backup for the demo.
- **Why.** Written in Python, the app reuses the team's own code and frozen files: `task8_model.py`, `task7_pipeline.py`, the `.joblib` models and the Chronos-Bolt configuration. So the dashboard shows exactly the model that was evaluated, and can run it.
- **Evidence.** On the same cases (`Injection_Tests_Explained.md` §4):
  - spikes at about 5 alerts a day: tie (52–55% each);
  - with fewer alerts (about 4 a day): Dash finds 12–15 points more;
  - only Dash detects switch-offs (42–55%);
  - spike alerts a day at default: 3.6 for Dash vs 5.2 for Energy Watch;
  - calibration at 90%: 3.9 points per circuit.
- **Alternative rejected.** Streamlit (`UX_V3.py`, earlier prototype): it reruns the whole script at every click, which makes synchronised filters across pages, side panels and multi-page navigation harder to build. Energy Watch alone: no drops, and it is a static page that cannot run the model.
- **Weakness.**
  - It is not a hosted website: each user needs Python 3.11+ and a first install of about 1 GB.
  - Energy Watch is still better on the four most variable circuits and on very small loads.

### D2 — Built around three users, with plain language and Madrid time

- **Decision.** Three users (building energy manager, maintenance technician, researcher), each pointed to their best pages. There are 8 pages: Overview, Live forecast, Anomalies, Energy & costs, Forecast replay, Performance, Known limitations, The model. Every figure has an ⓘ explanation, and all times are shown in Madrid local time.
- **Why.** Backlog PB-03 (user roles) and the specification ask for decision support, not a model viewer. Users think in local time, while the model works in UTC.
- **Evidence.** `README.md` §1; guide §1; `06_Backlog_Coverage.md`: 37 of 58 items covered, 11 partly, 9 belong to other parts of the project, 1 pending (the presentation).
- **Alternative rejected.** One page per model output (scores, forecasts) for experts only.
- **Weakness.** The task-based usability test was done and used to improve the app, but there is no written report (PB-51, audit check L1-17). Daylight-saving changes are not exercised by the data (PB-16).

### D3 — Frozen model, never retrained in the app

- **Decision.** By default the app reads the frozen Blend v1.3 forecasts saved in Task 6. **Run model** recomputes them from the saved models (GBM and ChronosGBM `.joblib`, Chronos-Bolt cache, frozen weights). New data only make the input history grow; the model stays the same.
- **Why.** The model was chosen by rule D10 and tested once (doc 14 E3, doc 17). Retraining inside the app would show a model that was never evaluated.
- **Evidence.** Recomputed vs stored, test and validation: 8,064 forecasts each, max. difference 5.7 × 10⁻¹⁴ Wh, about 2 s per week (`README.md` §3).
- **Alternative rejected.** A "retrain" button. It is simple to build, but it breaks the protocol and the link to the reported scores.
- **Weakness.** The model will age: NW|Plugs & Sockets already drifts upward (D13, Known limitations). Retraining will need a new evaluation, outside the app.

### D4 — Official scores come from Task 6, not recomputed

- **Decision.** The Performance page shows the Task 6 scores: same 1,911 hours for every model, 95% CIs from the 24-hour block bootstrap. The "error" and "bias" cards of Forecast replay are computed live, and the page says so.
- **Why.** There must be one official number for the presentation and the report (doc 22). The live cards answer a different question: the error on the selection the user made.
- **Weakness.** Two error figures can differ slightly. The live cards use every measured hour of the selection (guide example: zone NW, day-ahead, 990 of 1,008 hours); the official scores use the common hours of all models. Users must read the label.

### D5 — Forecast interval: Chronos-Bolt band calibrated per circuit (conformal)

- **Decision.**
  - Start from the Chronos-Bolt v1.3 10–90% band, widened so that it always contains the Blend forecast.
  - For each circuit and horizon, calibrate it on the validation week with split-conformal (CQR) at the chosen level.
  - Circuits with fewer than 30 validation hours use the horizon-wide value.
  - Levels 80, 90 (default) and 95% (`README.md` §4, `core/settings.py`).
- **Why.** The raw Chronos band is too narrow: 82% inside for a nominal 80% (doc 10). A symmetric band (forecast ± q) had the right total coverage but was uneven circuit by circuit: 69% on NW HVAC, 100% on SE Plugs. The Chronos band follows the daily shape: narrow at night, wide in use.
- **Evidence.** On the test week, never used for calibration:
  - 89.9 / 91.4 / 90.7% inside, mean width 97 / 159 / 171 Wh;
  - mean distance from 90% per circuit: 6.6 points with the symmetric band, 3.9 points with this one;
  - anomalies on real data: 5.7 → 4.8 per day (`04_Detection_Validation_Dash.md` §4).
- **Alternative rejected.** The raw Chronos band (badly calibrated). The symmetric conformal band (uneven across circuits; still the fallback). Quantile regression for every model (only Chronos gives quantiles).
- **Weakness.**
  - The validation week is in-sample for the interval.
  - It is calibrated on one week only.
  - When circuits are added up, the distances are summed, which is conservative (too wide).
  - Not yet validated by Pole 1 (D11).

### D6 — Anomaly = outside the interval *and* at least the minimum deviation

- **Decision.**
  - An hour is anomalous if the measurement is outside the interval and at least `min_dev` (default 25 Wh) from the forecast.
  - Above = **spike**, below = **drop**.
  - Consecutive hours of one circuit in the same direction form one anomaly (`core/anomalies.py`).
- **Why.**
  - The interval says "unusual for this circuit at this hour".
  - The minimum deviation stops tiny circuits (hand dryers under 1 Wh/h) from raising alerts for a few Wh.
  - Drops matter because a circuit that stops can mean a fault or an outage.
- **Evidence.** Default result on the evaluation weeks: 67 anomalies (51 spikes, 16 drops, 14 critical). Known real event: NE|HVAC, 3 Oct, critical spike of +1.63 kWh, found at 80, 90 and 95%.
- **Alternative rejected.** A fixed threshold in Wh per circuit (ignores the daily shape). A z-score on residuals (assumes symmetric, constant spread). Energy Watch's band (no drops).
- **Weakness.**
  - Detection depends on the forecast: when the forecast is wrong, normal use becomes "anomalous". Example: night spikes on NW|Plugs & Sockets, where the model under-forecasts.
  - There is no separate occupancy-based out-of-hours rule (PB-34 partly). Each anomaly only shows its share at night or weekend.

### D7 — Default setting 90% · 25 Wh

- **Decision.** Default interval level 90% and minimum deviation 25 Wh, both editable in Settings.
- **Why.** It is the best trade-off between alerts a day and faults found (`04_Detection_Validation_Dash.md` §4):

  | Setting | Anomalies a day (real data) | +100% spike, 6 h, found | Switch-off 6 h found |
  |---|---|---|---|
  | 80% · 25 Wh | 8.50 | 48.1% | 47.0% |
  | **90% · 25 Wh** | **4.79** | **45.4%** | **46.1%** |
  | 95% · 25 Wh | 3.21 | 41.6% | 39.3% |
  | 90% · 10 Wh | 6.14 | 57.0% | 56.9% |
  | 90% · 50 Wh | 4.50 | 39.9% | 35.4% |

  90% finds almost as much as 80% with 44% fewer alerts.
- **Weakness.**
  - Even large faults are found only about half of the time, because about half of the circuits cannot be watched.
  - At 25 Wh, the smallest circuits are never flagged: hand dryers, emergency lights, NE HVAC, SW Lighting.
  - SE Lighting is found in only 1.9% of the cases (its interval is too wide).
  - A per-circuit minimum would fix this, but it needs more data to avoid false alerts.

### D8 — Three levels: Critical, Moderate, Minor

- **Decision.**
  - **Critical:** at least 1 kWh from the forecast, or 6 h or longer.
  - **Moderate:** at least 0.25 kWh, or 3 h or longer.
  - **Minor:** everything else.
- **Why.** The levels combine energy (what it costs) and duration (what it suggests: something left on). They are easy to explain and stable when settings change.
- **Evidence.** 14 of 67 anomalies are critical. The known real event is critical.
- **Alternative rejected.** Levels relative to the circuit's size: fairer to small circuits, but harder to explain, and small circuits are not watched anyway (D7).
- **Weakness.** The thresholds were set by judgement, not calibrated with users. In absolute kWh, the big circuits dominate the critical list (the first six critical anomalies are all on NW|Plugs & Sockets).

### D9 — Detection validated by injected anomalies

- **Decision.**
  - Add artificial spikes (+25 to +200% of mean use) and drops (−50%, −100%) of 1, 3 and 6 h to the real data, at every valid start hour of every circuit.
  - Run the exact detector of the app on them: 5 settings, 321,366 cases in about 6 s.
  - Count alerts a day on the unmodified data as the user's workload.
- **Why.** Only one real event is confirmed, which cannot measure a detector.
- **Evidence.** `04_Detection_Validation_Dash.md`, `analysis/injection_*_dash.csv`. Timing (occupied vs out of hours) makes little difference.
- **Alternative rejected.** Validate on real events only: just one exists.
- **Weakness.** Injected faults are clean rectangles; real faults ramp up or come and go. The real false-alarm rate is unknown (PB-38 partly).

### D10 — Costs and CO₂ as editable assumptions

- **Decision.**
  - Tariff periods of the Spanish 2.0TD access tariff (peak weekdays 10–14 and 18–22 h; standard 8–10, 14–18, 22–24 h; off-peak nights, weekends, holidays).
  - Placeholder prices 0.24 / 0.17 / 0.12 €/kWh and 0.25 kg CO₂/kWh, all editable in Settings.
  - Every € and kg is labelled "estimate".
- **Why.** The backlog asks for cost and CO₂ (PB-47). UPM's real tariff is not known, so the values must be visible and changeable, not hidden in code.
- **Weakness.**
  - 2.0TD is the tariff for supplies up to 15 kW. A university building is probably on a 3.0TD or 6.1TD tariff with 6 periods.
  - The CO₂ factor depends on the definition, and the team uses two values. Energy Watch uses 0.27 kg/kWh (MITECO 2024). The average of Spanish generation in 2024 is much lower: Red Eléctrica reports 27 Mt CO₂ from about 266 TWh, about 0.10 kg/kWh (our own calculation from their figures).
  - Costs count only hours with a valid measurement (88%), so they under-estimate.
  - The monthly bill is projected from the period shown, not measured.
  - **To do:** agree one factor and one definition for both dashboards (open point in `02_Assumptions_and_Decisions_Dash.md` §4), and cite it.

### D11 — Prediction intervals hidden by default and marked "experimental"

- **Decision.** The interval switch is off by default, and every interval is labelled "experimental · pending Pole 1" (`INTERVALS_VALIDATED = False`).
- **Why.** Task 3 asks for prediction intervals "if validated by Pole 1". Showing them as validated before that would over-claim.
- **Weakness.** Anomaly detection uses the same interval even while it is "experimental", so its status should be stated wherever anomalies are shown (PB-30 partly).

### D12 — Data problems are shown, never hidden or set to zero

- **Decision.** Hours that fail the team's dataset v1.2 rules are left out of every figure and listed in **Anomalies › Data quality**, with their reason.
- **Why.** Setting them to 0 would create false drops and false savings. The team rule is that bad readings are NaN (doc 12).
- **Evidence.** 647 circuit-hours excluded:
  - 247 energy above what the power allows;
  - 198 catch-up after a gap;
  - 168 hour cut by an outage;
  - 34 other rules.

  Valid hours per circuit: NE/NW 94–100%, SE 71–81%, SW 71–77%.
- **Weakness.** SE/SW circuits have fewer valid hours. Their scores and anomalies rest on less data.

### D13 — Base load = 10th percentile of hourly use

- **Decision.** For each circuit, base load is the 10th percentile of its hourly use from 19 Aug to 13 Oct 2025. A slider estimates the yearly saving of cutting it.
- **Why.** The minimum is too sensitive to a single bad or near-zero hour. The 10th percentile is "the level it almost never goes below".
- **Evidence.** NW|Plugs & Sockets averages 663 Wh/h, and 69% of it is always on. A 20% cut on the selection saves about 1,980 kWh a year (estimate).
- **Alternative rejected.** Minimum (outliers), night mean (some circuits work at night: rack, emergency lighting).
- **Weakness.**
  - It uses 8 weeks of late summer and autumn, with no winter.
  - The yearly saving is a linear extrapolation.
  - The window includes 6–13 Oct, which the model protocol kept outside (doc 14 E2).

### D14 — Live forecast on the reserve week, and an update path for new data

- **Decision.**
  - The Live forecast page shows the data up to 13 Oct 2025, 16:00 Madrid, and forecasts ahead with the frozen Blend v1.3, issued one hour after the last measurement.
  - New exports are added in five guided steps. The app rebuilds the hourly dataset with the team's own v1.2 pipeline (`task7_pipeline.py`) into a separate folder; the frozen dataset is never touched.
- **Why.** A forecasting dashboard must show the future, not only the past. And the data will grow after the project (PB scalability).
- **Evidence.**
  - Rebuilt from `CLEAN DATA all zones.zip`, the dataset is identical to the frozen one (21,456 hourly rows).
  - The self-test (`live_engine.py --check`) reproduces the stored test forecasts: 8,064 rows, max. difference 2 × 10⁻¹³ Wh.
  - The Chronos-Bolt weights are checked against the SHA-256 recorded when the model was frozen.
- **Alternative rejected.** Show only the evaluation weeks: a replay, not a forecast.
- **Weakness.**
  - The reserve week 6–13 Oct is no longer untouched. It was not used to train, choose or score the model, but the app shows and forecasts it (doc 14 E2, doc 10).
  - Some SE/SW circuit-hours have no forecast (gaps on 7–8 Oct; the +6 h Chronos part reads only 24 h).
  - The first live run downloads about 250 MB of weights.
  - Tomorrow's day-ahead forecast is not shown.

### D15 — One-click launchers and repository-relative paths

- **Decision.** `Start_dashboard.bat` and `Start_dashboard.command` create a `.venv`, install the packages once, start the app and open the browser. The app finds the model and the Task 6 results next to its folder; `TBDA_REPO` can override this.
- **Why.** The users are not developers, and the demo must start reliably on another computer.
- **Weakness.**
  - Windows SmartScreen and macOS Gatekeeper warn on the first start (handled in the guide).
  - The first install takes minutes.
  - The demo depends on a prepared computer, so the plan has two fallbacks (doc 11 §3).

### D16 — Validated colours, always with a text label

- **Decision.** One fixed colour per zone (NE green, NW orange, SE purple, SW pink) and one meaning per colour across all pages, from a palette checked for colour-blind separation. Every colour is paired with a text label or icon.
- **Why.** Users must read a chart without its legend, and colour must never be the only cue.
- **Weakness.** Only light mode was checked.

### D17 — "Acknowledge" button on each anomaly

- **Decision.** The side panel of an anomaly has an **Acknowledge** button for anomalies that have been checked.
- **Why.** It lets a user work through the list.
- **Weakness.** The state is kept in the browser session only (`dcc.Store`, `storage_type="session"`). It is lost when the browser closes and is not shared between users. For a real deployment it should be saved to a file or database.

## 3. Errors found on 23 Nov and corrections to make

The app (`app.py`) and the user guide (`dash_guide.pdf`) were checked against the code, dataset v1.2 and Task 6.

| # | Where | Now | Correct |
|---|---|---|---|
| 1 | Guide §7 | "The model learned from about eight weeks" | Training is 19 Aug – 21 Sep, about **5 weeks**. The 8 weeks are all the data, up to 13 Oct |
| 2 | Guide §4.8 **and** `app.py` (The model page) | GBM "learns … the hour, the weekday and holidays" | The GBM inputs have no holiday feature: hour, weekday, weekend flag. No holiday falls in the data |
| 3 | Guide §4.4 **and** `app.py` (Energy & costs) | "Racks, emergency lighting and refrigeration cannot be switched off" | There is **no refrigeration circuit** among the 16. Remove "refrigeration" |
| 4 | Guide §3.1 vs §4.6; app Settings vs Detection test | "67 anomalies in **15** days (4.5 a day)" vs "4.8: 67 in **14** days" | The two counts use different day definitions (15 Madrid calendar dates vs 14 full days). Use one, or explain |
| 5 | Guide §4.2 | Indicator "error since 6 October" | The app label is "Error on the latest days" |
| 6 | Guide §1 | "The data cover 19 August …" | The first hourly row is 18 Aug, 18:00 UTC. 19 Aug is the start of training |
| 7 | Guide §4.6 | "number of cases tested (64,860)" | Check against `injection_test_cases_dash.csv.gz`: 321,366 cases over 5 settings (doc 11 consistency rule) |
| 8 | Guide §3.1, §4.4; app Settings | CO₂ 0.25 kg/kWh and 2.0TD without source | Agree one CO₂ factor with Energy Watch (0.27 kg/kWh, MITECO 2024) and cite it. Generation-average 2024 is about 0.10 kg/kWh (Red Eléctrica). State that 2.0TD is an assumption (D10) |
| 9 | Guide §7 | Detection limit not mentioned | Add: large faults are found about half of the time, and small circuits are never watched (D7) |

## 4. If we did it again

1. **Host it** (for example on a university server) instead of asking each user to install Python.
2. **Per-circuit minimum deviation**, learned on more weeks, so that small circuits can be watched too.
3. **Save acknowledgements** in a shared file or database, with the user and date.
4. **Get UPM's real tariff and an official CO₂ factor** before showing € and kg.
5. **Write the usability test down** (tasks, users, problems found, changes made) as it happens.
6. **Keep the reserve week untouched** until a second check of the frozen model is done, and only then show it live.

## 5. Likely questions

| Question | Short answer |
|---|---|
| Why Dash and not Energy Watch? | Same spike detection at the same alert load, fewer alerts at default, and it detects switch-offs. It also runs the real frozen model (D1). |
| Is the model retrained in the app? | Never. It recomputes the frozen forecasts identically, and new data only extend the history (D3). |
| How reliable is the interval? | Calibrated on validation, checked on test: 89.9 / 91.4 / 90.7% inside for 90% nominal. Still marked experimental (D5, D11). |
| How many faults does it find? | +100% for 6 h: 45%. A switch-off for 6 h: 46%. Large stable circuits 100%, tiny ones never (D7). |
| How many alerts would a manager get? | About 4.8 a day at the default setting, editable (D7). |
| Are the costs real? | No, they are estimates with placeholder prices and CO₂ factor, editable in Settings (D10). |
| Why are some circuits never flagged? | Their normal use is below the 25 Wh minimum deviation, by design, to avoid false alarms (D7). |
| What happens with new data? | Five guided steps rebuild the dataset with the team pipeline and forecast with the frozen model (D14). |

## 6. Sources outside the repository

- Red Eléctrica, *Spanish electricity system, provisional 2024 data*: https://ree.es/sites/default/files/2025-01/EN_1912_NP%20Cierre%202024_0.pdf
- Red Eléctrica, *Renewables generated 56% of Spain's electricity mix in 2024*: https://www.ree.es/en/press-office/press-release/news/press-release/2025/01/renewable-energies-generated-56-per-cent-spains-electricity-mix-2024
