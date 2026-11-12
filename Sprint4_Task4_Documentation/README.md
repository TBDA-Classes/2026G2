# Sprint 4 — UX: Documentation and evidence

Documents, analysis scripts and CSV evidence that support the Energy Watch dashboard (`../Sprint4_UX_EnergyWatch/`). All documents are in English.

## Documents (`documents/`, read in order)
| File | Content |
|---|---|
| `01_Technical_Documentation.md` | Setup, data, model, detection rules, dashboard, limits |
| `02_Assumptions_and_Decisions.md` | Tool choice, decision register, price/CO2 assumptions, why W and I are not forecast, open points for UPM |
| `03_Experiment_Log.md` | Experiment log reconstructed from the repository |
| `04_Detection_Validation.md` | Injected-anomaly test of the detector |
| `05_Deployment_and_Handover_Plan.md` | Deployment options, data requirements, retraining, monitoring, effort, responsibilities |
| `06_Backlog_Coverage.md` | Status of every backlog item PB-01 to PB-58 with evidence |
| `07_Deliverables_and_Reproducibility.md` | Delivery package index, folder layout, rebuild steps, verification |

## Other folders
- `analysis/` — CSV evidence (standby baseline, occupancy, accuracy metrics, band coverage, injection test)
- `scripts/` — Python scripts that produce the analysis CSV files (run by `../Sprint4_UX_EnergyWatch/source/run_all.py`)

To regenerate the CSV files: `python Sprint4_UX_EnergyWatch/source/run_all.py` from the repository root.
