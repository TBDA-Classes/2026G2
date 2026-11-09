# Model 1 — linear regression, all 16 circuits (rework 2 Nov 2026)

## How to run
Put `task1_linear_all16.py` in the `Task7&8_rev0_19-10` folder (next to `task8_model.py`).
```
pip install -r requirements.txt
python task1_linear_all16.py          # ~1.5 min, chooses settings on validation, test not touched
python task1_linear_all16.py --test   # runs the frozen choice ONCE on the test week
```

## Setup (same as Model 3, random forest)
- Dataset `derived/Storey1_hourly_v1.1.parquet` (sha256 `363dfdfa…66e8db8b`).
- **Trains on the 8 NE/NW circuits, predicts all 16.** Each circuit is scaled by its own training mean.
- Pooled LAD linear regression, no circuit identity, alpha 0.001 at every horizon. Full table in `PARAMETERS.md`.

## Dates (UTC, end exclusive)
| Split | From | To (last day) |
|---|---|---|
| Train | 19 Aug 2025 | 21 Sep 2025 |
| Validation | 22 Sep 2025 | 28 Sep 2025 |
| Test | 29 Sep 2025 | 5 Oct 2025 |

## Results, scaled MAE (lower is better), each model on its own valid hours
Validation (16 circuits): +1h 0.340 · +6h 0.392 · day-ahead 0.395.

Test, same hours for linear and baselines:
| Horizon | Linear all 16 | trained 8 | SE/SW 8 | B1 | B2 | B3 | MAE Wh (mean over circuits) |
|---|---|---|---|---|---|---|---|
| +1h | **0.613** | 0.907 | 0.319 | 0.894 | 0.775 | 0.630 | 24.8 |
| +6h | 0.831 | 1.289 | 0.373 | 0.893 | **0.774** | 1.203 | 38.5 |
| day-ahead | 0.838 | 1.297 | 0.379 | 0.893 | **0.774** | 0.793 | 39.0 |

The trained-8 numbers stay high because of the 3 Oct NE|HVAC run and the 5–6 Oct NW|Emerg. Lighting readings.
SE/SW coverage in the test week is only 35–89 % of hours (column `actual_Wh` is empty where the hour is invalid).

## Files
- `results/linear_test_predictions_all16.csv` — **for the comparison**: model, zone, circuit_zone, horizon_h (1/6/24), horizon_label, lead_h, issue_time_utc, target_hour (start of the hour, UTC), target_hour_madrid, actual_Wh, predicted_Wh, circuit_in_training. 8,064 rows = 16 circuits × 168 h × 3 horizons. horizon_h 24 = day-ahead issued 00:00 Madrid (leads 1–24).
- `results/task1_linear_all16_tuning_log.csv` — all 54 validation runs
- `results/task1_linear_all16_test_per_circuit.csv` — MAE, RMSE, scaled MAE, coverage per circuit on the test week (with baselines)
- Running the script again also writes the validation per-circuit table and .parquet prediction files.
- `models/task1_linear_all16_config.json` — frozen choice, dataset checksum, versions
