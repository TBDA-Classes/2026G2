# Sprint 4 — Task 2: Outdoor temperature

## Purpose

Test whether outdoor temperature helps the selected model, **Blend v1.3**, forecast hourly energy consumption. The result
is either an improved model or a justified decision to exclude temperature.

## What was done

1. **Data:** hourly outdoor temperature for CeDInt from Open-Meteo, including the forecast made 48 h in advance. The data
   were quality-checked and compared with the Madrid Casa de Campo station.
2. **Experiment:** the two GBM parts of Blend v1.3 (GBM and ChronosGBM) were retrained twice with their frozen v1.3
   parameters:
   - **E0:** original inputs (= Blend v1.3);
   - **E1:** original inputs + 2 temperature inputs.

   Chronos and the Blend weights were not changed. This follows decision D12: weather only enters the GBM parts,
   because Chronos-Bolt cannot use external inputs.
3. **Evaluation:** validation week only (22–28 Sep 2025), on the same hours, by horizon, zone, load type and circuit. The
   test week was not used.

## Result in one line

Temperature does **not** improve Blend v1.3. It is worse at +1h and +6h and makes no clear difference day-ahead, so
**Blend v1.3 stays unchanged**. See `REPORT.md`.

## Files and reading order

| File | Content |
|---|---|
| `REPORT.md` | Report: data, method, results, limitations, decision |
| `data/temperature_source.md` | Source, choice, columns and quality checks |
| `data/temperature_cedint_hourly_2025.csv` | Clean hourly temperature, UTC |
| `outputs/temperature_qa.csv` | All quality and reproduction checks |
| `outputs/experiment_table.csv` | E0 vs E1 for each model part, team selection metric |
| `outputs/comparison_by_{horizon,zone,load_type,circuit}.csv` | Blend E0 vs E1, MAE and RMSE in Wh |
| `outputs/fig_*.png` | Temperature by period, MAE change by circuit, NW HVAC before/after |
| `outputs/validation_predictions_E0_E1.csv` | Every validation forecast of E0 and E1 |
| `task2_temperature.py` | The only script; it produces all of the above |

## How to run

Place this folder in the root of the group repository, next to `TBDA_v1.3_ChronosGBM_29-10/`. Then:

```
pip install -r requirements.txt
python task2_temperature.py
```

If the folder is elsewhere, pass the repository path: `python task2_temperature.py --repo "path/to/2026G2-main"`.
The script uses the saved temperature file, so the result does not depend on the provider's current data. Run time is
about one minute. It uses the team's code (`task8_model.py`, `hybrid_model.py`, `selection.py`) without modifying it.
