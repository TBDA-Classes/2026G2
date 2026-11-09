# v1.2 — all 16 circuits, new data rules, ChronosGBM (points 1–7)

Unzip over the Task 7&8 folder (`Task78_rev0_19-10`) together with the Chronos rev0 files. The Chronos
weights stay outside Git (`weights/chronos-bolt-small/`, checksum checked by the scripts).

```
python -m pytest -q tests/                                    # 42 tests, toy data only
python run_task7.py --data data/Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz   # dataset v1.2 + S10 (~1 min)
python make_v12_data_report.py                                # regression check vs v1.1 + data report
python run_v12_chronos_tune.py                                # Chronos: context on validation, freeze, cache (~6 min CPU)
python run_v12_gbm_tune.py                                    # GBM: grid on validation, freeze (~5 min)
python run_v12_hybrid_tune.py                                 # ChronosGBM + blend: validation, freeze (~6 min)
python run_v12_hybrid_importance.py                           # what the hybrid uses (validation only)
```

Every tuning script refuses to overwrite an existing frozen config. **No script here builds a test row**; the
only `split` values in the v1.2 result files are `train` and `validation`. The single test run is point 8.

Rules and reasons: `DECISIONS_v1.2.md` (written before any v1.2 run) and `PROTOCOL_NOTE_v1.2.md`.
All parameters with their status: `README_parameters.md`.

## What changed

| | v1.1 | v1.2 |
|---|---|---|
| Hour validity | ≥ 30 readings and no gap > 15 min | no gap > 15 min (row count dropped) and energy ≤ 2 × mean power + 1 Wh |
| Circuits forecast | 8 (NE + NW) | **16** (all with 2025 data; SW RACK has none) |
| Circuits used to fit models | 8 | 15 (rule D4, same for all) |
| 90 % rule | decided what was modelled | only marks low-coverage circuits in reports |
| Selection metric | mean scaled validation MAE over 8 | same, over the 15 training circuits |
| Circuit lists | hard-wired in several scripts | read from `S10_eligibility_v1.2.xlsx` via `eligible_series(which=...)` |

Code changes: `config.py` (new parameters, versioned file names), `task7_pipeline.py` (S06 `energy_spread_share`,
new S06b `consistency_check`, S10 training rule), `task7_baselines.py` (`eligible_series`), `task8_model.py`
(GBM accepts a feature list; old pickles still load), `chronos_model.py` (records context hours per forecast),
`run_task7.py` (S06b, gap sensitivity instead of THRESHOLD loop), `task1_linear.py`, `run_task7_baselines.py`,
`run_task8_tune.py` (eligibility file path). New: `hybrid_model.py`, `run_v12_*.py`, `make_v12_data_report.py`,
`tests/test_v12.py`, `tests/test_hybrid.py`.

## Dataset v1.2 (`results/v1.2_data_report.xlsx`)

- **Valid hours, validation + test:** NE/NW 99.7 % → 99.0 %, SE/SW 66.7 % → 76.9 %.
- **NE/NW regression check:** 88 hours changed validity, all explained (`v1.2_nenw_validity_changes.csv`):
  11 became valid (fewer than 30 readings, no long gap) and 77 became invalid because energy > 2 × power, all in
  NW Emerg. Lighting except one NE Plugs hour. The 18 flagged **test** hours of NW Emerg. Lighting are exactly
  the 18 "energy > 2 × power" event hours of Task 3.
- **SE Plugs & Sockets is not used for training:** 86 % of its checked training hours are flagged (152 valid
  training hours left). Weekly flagged share: 81–95 % in every training week, 41 % in the validation week, 14 %
  in the test week. It is forecast and scored as a cold-start circuit (Chronos, pooled GBM, pooled hybrid).
- **Flags follow the energy source:** 9.2 % of checked hours derived mostly by `spread` are flagged, 2.6 % of
  those derived by counter or power. SW Lighting has the next-highest share (13 % in training, 50–100 % per
  week from September), below the 50 % training limit.
