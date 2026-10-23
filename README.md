# 2026G2
Documentation: https://tbda-classes.github.io/2026G2/
## Project Overview

# CeDInt Storey 1 — Energy Forecasting & Waste Detection

**Tools for Big Data Analytics · Group 2 · ETSII-UPM · 2026**

Short-term forecasting of electrical energy consumption in the CeDInt building
(Storey 1, UPM), as the basis for detecting unusual consumption and energy waste.

| | |
|---|---|
| **Current sprint** | Sprint 3 — 19 October to 1 November 2026 |
| **Forecasting target** | `energy_Wh` — active energy consumed per interval |
| **Horizons** | +1 hour, +6 hours, day-ahead (24 h) |
| **Primary metric** | MAE (RMSE secondary) |
| **Final presentation** | 30 November 2026 |

---

## 1. The problem

The building's energy meters record **cumulative** counters (`Ea`, `Er`), instantaneous
power (`W`) and current (`I`), across four zones (NE, NW, SE, SW) and several device
categories (HVAC, Lighting, Plugs & Sockets, RACK, Hand Dryer, Emergency Lighting).

Raw counters cannot be forecast directly. The cleaning stage derives `energy_Wh`, the
active energy consumed **within each interval** (`Er[N] − Er[N−1]`), which is the
quantity every model in this repository predicts.

---

## 2. Status

**Sprint 1** — Data cleaning and EDA · complete
**Sprint 2** — Timestamps, merge, freeze, modelling spec, baselines, first ML model · complete
**Sprint 3** — Two new models, fair comparison, uncertainty, final report · in progress

### Results so far

Scaled MAE = MAE ÷ each circuit's training mean, averaged over the 8 eligible
circuits. Lower is better. Best per row in **bold**.

**Validation week** (22–28 Sep 2025) — used for model selection

| Horizon | B1 last week | B2 weekday×hour | B3 persistence | Gradient boosting | Linear |
|---|---|---|---|---|---|
| +1 h | 0.578 | 0.427 | 0.290 | **0.246** | 0.272 |
| +6 h | 0.578 | 0.429 | 0.460 | 0.355 | **0.350** |
| day-ahead | 0.578 | 0.427 | 0.367 | 0.384 | **0.348** |

**Test week** (29 Sep – 5 Oct 2025) — run once, after model settings were frozen

| Horizon | B1 | B2 | B3 | Gradient boosting | Linear |
|---|---|---|---|---|---|
| +1 h | 1.266 | 1.166 | **0.930** | 1.032 | 2.080 |
| +6 h | 1.267 | 1.167 | 1.887 | **1.175** | 1.276 |
| day-ahead | 1.267 | 1.166 | **1.162** | 1.173 | 1.260 |

**Reading these results honestly:**

- At **+1 h** the gradient-boosting model clearly beats both Task 7 baselines.
- At **+6 h and day-ahead** it does not yet beat the weekday×hour median (B2).
  With only ~35 days of training, each weekday appears about five times, so the
  model mostly learns "tomorrow resembles today at this circuit's level".
- The linear model is competitive on validation but **fails badly at +1 h on the
  test week** (2.080). NE|HVAC ran at ~690 Wh/h on 3 October against a normal
  ~3 Wh/h; because the linear model's inputs include 24 h and 168 h means, it
  extrapolated that jump for a day. Tree models do not extrapolate this way.
- Two events dominate the test scores. Any claim about which model is "best"
  must state which week, which horizon, and which hours were included.

> **Known inconsistency, open in Sprint 3 Task 3.** The Task 8 and Task 1 packages
> both report a "without 2 events" figure but define it differently — Task 8 removes
> the affected *hours* across 8 circuits, Task 1 removes the two affected *circuits*
> and averages over 6. The resulting numbers are not comparable and must be
> recomputed on one agreed set of hours before any model is declared best.

---

## 3. Repository map

