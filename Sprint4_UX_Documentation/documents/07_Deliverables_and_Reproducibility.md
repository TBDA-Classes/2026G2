# Deliverables Index and Reproducibility

**Backlog items:** PB-57 (reproducible analysis, code, documentation, data dictionary), backlog §8 (delivery and handover package)
**Version:** 12 Nov 2026

This page answers three questions: what is delivered, where it is, and how anyone can rebuild it from the repository.

---

## 1. Delivery package (backlog §8) and where each item is

| Backlog §8 item | Location in the repository (`TBDA-Classes/2026G2`) | Status |
|---|---|---|
| Working dashboard | `Sprint4_UX_EnergyWatch/index.html` | Delivered |
| Forecasting and anomaly-detection methodology, model-selection evidence | `TBDA_v1.3_ChronosGBM_29-10/` (model, decisions, tuning logs), `Task6_rev0_03-11/` (comparison), `Sprint4_UX_Documentation/documents/01`, `03`, `04` | Delivered |
| Clean analytical dataset or process to rebuild it | `CLEAN DATA all zones.zip`, `TBDA_v1.3_ChronosGBM_29-10/derived/Storey1_hourly_v1.2.parquet`, `run_task7.py` and the v1.2 pipeline | Delivered by the team |
| Data dictionary | `Storey1_data_dictionary_missing_anomalies_EN.xlsx` | Delivered; units of `W`, `I` to confirm |
| Technical documentation | `Sprint4_UX_Documentation/documents/01_Technical_Documentation.md` | Delivered |
| User guide with screenshots | Prepared by the team | Team |
| Deployment and handover plan | `Sprint4_UX_Documentation/documents/05_Deployment_and_Handover_Plan.md` | Delivered |
| Final presentation and demonstration | 30 Nov 2026 | Pending |
| Backup demonstration material | `Sprint4_UX_EnergyWatch/index.html` works offline on any laptop | Delivered |

## 2. Package layout (two folders)

The project is split in two folders so the application and its supporting material are not mixed.

```
Sprint4_UX_EnergyWatch/            THE APPLICATION
├── README.md                      how to open and rebuild
├── index.html                     the dashboard (generated file, do not edit by hand)
├── requirements.txt               Python packages for the rebuild
└── source/
    ├── run_all.py                 runs the seven steps below (both folders)
    ├── build_data.py              expected values, alerts, impact  → data.json
    ├── injection_test.py          injected-anomaly test (adds results to data.json)
    ├── build_html.py              data.json + template.html + Plotly → index.html
    ├── template.html              interface source (CSS and JavaScript)
    └── data.json                  everything the dashboard shows (generated)

Sprint4_UX_Documentation/          DOCUMENTS AND EVIDENCE
├── README.md                      index of the documents
├── documents/
│   ├── 01_Technical_Documentation.md
│   ├── 02_Assumptions_and_Decisions.md
│   ├── 03_Experiment_Log.md
│   ├── 04_Detection_Validation.md
│   ├── 05_Deployment_and_Handover_Plan.md
│   ├── 06_Backlog_Coverage.md
│   └── 07_Deliverables_and_Reproducibility.md   (this file)
├── analysis/                      CSV evidence produced by the scripts
└── scripts/
    ├── prep_presence.py           presence detector series
    ├── analysis_occupancy.py      occupancy rule evidence
    ├── analysis_standby_wi.py     standby baseline, W and I redundancy
    └── analysis_accuracy.py       MAPE, CV(RMSE), WAPE, band coverage
```

**Dependency between the folders.** The application reads the CSV files in `Sprint4_UX_Documentation/analysis/` when it builds `data.json`, and `injection_test.py` writes its CSV files there. `index.html` itself needs nothing: it is self-contained.

## 3. Rebuild from the repository

Requirements: Python 3.10 or later, no GPU, no internet.

```
git clone https://github.com/TBDA-Classes/2026G2.git
cd 2026G2
pip install -r Sprint4_UX_EnergyWatch/requirements.txt
python Sprint4_UX_EnergyWatch/source/run_all.py
```

