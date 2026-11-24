# Assumptions, Decisions and Justifications — Dash dashboard

**Owner:** Edoardo (Sprint 4 Task 3, UX) · **Version:** 17 Nov 2026 · **Backlog items:** PB-05, PB-30, PB-33–PB-49, PB-52, PB-54, PB-57

Every choice made for the Dash dashboard is listed here with **what we chose, why it is good (with evidence), its
weakness, the alternatives we considered, whether we implemented them, and what we would do if we started again**.
"Assumption" means a value that is not measured by the project and must be confirmed by UPM.
Same structure as Energy Watch's `Sprint4_Task4_Documentation/documents/02_Assumptions_and_Decisions.md`.

All numbers come from files in this repository; the source is given next to each one.

---

## 1. Decision register (summary)

| ID | Decision | Value | Main evidence | Where to change |
|---|---|---|---|---|
| D1 | Framework | Dash + Dash Bootstrap Components + Plotly | Runs the model and the live forecast in Python; multi-page; partial updates | `app.py` |
| D2 | Users and pages | 3 users, 8 pages | Task 3 brief; each page answers one user question | `app.py` (`page_*`) |
| D3 | Model shown | Blend v1.3, frozen, never retrained in the app | Rule D10 chose it at every horizon (`TBDA_v1.3_ChronosGBM_29-10/models/model_choice_v1.3.json`) | `core/settings.py` |
| D4 | Connection to the model | The app re-runs the frozen files | Recomputed = stored Task 6 forecasts, max diff 5.7e-14 Wh | `engines/model_engine.py` |
| D5 | "Live" forecast | From the newest data in the files, issued as in operation | Self-test equals Task 6 on the test week (max diff 2e-13 Wh) | `engines/live_engine.py` |
| D6 | New data | Rebuilt with the team's v1.2 pipeline | Rebuild from `CLEAN DATA all zones.zip` = frozen dataset (21,456 rows, same values) | `engines/update_data.py` |
| D7 | Where new data go | `new_data/` folder + upload box + format check | Guided 5-step section on the Live forecast page | `core/data_layer.py`, `app.py` |
| D8 | Forecast interval | Chronos-Bolt 10–90 % band calibrated per circuit (conformal) at 90 % | Test week 90.7 % inside; 3.9 points per circuit from target | `core/data_layer.py` (`apply_intervals`) |
| D9 | Interval status | "Experimental", off by default on forecast charts | Task 3: intervals only if validated by Pole 1 | `INTERVALS_VALIDATED` in `core/settings.py` |
| D10 | Reference for anomalies | Day-ahead forecast | +1 h would split events (120 anomalies, 1.2 h each, vs 67 and 1.9 h) | `core/anomalies.py` (`_frame`) |
| D11 | Anomaly rule | Outside the interval **and** ≥ minimum deviation; spikes **and** drops | Without the minimum: 336 anomalies instead of 67 | `core/anomalies.py` (`detect`) |
| D12 | Default setting | 90 % interval, 25 Wh | Injection test: 45.4 % / 46.1 % found, 4.8 anomalies/day | Settings panel; `DEFAULTS` |
| D13 | Levels | Critical ≥ 1 kWh or ≥ 6 h; Moderate ≥ 0.25 kWh or ≥ 3 h; Minor | 14 Critical anomalies hold 75.7 % of the deviation energy | `core/anomalies.py` (`_level`) |
| D14 | Costs | 2.0TD tariff periods, prices 0.24 / 0.17 / 0.12 €/kWh, CO₂ 0.25 kg/kWh | **Assumptions**, editable, every € labelled "est." | Settings panel; `DEFAULTS` |
| D15 | Base load | 10th percentile of hourly use per circuit | Stable choice (p5 1,090 / p10 1,130 / p20 1,334 Wh/h for the floor) | `core/anomalies.py` (`base_load`) |
| D16 | Detection validation | Injection test, 321,366 cases, spikes and drops | `analysis/injection_*_dash.csv` | `engines/injection_test.py` |
| D17 | Comparison with Energy Watch | Same cases, compared at the same number of alerts | `documents/Injection_Tests_Explained.md` | — |
| D18 | Data quality | Invalid hours excluded, never zero, listed with reason | Dataset v1.2 flags | `core/anomalies.py` (`_quality`) |
| D19 | Time | Madrid local time on screen, UTC inside | Users think in local time; model works in UTC | `TZ_LOCAL` |
| D20 | Readability | One colour code, legend, (i) pop-up on every chart/KPI/table | Colour palette checked for colour blindness | `core/info_texts.py`, `assets/style.css` |
| D21 | Delivery | One-click launcher for Mac and Windows | Fresh clone from GitHub opens all pages | `Start_dashboard.command` / `.bat` |
| D22 | Folder and file names | Same structure as Energy Watch + suffix `_dash` | Both tests can be read side by side | — |

