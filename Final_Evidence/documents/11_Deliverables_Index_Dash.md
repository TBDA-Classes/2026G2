# Deliverables Index — Dash as the main dashboard

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Jules (main author) · Claude (co-author)

This index replaces the delivery table of `Sprint4_Task4_Documentation/documents/07_Deliverables_and_Reproducibility.md`, which still lists the Energy Watch `index.html` as the working dashboard. **The validated main dashboard is the Dash app (Edoardo).** Energy Watch stays in the repository as the earlier prototype and as a lightweight offline backup.

## 1. What is delivered

| Deliverable | Where | Status |
|---|---|---|
| Final model Blend v1.3 (Chronos-Bolt + ChronosGBM + GBM) and parameters | `TBDA_v1.3_ChronosGBM_29-10/` (`README_v1.3.md`, `TBDA_G2_Model_parameters_and_results_v1.3.pdf`) | frozen |
| Model comparison (9 models scored on the same hours, with CIs) | `Task6_rev0_03-11/` (`RESULTS.md`, `results/`) | final |
| **Main dashboard (Dash)** | `Sprint4_Task3_UX_Dash/` (`README.md`, `Start_dashboard.bat`, `Start_dashboard.command`) | validated; user guide `dash_guide.pdf` (22 pages, 22 Nov); usability test done and used to improve the Dash, no written report |
| Detection validation of the dashboard | `Sprint4_Task3_UX_Dash/documents/04_Detection_Validation_Dash.md`, `analysis/injection_*_dash.csv` | final |
| Diagnosis of errors | `Sprint4_Task1_Diagnosis/` | final |
| Temperature test | `Sprint4_Task2_Temperature/` | final (not used by Chronos, decision D12) |
| Prophet check | `Sprint4_Prophet_PB28/` | final |
| Backlog coverage for the Dash | `Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md` (Energy Watch version archived in `06a`) | updated 23 Nov |
| Technical documentation, assumptions | `Sprint4_Task4_Documentation/documents/01–07` | written around Energy Watch; see status notes |
| Scope decision (2025-only) | `Final_Evidence/documents/08_Scope_Decision_2025_Only.md` | new |
| ASHRAE 14 assessment by level | `Final_Evidence/documents/09_ASHRAE14_Assessment.md` | new |
| Evidence map (claim → file) | `Final_Evidence/documents/10_Evidence_Map.md` | new |
| Mid-term review deck (PDF) | `Midterm_Review/` | mid-term version |
| Energy Watch prototype (backup) | `Sprint4_UX_EnergyWatch/index.html`, `source/run_all.py` | earlier prototype |

## 2. How to run the Dash app

1. Clone `https://github.com/TBDA-Classes/2026G2` (the app reads the model and the Task 6 results next to its folder).
2. Install **Python 3.11 or newer**.
3. Double-click `Sprint4_Task3_UX_Dash/Start_dashboard.bat` (Windows) or `Start_dashboard.command` (macOS / Linux). It creates a `.venv`, installs the packages (first start: a few minutes, about 1 GB) and opens `http://127.0.0.1:8050`.
4. The pages that replay the evaluation weeks work from the files in the repository. The **live forecast** button needs `requirements-live.txt` and downloads about 250 MB of Chronos-Bolt weights the first time.

## 3. Demo plan for 30 Nov (owner: Jules)

Prepared and tested **before** the presentation, with a fallback:

| Layer | What to prepare |
|---|---|
| Primary | Dash app started once on the demo computer (so that the install and the Chronos download are done); `Sprint4_Task3_UX_Dash/cache/ML_Blend_v1.3_test_recomputed.csv` present (currently untracked in git) |
| Fallback 1 | Screenshots or a screen recording of each demo step |
| Fallback 2 | Energy Watch `index.html` (opens offline, no installation) |

Suggested demo scenarios: (1) forecast replay of the test week for a zone and a horizon; (2) the NE HVAC event of 3 Oct 11:00–14:00 flagged as anomaly at all three sensitivities (`injection_known_event_check_dash.csv`); (3) a circuit that cannot be watched (e.g. SE Lighting) to show the limits; (4) performance and limitations pages.

## 4. Consistency rules for the final presentation

- Accuracy numbers: official Task 6 mask (1,911 circuit-hours). Do not quote the older 2,174-hour mask.
- Detection numbers: Dash test (321,366 cases), not the Energy Watch one (43,500 cases).
- Interval: say which band (raw q10–q90 → 82 %; Dash 90 % level → 89.9 / 91.4 / 90.7 %).
- ASHRAE 14 is a reference; building and SE zone rest on 12 and 24 hours.
