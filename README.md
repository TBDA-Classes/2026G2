# TBDA Group 2 · CeDInt Storey 1 · Building energy forecasting

Hourly energy forecasting for the 16 circuits of the first floor of CeDInt (zones NE, NW, SE, SW) with the final model **Blend v1.3** (Chronos-Bolt + ChronosGBM + GBM), and the **Dash** dashboard. Final presentation: 30 Nov 2026. Moodle hand-over: 14 Dec 2026.

## Where to start

| You want to… | Go to |
|---|---|
| Run the dashboard | `Sprint4_Task3_UX_Dash/` (`README.md`, double-click `Start_dashboard.bat` or `.command`) and the user guide `dash_guide.pdf` |
| See the evidence behind every claim | `Final_Evidence/` (start with `documents/10_Evidence_Map.md` and `documents/11_Deliverables_Index_Dash.md`) |
| See the official model comparison | `Task6_rev0_03-11/` (`RESULTS.md`) |
| See the final model and its parameters | `TBDA_v1.3_ChronosGBM_29-10/` |
| Check which backlog items are covered | `Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md` |
| Re-run the independent audit | `Sprint4_Audit_Reproducibility/` |

## Repository map

| Folder or file | Content |
|---|---|
| `Final_Evidence/` | Evidence pack for the final phase: ASHRAE 14, scope and protocol justifications, cleaning, one justification per model, evidence map, deliverables index |
| `Sprint4_Task1_Diagnosis/` | Diagnosis of the forecast errors |
| `Sprint4_Task2_Temperature/` | Temperature test (excluded, decision D12) |
| `Sprint4_Task3_UX_Dash/` | **Validated main dashboard (Dash)**, detection tests |
| `Sprint4_Task4_Documentation/` | Technical documentation, assumptions, experiment log, detection validation, deployment plan, backlog coverage |
| `Sprint4_Prophet_PB28/` | Prophet check (backlog PB-28) |
| `Sprint4_UX_EnergyWatch/` | Earlier prototype, offline backup demonstration |
| `Sprint4_Audit_Reproducibility/` | Independent audit scripts and results |
| `Task6_rev0_03-11/` | Official model comparison, same hours, bootstrap CIs |
| `TBDA_v1.3_ChronosGBM_29-10/` | Frozen final model, dataset v1.2, decisions D1–D12 |
| `model1_LinearRegression_all16/`, `Model3_RandomForest.zip` | Linear regression and Random Forest model packages |
| `docs/linear_error_by_hour/` | Linear model error by hour of day |
| `Midterm_Review/` | Mid-term review deck |
| `Building_Plans/` | Floor plans (SVG) and the circuit-per-zone mapping |
| `Data_Weather/` | Madrid weather files and the source evaluation (used by the temperature test) |
| `Archive/` | Earlier material kept for traceability, see `Archive/README.md` |
| Root files | Inputs and specifications used by scripts: `CLEAN DATA all zones.zip`, `Sensor_data_cleaning_Storey1_v4.ipynb`, `Storey1_data_dictionary_missing_anomalies_EN.xlsx`, `CeDInt__Modelling_Problem_Specification.pdf`, `TBDA_Group2_CeDInt_Refined_October_8.pdf` (product backlog), `task6.pdf` and `task6_split_design.py` (evaluation protocol), `dash_guide.pdf` (user guide), `upm_calendar.xlsx` and `build_calendar.py`, `requirements.txt` |

## Conventions
- Official accuracy numbers use the Task 6 mask: 1,911 circuit-hours per horizon on the test week (29 Sep – 5 Oct 2025).
- Baselines are called B1 (last week), B2 (weekday × hour median) and B3 (persistence). `Task6_rev0_03-11/RESULTS.md` calls them A, B and C.
- The 6–13 Oct 2025 window was not used for training, selection or official scoring.
