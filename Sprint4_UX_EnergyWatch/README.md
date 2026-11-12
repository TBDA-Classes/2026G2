# Sprint 4 - UX: Energy Watch (mock-up)

Interactive mock-up of the CeDInt Storey 1 energy dashboard: expected vs actual consumption, alerts, waste patterns, estimated savings, replay and reliability.

## Open it
Double-click `index.html` (any modern browser, works offline).

## Contents
| Path | What |
|---|---|
| `index.html` | The mock-up (generated file, do not edit by hand) |
| `DOSSIER_JUSTIFICATIONS.md` | Tool choice, assumptions (price, CO2, occupancy rule), why W and I are not modelled, limits |
| `source/build_data.py` | Python: builds `data.json` (expected values, alerts, impact) from the Blend v1.3 predictions |
| `source/build_html.py` | Python: injects `data.json` + Plotly into `template.html` -> `index.html` |
| `source/template.html`, `source/data.json` | Interface source and its data |
| `analysis/` | CSV evidence: MAPE, CV(RMSE), band coverage, occupancy, standby baseline, W/I redundancy |

## Rebuild
```
pip install pandas pyarrow plotly
cd source
python build_data.py --model-dir ../../TBDA_v1.3_ChronosGBM_29-10 --task6-dir ../../Task6_rev0_03-11/results/predictions --out data.json
python build_html.py        # writes ../index.html next to source/ -> see note below
```
Note: `build_html.py` writes `index.html` inside `source/`; copy it one level up to replace the mock-up.

## Status
Impact figures (EUR, kg CO2) are estimates from assumed price 0.18 EUR/kWh and 0.27 kg CO2/kWh (editable in Settings). User test and user guide: to do. Sponsor feedback: to add after 30 Nov.