---

## 2. Decisions in detail

### D1 — Framework: Dash

**Why it is good.** The dashboard must **run** the model (re-run the frozen files, compute a live forecast with
Chronos-Bolt, rebuild the data from a new export). All of this is Python, so a Python web framework keeps the model
and the interface in one place. Dash has real multi-page navigation and callbacks that update only the charts that
change (a click on the treemap refocuses the whole Energy & costs page).

**Weakness.** It needs a running Python server and about 1 GB of packages with Chronos; it cannot be opened as a
single file like Energy Watch's `index.html`.

**Alternatives considered.**

| Alternative | Implemented? | Why not chosen |
|---|---|---|
| Streamlit (`UX_V3.py`) | Yes, by the team in Sprints 3–4 | Re-runs the whole script on every click; harder multi-page layout and partial updates |
| Static HTML + Plotly.js (Energy Watch) | Yes, by Jules | Works offline, but cannot run the model or take new data: numbers are frozen when the page is built |
| Power BI / Tableau | No | No way to run the Python model; alert logic and Git versioning are not natural there |
| Flask/FastAPI + database + real-time feed | No | Out of scope (no real-time streaming, PB-05) |

**If we started again.** Same choice, but we would agree on one dashboard from the start instead of building
Streamlit, Energy Watch and Dash in parallel; the HTML would remain only as an offline backup for the demo.

### D2 — Users and pages

**Why.** Task 3 asks to define users and needs. Three users with different questions: the energy manager (how much,
what it costs, where to save), the maintenance technician (is a circuit abnormal now?), the researcher (how accurate,
what are the limits). Each page answers one question: Overview, Live forecast, Anomalies, Energy & costs, Forecast
replay, Performance, Known limitations, The model.

**Weakness.** The users are assumed, not interviewed; no task-based usability test has been run yet (PB-51).

**Alternative.** One long single page: rejected, too many charts for one screen.

**If we started again.** Run a short usability test with two real users (one technician, one energy manager) before
building the last pages.

### D3 — Model shown: Blend v1.3, frozen

**Why.** Rule D10 (scaled MAE on validation, tie margin 0.005, tie-break scaled RMSE) chose Blend v1.3 at every horizon
(`model_choice_v1.3.json`). On the test week its MAE is 22.2 / 34.7 / 34.2 Wh at +1 h / +6 h / day-ahead, 49 / 21 / 22 %
below Baseline B (`Task6_rev0_03-11/RESULTS.md`). Sprint 4 Task 2 showed that adding outdoor temperature made +1 h and
+6 h worse, so the model was not changed.

**Weakness.** Only one test week; at +1 h and day-ahead Blend is lower than persistence but tied within the
confidence interval. The night consumption of NW Plugs & Sockets doubled after training (514 → 980 → 1,043 Wh/h), so
the model underestimates it.

**Alternative.** Showing several models side by side in the app. Not implemented: the task asks for the chosen model,
and the comparison already lives in Task 6.

**If we started again.** Use a longer training period (more weeks, other seasons) and recalibrate NW Plugs at night.

### D4 — The app re-runs the frozen model

**Why.** "Connected to the model" should mean more than reading a CSV. `engines/model_engine.py` loads the two frozen
GBM files and the Chronos caches and blends them with the frozen weights; the result equals the stored Task 6 forecasts
(8,064 rows per week, max difference 5.7e-14 Wh). It proves reproducibility (PB-57).

