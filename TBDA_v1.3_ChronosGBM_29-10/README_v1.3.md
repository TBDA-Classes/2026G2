# v1.3 — extended parameter grid (≥ 100 combinations per model) and selection rule D10

Unzip over the v1.2 folder (`TBDA_v1.2_ChronosGBM_rev0_28-10`). Nothing of v1.2 is changed or overwritten:
v1.3 adds new files and a block at the end of `config.py`; every v1.3 output carries `_v1.3` in its name.

## Run order

```
# 0. D10 agreed 29 Oct (option B, margin 0.005, baselines tracked) -> already in config.py; commit first
python -m pytest -q tests/                      # 24 tests, toy data only
python run_v13_gbm_tune.py                      # GBM, 128 x 3 horizons            (~5–10 min CPU)
python run_v13_chronos_tune.py                  # Chronos, 104 x 3 + hybrid cache  (~1–2 h CPU, size "base" dominates)
python run_v13_hybrid_tune.py                   # ChronosGBM, 128 x 3              (~10 min)
python run_v13_blend_tune.py                    # Blend, 231 x 3, then final model per horizon (D10)  (< 1 min)
```

Code checks without the real run (write only to `results/smoke/`, no frozen file in `models/`):
`python run_v13_gbm_tune.py --smoke`, `python run_v13_chronos_tune.py --sizes small`,
`python run_v13_hybrid_tune.py --smoke`, `python run_v13_blend_tune.py --smoke`.

## Chronos weights

`weights/chronos-bolt-small/` exists from Sprint 3. Download the other three sizes once (outside Git):

```
pip install -U "huggingface_hub[cli]"
huggingface-cli download amazon/chronos-bolt-tiny --local-dir weights/chronos-bolt-tiny
huggingface-cli download amazon/chronos-bolt-mini --local-dir weights/chronos-bolt-mini
huggingface-cli download amazon/chronos-bolt-base --local-dir weights/chronos-bolt-base
```

The SHA-256 of every size is written into `models/chronos_frozen_config_v1.3.json`.

## Outputs

| File | Content |
|---|---|
| `models/{task8,chronos,hybrid,blend}_frozen_config_v1.3.json` | chosen configuration per horizon, its score, scaled RMSE, number of tied configurations |
| `results/{task8,chronos,hybrid,blend}_tuning_log_v1.3.csv` | every combination with `mean_scaled_MAE`, `mean_scaled_RMSE`, all-16, core-8, per circuit, `d10_tied`, `d10_chosen` |
| `results/*_validation_predictions_v1.3.parquet` | validation forecasts of the chosen configurations (+ B1–B3 in the task8 file) |
| `results/chronos_cache_v1.3.parquet` | frozen Chronos forecasts, train + validation issue times (hybrid inputs) |
| `models/model_choice_v1.3.json`, `results/model_choice_v1.3.csv` | **final model per horizon** (D10 across models) — commit before point 8 |

## Before the test run (point 8)

1. Commit `models/model_choice_v1.3.json` and all v1.3 frozen configs (one commit, before any test forecast).
2. Optional D12: weather inputs for the GBM part of the chosen model, validation only.
3. Adapt `run_task8_test.py` / `run_chronos_test.py` to v1.3 (frozen configs v1.3, Chronos size per horizon,
   test issue times added to the cache with `load_cache(allow_test=True)`), then run once.

## Baselines in the tuning logs (D10c)

Every row of every v1.3 tuning log carries the B1–B3 scores on the same validation rows (`ref_*`), the gap to the
best baseline (`gap_to_best_baseline`, negative = better) and `clearly_beats_best_baseline` (better by more than
0.005). `results/baseline_reference_v1.3.csv` has the baselines per circuit; `model_choice_v1.3.json` lists any
baseline within the tie margin of the chosen model (`baselines_within_tie_margin`) — state those in the report.