Everything lives on `main`. See [Working conventions](#6-working-conventions).

### Raw data

| File | Contents |
|---|---|
| `S1-B2 Data 2019.csv` … `S1-B2 Data 2025-26.csv` | Source meter exports. Years 2019, 2020, 2022, 2023, 2024, 2025–26 (no 2021 file) |
| `Storey1_data_dictionary_missing_anomalies_EN.xlsx` | Data dictionary, missing values and known anomalies |
| `Spatial Mapping - Number per area.pdf` | Measurement points per floor, zone and system |
| `proyectoedificio-planta-{1,2,3}.svg` | Building floor plans |
| `upm_calendar.xlsx`, `build_calendar.py` | UPM academic calendar: working / weekend / holiday / vacation / lockdown day types |

### Sprint 1 — Cleaning and exploration

| File | Contents |
|---|---|
| `Sensor_data_cleaning_Storey1_v4.ipynb` | Cleaning pipeline. Derives `energy_Wh`, flags faults rather than deleting them |
| `CLEAN DATA all zones.zip` | Cleaned data, one folder per zone. See [below](#the-clean-data-package) |
| `eda_analysis.py`, `EDA_Analysis.pdf` | Exploratory data analysis of the electrical quantities |
| `TBDA - Sprint 1.pdf` | Sprint 1 report |

### Sprint 2 — Preparation and first models

| Task | File | Contents |
|---|---|---|
| 1 | `Task1_data_NE_NW.zip`, `Task1_data_SE_SW (1).zip`, `Task1_documents.zip` | Madrid local timestamps added next to UTC (DST-aware), plus QA per zone |
| 2 | `Task2_Temporal_QA_compact.zip` | Temporal quality checks |
| 3–4 | `task3_task4_final_qa.zip` | Merged dataset, QA, and the **frozen dataset** `Storey1_ALL_ZONES_FROZEN_v1.0` |
| 5 | `CeDInt__Modelling_Problem_Specification.pdf` | What is predicted and why: targets, horizons, regimes |
| 6 | `task6.pdf`, `task6_split_design.py` | Train / validation / test strategy and evaluation protocol |
| 7–8 | `Task7&8_rev0_19-10.zip` | Baselines and first ML model — 38 files, 26 tests, frozen models |
| 7–8 | `TBDA_Task7_Task8_Summary.pdf` | Guide to the above package. **Read this first** |
| 7–8 | `Task8_ModelMetrics_Summary.xlsx` | Evaluation metrics for all four models |
| — | `Sprint 2 - Tasks Presentation.pdf` | Sprint 2 task plan |

### Sprint 3 — In progress

| Task | Status | File |
|---|---|---|
| 1 — Random Tree + Linear Regression | Linear done | `Task1_linear_regression (3).zip` |
| 2 — Additional model (optional) | Not started | — |
| 3 — Compare all models, investigate errors | Not started | — |
| 4 — Prediction uncertainty | Not started | — |
| 5 — Final report and Sprint 4 handover | Not started | — |

Plan: `Sprint 3 - updated Teamwork Plan.pdf`

### Project management

| File | Contents |
|---|---|
| `TBDA_Group2_CeDInt_Refined_October_8.pdf` | **Current product backlog** (Energy Waste & Anomaly Detection) |
| `CeDInt_DataPack_Product_Backlog_Feedback_October_7.pdf` | Client-view backlog with tutor feedback |
| `BackLog Draft - Refused on 5 oct.pdf` | Earlier draft, superseded |
| `Group 2.zip` | Business case, change log, risk/issue log, sprint reports, weekly Scrum reports |
| `Updates week 4.pdf` | Weekly progress update |
| `Source Evaluation.xlsx` | Assessment of data sources |
| `Task B1 - description.pdf`, `requirements.txt` | Shared Python environment setup |
| `CSV Explanation (ES).pdf` | Format notes for an external Madrid air-quality CSV (context data, Spanish) |

---

## 4. Data pipeline

```
raw CSV exports
   └─ Sprint 1 cleaning ........ energy_Wh derived, faults flagged
        └─ Task 1 timestamps ... Madrid local time added beside UTC
             └─ Task 3–4 ....... zones merged, QA, FROZEN v1.0
                  └─ Task 7 .... hourly dataset v1.1 (one row per circuit-hour)
                       └─ Tasks 7/8, Sprint 3 models
```

**Which file should I use?**

- Modelling → the **frozen dataset** `Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz`
  inside `task3_task4_final_qa.zip`. Never modify it; work on a derived copy.
- Already-hourly modelling input → `derived/Storey1_hourly_v1.1.parquet` inside
  `Task7&8_rev0_19-10.zip`.
- Understanding the cleaning → `CLEAN DATA all zones.zip` and the notebook.

### The clean data package

`CLEAN DATA all zones.zip` contains one folder per zone, each with seven files
(example for NE):

| File | Purpose |
|---|---|
| `clean_Storey1_NE_CLEAN_DATA` | The deliverable — model-ready data, one row per original timestamp |
| `audit_NE` | Every cell the script changed, value before and after |
| `correction_log_NE` | How many cells each rule changed, per sensor |
| `rules_NE` | What each rule detects, why, what was done, which alternatives were rejected |
| `counter_events_NE` | Dates where an energy counter reset or jumped |
| `sensor_quality_NE` | Which sensors to trust as a modelling target, and why |
| `run_config_NE` | Thresholds and run ID, so the run can be reproduced |

The cleaning **flags** suspect data rather than deleting it, so that modellers can
exclude or down-weight it as a deliberate, documented decision.

---

## 5. Modelling setup

**Evaluation split** (from Task 6, 2025 regime — all dates UTC):

| Set | Period | Use |
|---|---|---|
| Training | 19 Aug – 21 Sep 2025 | Fit models, compute training statistics |
| Validation | 22 – 28 Sep 2025 | Choose models and settings |
| Test | 29 Sep – 5 Oct 2025 | Final evaluation, run once |

**Rules**

1. Never modify the frozen dataset.
2. Same evaluation periods, targets and horizons for every model.
3. Validation selects; test is run once and never used for tuning.
4. Missing or unreliable energy is never replaced with zero.
5. The 2020–2023 and 2025 periods are treated as separate regimes.

**Eligible circuits** — 8 of 16 qualify (all NE and NW). A circuit needs ≥ 90 %
valid hours in validation and test. SE and SW are excluded: beyond missing hours,
their energy and power readings contradict each other.

**Baselines**

- **B1** — same hour last week (value from 168 h earlier)
- **B2** — median for that weekday and hour, from training data only
- **B3** — persistence: the last valid hour before the forecast is made

---

## 6. Known data limitations

Open questions for the data owner, carried into Sprint 3:

- **SE / SW circuits** — energy and power readings disagree (e.g. SE|Lighting up
  to 2,097 Wh recorded at 0.5 W). Currently excluded from modelling.
- **NW|Emergency Lighting, 5–6 Oct 2025** — 18 hours with energy 10,000–45,000×
  the measured power. Kept in the official results and flagged.
- **Outages** — after an outage a single reading carries the whole gap (e.g.
  10,229 Wh covering 1,006 minutes on 17 Sep). Such hours are marked invalid.
- **Short training window** — only ~35 days of 2025 data. The 2020–2023 history
  (~25,000 hours per circuit) is the largest untapped source for Sprint 4.
- **Context variables** — no weather or academic-calendar inputs are used yet.

---

## 7. Reproducing the models

```bash
pip install -r requirements.txt
```

Then, from the unpacked `Task7&8_rev0_19-10.zip` with the frozen dataset placed
in `data/`:

```bash
python -m pytest -q tests/        # 26 tests
python run_task7.py --data data/Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz --out derived
python run_task7_baselines.py     # baselines B1, B2
python run_task8_tune.py          # train, select on validation, freeze
python run_task8_test.py          # run frozen models once on the test week
python run_task8_analysis.py      # error analysis
```

The linear model (`Task1_linear_regression (3).zip`) imports from `task8_model.py`,
so place `task1_linear.py` in the same folder before running it.

---

## 8. Working conventions

- **All work goes to `main`.** The `Data-cleaning-process` branch was merged in
  [#46](../../pull/46) and is no longer used — it remains only so that previously
  shared links keep working.
- Use folders inside `main` for organisation, not branches.
- Write a real commit message describing what changed.
- Every task produces a file, table, graph or written decision.
- Do not claim a model is better unless the comparison supports it.