**Weakness.** Needs scikit-learn 1.9.1 exactly (the version the files were saved with), so Python 3.11+.

**Alternative.** Only reading the Task 6 CSV files (as Energy Watch does): simpler, but not a real connection.

### D5 — "Live" forecast from the newest data

**Why.** No real-time feed exists (PB-05). "Live" therefore means: the frozen Blend v1.3 forecasts from the newest data
in the files exactly as it would in operation (+1 h, +6 h, day-ahead issued at 00:00 Madrid), using only the data
known at that moment. The week 6–13 Oct was never used to build, choose or score a model, so it is a fair check: MAE
22.6 / 36.4 / 34.4 Wh, almost the same as the test week. A self-test (`--check`) rebuilds the test week and equals
Task 6 (max difference 2e-13 Wh).

**Weakness.** It is not real time; it depends on someone exporting new data. The first run downloads the Chronos-Bolt
weights (about 250 MB).

**If we started again.** Connect directly to the building's data export (scheduled job) so the forecast refreshes
by itself.

### D6 — New data rebuilt with the team's pipeline

**Why.** Using the team's own v1.2 cleaning code (`task7_pipeline.py`) guarantees that new data follow exactly the
same rules as the data the model was built on. Rebuilt from `CLEAN DATA all zones.zip`, the hourly dataset is
identical to the frozen one (21,456 rows, same energy values). The frozen dataset is never overwritten.

**Weakness.** The export must contain the whole history, not only the new days (the model needs the past weeks).

**Alternative.** Appending only the new days: faster, but risks inconsistent cleaning at the boundary. Not implemented.

### D7 — Where new data go (`new_data/`)

**Why.** A non-technical user should not type file paths. The Live forecast page explains five steps, shows the
folder, opens it with one click, accepts drag-and-drop, checks the format (green tick / red cross with the reason)
and updates data and forecast with one button. A "Go back to the project dataset" button undoes the update.
`new_data/` is ignored by git, so personal exports are never uploaded.

**Weakness.** Large uploads through the browser are slow (the full export is about 50 MB); copying into the folder is
faster.

### D8 — Forecast interval: Chronos band calibrated per circuit

**What.** Start from Chronos-Bolt's 10–90 % band (one of the three Blend parts), widened to contain the forecast.
On the **validation week** compute, per circuit and horizon, how far measurements fell outside it and shift it by the
conformal quantile Q, so that it holds the chosen share (conformalized quantile regression, CQR).

**Why it is good.** Distribution-free coverage guarantee; the band follows the daily shape (narrow at night, wide in
the day); calibrated only on validation, so the test week is an honest check.

| Method (test week, never used to calibrate) | Implemented? | Hours inside (target) | Mean distance from target per circuit |
|---|---|---|---|
| Raw Chronos band (Energy Watch) | Yes, in Energy Watch | 83.4 % (80 %) | 4.8 points |
| Symmetric split-conformal `forecast ± q` (first Dash version) | Yes, replaced on 14 Nov | 89.6 % (90 %) | 6.6 points |
| **Calibrated Chronos band (current)** | **Yes** | **90.7 % (90 %)** | **3.9 points** |
| Quantile GBM or bootstrap of residuals | No | — | would need retraining (model is frozen) |

At 80 / 90 / 95 % the current interval holds 82.8 / 90.7 / 95.0 % of the test hours; by horizon 89.9 / 91.4 / 90.7 %.

**Weakness.** Calibrated on one validation week only; on very variable circuits it stays wide (SE Lighting, NW Plugs),
so small faults there cannot be seen.

**If we started again.** Calibrate on several weeks (rolling) and per occupancy period (day/night).

### D9 — Interval marked "experimental"

**Why.** Task 3 says to show prediction intervals only if validated by Pole 1. Until then they are labelled
"experimental" and off by default on the forecast charts; setting `INTERVALS_VALIDATED = True` switches them on.
**Open point:** Pole 1 validation.

### D10 — Anomalies are judged against the day-ahead forecast

**Why.** The +1 h forecast uses the last measurement, so after one hour it "learns" the fault and stops seeing it.
Evidence (evaluation weeks, 90 %, 25 Wh):