- **Hours with zero energy while power > 1 W** (counted, not flagged, D3): mainly NW/SW Hand Dryer and
  SW/SE Lighting.
- **Gap sensitivity** (`S10_eligibility_v1.2.xlsx`, sheet `gap_sensitivity`): 15 → 30 min adds 1–7 percentage points
  of valid validation hours for SE/SW and changes no training decision.

## Frozen models (validation only)

| Horizon | Chronos context | GBM | ChronosGBM | Blend (weight of GBM) |
|---|---|---|---|---|
| +1h | 672 h | pooled, lr 0.1, 31 leaves, min leaf 50 | pooled, lr 0.05, 31 leaves, min leaf 20 | 0.5 |
| +6h | 504 h | pooled, lr 0.05, 15 leaves, min leaf 20 | pooled, lr 0.05, 31 leaves, min leaf 50 | 0 (= Chronos) |
| day-ahead | 168 h | pooled, lr 0.1, 15 leaves, min leaf 50 | pooled, lr 0.1, 31 leaves, min leaf 20 | 0 (= Chronos) |

Selection score (mean scaled validation MAE, 15 training circuits, **each model on its own forecasts**, not the
common mask of point 8):

| Horizon | GBM | Chronos | ChronosGBM | Blend |
|---|---|---|---|---|
| +1h | 0.282 | 0.288 | 0.283 | **0.276** |
| +6h | 0.432 | **0.353** | 0.389 | 0.353 |
| day-ahead | 0.429 | **0.366** | 0.403 | 0.366 |

**Observations for point 8 (not a decision):**
- The hybrid beats the standalone GBM at every horizon but **does not beat Chronos at +6h and day-ahead.**
  Its worst circuits are the ones whose level changes in validation: NW HVAC (standby, day-ahead 0.276 vs
  Chronos 0.152) and SE Lighting. The GBM part pulls towards training-period patterns; Chronos follows the new
  level. This is the Sprint 3 finding again, now on 16 circuits.
- The hybrid does use Chronos: shuffling its Chronos inputs within each circuit worsens it on most circuits,
  most for SE Lighting, SW Plugs and NW Lighting at +1h (`hybrid_importance_v1.2.xlsx`). `chr_q50` is its most
  important input at +1h and +6h.
- The blend picks w = 0 (pure Chronos) at +6h and day-ahead and w = 0.5 at +1h.
- Chronos context lengths score within 0.003 of each other at +1h and day-ahead; the chosen values are close to
  arbitrary there (as in Sprint 3).
- Cold-start SE Plugs & Sockets: its Chronos contexts are only 20–26 % valid (most training hours flagged),
  so its Chronos forecasts rest on few hours. Report it separately in point 8.

## Checks done

- 42 tests pass (`tests/`), including: sparse-but-complete hours valid, energy > 2 × power invalidates,
  hand-dryer pattern not flagged, training rule, a Chronos cache shifted by one hour is refused, the pooled model
  forecasts an unseen circuit and the per-series model does not.
- Chronos in this environment reproduces the frozen Sprint 3 forecasts (max relative difference 1e-6).
- Full chain re-run from a clean copy: identical dataset, cache, choices and validation scores.
- Frozen source file unchanged (SHA-256 before and after).

## Still to do (point 8 and after)

- Single test run of B1–B3, Chronos, GBM, blend, ChronosGBM; common mask; core-8 and all-16 tables; leading model
  per horizon chosen on validation and committed first. Test Chronos forecasts must be added to the cache with
  the frozen contexts (`load_cache(allow_test=True)` in the test script only).
- `run_task8_test.py` and `run_chronos_test.py` still follow the v1.1 layout (8 circuits, no cache); they need
  the same v1.2 changes as the tune scripts before the test run. `config.FROZEN_CONFIG` now points to the v1.2 file.
- Linear model: code updated for the v1.2 circuit lists but not re-tuned.
- Data owner: how `spread` is computed; SE Plugs level change around 22 Sep; zero energy with power.