| Step | Script (folder) | Reads | Writes |
|---|---|---|---|
| 1 | `prep_presence.py` (Documentation) | `CLEAN DATA all zones.zip` | `Sprint4_UX_Documentation/analysis/presence_hourly.csv` |
| 2 | `analysis_occupancy.py` (Documentation) | step 1, hourly dataset | `analysis/occupancy_profile_by_hour.csv` |
| 3 | `analysis_standby_wi.py` (Documentation) | hourly dataset | `analysis/standby_*.csv`, `analysis/W_I_vs_energy.csv` |
| 4 | `analysis_accuracy.py` (Documentation) | Task 6 forecasts, Chronos-Bolt forecasts | `analysis/accuracy_*.csv`, `analysis/band_coverage_*.csv` |
| 5 | `build_data.py` (App) | Task 6 and Chronos forecasts, hourly dataset, `Sprint4_UX_Documentation/analysis/*.csv` | `Sprint4_UX_EnergyWatch/source/data.json` |
| 6 | `injection_test.py` (App) | `source/data.json` | `Sprint4_UX_Documentation/analysis/injection_*.csv`, adds results to `data.json` |
| 7 | `build_html.py` (App) | `template.html`, `data.json`, Plotly (from the `plotly` package) | `Sprint4_UX_EnergyWatch/index.html` |

All inputs are read-only. The frozen source data and the model folders are never modified.

### What the rebuild does **not** include
The model forecasts themselves (Blend v1.3, Chronos-Bolt, GBM). They are stored as files (`Task6_rev0_03-11/results/predictions/`, `TBDA_v1.3.../results/*.parquet`) and read as they are. Regenerating them needs the frozen model files and the Chronos-Bolt weights from Hugging Face (not in Git): see `TBDA_v1.3_ChronosGBM_29-10/README_v1.3.md`. The dashboard code does not call any model.

## 4. Verification performed

| Check | Result |
|---|---|
| Fresh shallow clone of the repository, both folders copied in, `python Sprint4_UX_EnergyWatch/source/run_all.py` | Completed in about 13 seconds without errors |
| `data.json` of the clean rebuild compared with the one used for the dashboard | **Identical** |
| The eight analysis CSV files compared (rounded to 2 decimals) | **Identical** |
| Dashboard opened with all network access blocked | Charts and all eight screens work (Plotly is embedded) |
| Environment used | Python 3.13, pandas 3.0, numpy 2.5, pyarrow 26, plotly 7.1 (newer versions than the minimums in `requirements.txt`) |
| Short fingerprint of `Sprint4_UX_EnergyWatch/source/data.json` (SHA-256, first 16 characters) | `4664a3f679443c6c` |

## 5. How to change something

| To change… | Edit | Then run |
|---|---|---|
| Alert thresholds, severity rules, occupied hours, analysis window | `Sprint4_UX_EnergyWatch/source/build_data.py` (constants at the top) | `python Sprint4_UX_EnergyWatch/source/run_all.py` |
| Wording, colours, screens | `Sprint4_UX_EnergyWatch/source/template.html` | `python Sprint4_UX_EnergyWatch/source/build_html.py` |
| Price or CO₂ factor | Settings in the dashboard (no rebuild) | — |
| Default price and CO₂ values shown first | `S` object in `Sprint4_UX_EnergyWatch/source/template.html` | `python Sprint4_UX_EnergyWatch/source/build_html.py` |

Never edit `index.html` or `data.json` by hand: both are generated.

## 6. Conventions
- Time: UTC in files, Europe/Madrid in the dashboard.
- Units: Wh per hour in charts, kWh in totals, € and kg CO₂ estimated.
- Language: English for every deliverable.
- Naming: versioned folders as used by the team (`Sprint4_<Task>`), documents numbered in reading order.

## 7. Known limits of reproducibility
1. Model forecasts are inputs, not regenerated here (section 3).
2. ChronosGBM retraining on another computer can give slightly different trees even with identical inputs and seed (differences below the 0.005 tie margin, `Sprint4_Task2_Temperature/REPORT.md`).
3. Chronos-Bolt weights are external (Hugging Face); their SHA-256 is recorded in `models/chronos_frozen_config_v1.3.json`.
4. Git line-ending conversion on Windows can mark data files as "modified"; this does not change values, but those files should not be committed by accident.
