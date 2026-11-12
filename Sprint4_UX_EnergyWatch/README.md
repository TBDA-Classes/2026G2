# Sprint 4 — UX: Energy Watch (the application)

Interactive dashboard for the energy waste and anomaly detection product: expected vs actual consumption, alerts, recurring waste patterns, estimated savings (EUR and CO2), historical replay and reliability.

Impact figures are **estimates** (assumed price 0.18 EUR/kWh, CO2 0.27 kg/kWh, editable in Settings).

## Open it
Double-click **`index.html`**. Any modern browser, works offline, nothing to install.

## Rebuild it (optional)
From a clone of this repository (the folder `Sprint4_UX_Documentation/` must be next to this one):
```
pip install -r Sprint4_UX_EnergyWatch/requirements.txt
python Sprint4_UX_EnergyWatch/source/run_all.py
```
About 13 seconds, no GPU, no internet.

## Content
- `index.html` — the dashboard (generated, do not edit by hand)
- `source/template.html` — interface source (edit this for wording, colours, screens, then run `source/build_html.py`)
- `source/build_data.py` — expected values, alerts, impact (constants at the top); writes `source/data.json`
- `source/injection_test.py`, `source/build_html.py`, `source/run_all.py`

Documents, CSV evidence and analysis scripts are in **`../Sprint4_UX_Documentation/`**.