| Reference forecast | Anomalies | Mean length | Known event NE HVAC 3 Oct |
|---|---|---|---|
| +1 h | 120 | 1.2 h | found, but only 2 h and 1.33 kWh |
| +6 h | 71 | 2.0 h | 3 h, 1.63 kWh |
| **Day-ahead (chosen)** | **67** | **1.9 h** | **3 h, 1.63 kWh** |

Day-ahead is fixed at midnight, so the whole fault is visible as one anomaly. Energy Watch made the same choice (U1).

### D11 — Anomaly rule: interval + minimum deviation, spikes and drops

**Why.** The interval alone would flag tiny differences on tiny circuits (hand dryers use 0.8 Wh/h): with a 0 Wh
minimum there are 336 anomalies instead of 67. **Drops** (use below the interval) are kept because a circuit switched
off or failed is as important for a technician as one left on; Energy Watch detects only spikes.

**Weakness.** Circuits whose whole use is below 25 Wh (hand dryers, emergency lights, NE HVAC, SW Lighting) cannot be
watched.

**Alternative.** A threshold proportional to each circuit's mean (Energy Watch: max(floor, share × mean)). Not
implemented; a per-circuit threshold is the first improvement we would make.

### D12 — Default setting 90 % · 25 Wh

**Why.** Chosen from the injection test (`analysis/injection_quiet_data_alerts_dash.csv`,
`injection_detection_by_magnitude_duration_dash.csv`):

| Setting | Anomalies/day (real data) | Spike +100 % 6 h found | Switched off 6 h found |
|---|---|---|---|
| 80 % · 25 Wh | 8.50 | 48.1 % | 47.0 % |
| **90 % · 25 Wh** | **4.79** | **45.4 %** | **46.1 %** |
| 95 % · 25 Wh | 3.21 | 41.6 % | 39.3 % |
| 90 % · 10 Wh | 6.14 | 57.0 % | 56.9 % |
| 90 % · 50 Wh | 4.50 | 39.9 % | 35.4 % |

90 % finds almost as much as 80 % with 44 % fewer alerts (PB-39: a manageable number of alerts). The user can change
it in Settings.

### D13 — Levels Critical / Moderate / Minor

**Why.** Separates the few events that matter from routine ones: the 14 Critical anomalies (of 67) hold 75.7 % of the
deviation energy. The first two thresholds are the same as Energy Watch's High level (≥ 1 kWh or ≥ 6 h), so both tools agree on what is serious.

**Weakness.** Engineering choices, not validated by the sponsor (PB-36).

### D14 — Costs and CO₂

**Why.** Prices differ by hour in Spain (2.0TD periods: peak weekdays 10–14 and 18–22, standard 8–10, 14–18, 22–24,
off-peak nights, weekends and holidays), so a spike at 11:00 costs more than one at 03:00. Every € and CO₂ figure is
labelled "est." and recomputes when the user edits the values (Modelling Specification §5).

**Assumptions.** Prices 0.24 / 0.17 / 0.12 €/kWh and CO₂ 0.25 kg/kWh are placeholders; no UPM invoice is available.
**Inconsistency to fix:** Energy Watch uses 0.18 €/kWh flat and 0.27 kg CO₂/kWh (MITECO 2024). The team should agree on
one CO₂ factor for the final presentation.

**Action for UPM.** Give the contracted tariff and whether the supply has a renewable guarantee of origin.

### D15 — Base load = 10th percentile

**Why.** The level a circuit "never goes below", robust to a few outlier hours. Sensitivity of the floor's total base
load (19 Aug – 13 Oct 2025, 16 circuits): minimum 728, 5th percentile 1,090, **10th 1,130**, 20th 1,334, median
1,554 Wh/h, mean 1,885 Wh/h. The minimum is driven by single odd hours; above the 10th percentile normal low use
starts to count as "always on".

**Alternative.** Median of out-of-hours use (Energy Watch, U11): answers a slightly different question (night use, not
the absolute floor). Not implemented.

### D16 — Detection validation by injection

