# Sprint 4 — UX: Energy Watch (CeDInt Storey 1)

Interactive dashboard for the energy waste and anomaly detection product: expected vs actual consumption, alerts, recurring waste patterns, estimated savings (EUR and CO2), historical replay and reliability.

**Status:** mock-up and documentation complete for the 30 Nov 2026 presentation. Impact figures are **estimates** (assumed price 0.18 EUR/kWh, CO2 0.27 kg/kWh, editable in Settings).

## Open it
Double-click **`index.html`**. Any modern browser, works offline, nothing to install.

## Rebuild it (optional)
From a clone of this repository:
```
pip install -r Sprint4_UX_EnergyWatch/requirements.txt
python Sprint4_UX_EnergyWatch/source/run_all.py
```
About 13 seconds, no GPU, no internet. Verified from a clean clone: identical output.

## Documentation (`docs/`, read in order)
| File | Content |
|---|---|
| `01_Technical_Documentation.md` | Setup, data, model, detection rules, dashboard, limits |
| `02_Assumptions_and_Decisions.md` | Tool choice, decision register, price/CO2 assumptions, why W and I are not forecast, open points for UPM |
| `03_Experiment_Log.md` | Experiment log reconstructed from the repository |
| `04_Detection_Validation.md` | Injected-anomaly test of the detector |
| `05_Deployment_and_Handover_Plan.md` | Deployment options, data requirements, retraining, monitoring, effort, responsibilities |
| `06_Backlog_Coverage.md` | Status of every backlog item PB-01 to PB-58 with evidence |
| `07_Deliverables_and_Reproducibility.md` | Delivery package index, rebuild steps, verification |

## Folders
- `source/` — Python scripts, interface template and `data.json` (generated)
- `analysis/` — CSV evidence produced by the scripts

`index.html` and `data.json` are generated files: edit `source/template.html` or `source/build_data.py`, then rebuild.