**Why.** Only one real fault is confirmed (NE HVAC, 3 Oct), so detection cannot be measured on real data. We add
artificial faults of known size and length to the real measurements (spikes +25 to +200 % of the circuit mean, drops
−50 and −100 %, 1/3/6 h, every valid start hour, 5 settings): 321,366 cases. Details in
`documents/04_Detection_Validation_Dash.md`.

**Weakness.** Faults are clean rectangles; alerts per day on real data are only a proxy for false alarms (real
anomalies are not labelled); 14 days only.

**If we started again.** Ask the building team to label a few real events, to measure false alarms directly.

### D17 — Comparison with Energy Watch at the same number of alerts

**Why.** A detector can always find more by raising more alerts, so the two tools are compared on the same 59,448
cases **at the same alert budget**. Result: equal at about 5 spike alerts a day; Dash finds 12–15 points more when
fewer alerts are wanted; only Dash detects switch-offs; Energy Watch is better on small faults and on the four most
variable circuits. Details in `documents/Injection_Tests_Explained.md`.

### D18–D20 — Data quality, time, readability

- **D18.** Hours that break a v1.2 rule (energy above what power allows, catch-up after a gap, outage) are excluded
  everywhere, never counted as zero, and listed with their reason (PB-35).
- **D19.** Madrid local time on screen (users), UTC inside (model). Day-ahead forecasts are issued at 00:00 Madrid.
- **D20.** One colour code for the whole app (legend next to Settings), zone colours checked for colour blindness and
  always written next to the colour, and an (i) pop-up on every chart, KPI and table.

### D21 — Delivery: one-click launcher

**Why.** The professor's feedback: teammates must open the app without set-up problems. `Start_dashboard.command`
(Mac) and `Start_dashboard.bat` (Windows) create the environment, install the packages once and open the browser.
A fresh copy from GitHub was checked: all required files found and all pages open.

**Weakness.** macOS and Windows warn once for files downloaded as a ZIP (unsigned scripts); a `git clone` or GitHub
Desktop avoids it. The `.bat` has not been tested on a Windows computer yet.

**Alternative.** Docker image or packaged executable: heavier, and Docker is not installed on most laptops.

### D22 — Folder and file names

Same structure as the Energy Watch documentation (`analysis/`, `documents/`, `04_Detection_Validation`, injection file
names) with the suffix `_dash`, so the two can be compared side by side and told apart.

---

## 3. Checks done (17 Nov 2026)

| Check | Result |
|---|---|
| Model choice claims vs `model_choice_v1.3.json` and Task 6 `RESULTS.md` | consistent |
| Numbers about Dash quoted in `Final_Evidence/documents/10_Evidence_Map.md` (89.9 / 91.4 / 90.7 %, 321,366 cases, 45.4 %, 46.1 %, 4.8/day, known event) | consistent with `analysis/` and README |
| Re-run of the frozen model vs Task 6 | identical |
| Rebuild of the dataset from `CLEAN DATA all zones.zip` | identical (21,456 rows) |
| Fresh clone of GitHub `main` | all required files present; all 8 pages open |
| Files committed | no data exports, caches or credentials; `.gitignore` keeps `cache/`, `data_live/` and `new_data/` contents out |

## 4. Open points

| Point | Owner | Status |
|---|---|---|
| Pole 1 validation of the forecast interval | Pole 1 | open |
| One CO₂ factor and one price for both dashboards | team | open (Dash 0.25, Energy Watch 0.27 kg/kWh) |
| UPM tariff and guarantee of origin | UPM | open |
| Task-based usability test (PB-51) and user guide with screenshots (PB-55) | Edoardo (per `Final_Evidence/documents/11_Deliverables_Index_Dash.md`) | to do |
| Test `Start_dashboard.bat` on a Windows computer | team | to do |
| Per-circuit minimum deviation, so small circuits can be watched | — | future work |

## 5. If we started over

1. One dashboard from the start (Dash), with the HTML version only as an offline backup.
2. Users interviewed and a usability test before building the last pages.
3. More weeks of data and seasons for training and for the interval calibration.
4. Thresholds per circuit and real labelled events to measure false alarms.
5. A scheduled data export so the live forecast refreshes by itself.
