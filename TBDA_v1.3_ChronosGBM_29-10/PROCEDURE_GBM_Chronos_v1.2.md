# Procedure — GBM + Chronos on all 16 circuits (dataset v1.2)

> **Note (29 Oct 2026):** this is the plan written before Phase 0. Where it differs from `DECISIONS_v1.2.md`
> (D2: hourly rule with 1 Wh instead of per reading with 0.5 Wh; D6: selection over the 15 training circuits instead of
> all 16), **DECISIONS_v1.2.md is what the code does.**

**Goal:** forecast `energy_Wh` for all 16 Storey 1 circuits at +1h, +6h and day-ahead. The final model is a
gradient-boosting model that uses the Chronos forecast and range as extra inputs ("hybrid").

**What changes compared to Sprint 2/3:**

| Before | Now |
|---|---|
| An hour is valid with ≥ 30 readings (`THRESHOLD`) | An hour is valid if no gap > 15 min (`ENERGY_MAX_GAP`, already in the code) and no inconsistent reading |
| A whole circuit is in or out (90 % rule) | Bad data are removed **per hour**; every circuit is forecast |
| 90 % rule decides which circuits are modelled | 90 % rule only decides which circuits enter the "core" table; every circuit is scored on its valid hours |
| GBM and Chronos are separate models | Plus a blend check and a hybrid (GBM with Chronos inputs) |

**Rules that do not change:** splits, horizons, issue times, MAE, fit on train only, configuration chosen on
validation and frozen, test used once at the end (see `README_parameters.md`, section 1).

**Order:** Phase 0 is decided and written down **before any model is run**. Nothing in Phases 1–5 may be
changed after looking at test results.

---

## Phase 0 — Decisions (team, written into `README_parameters.md`)

| ID | Decision | Proposal | Why it must come first |
|---|---|---|---|
| D1 | Hour validity | Drop the row count (`THRESHOLD`). Keep `ENERGY_MAX_GAP = 15` and `ENERGY_TAIL_MAX = 5`. | Changes the dataset; everything else depends on it. |
| D2 | Inconsistent readings | Flag a reading if `energy_Wh > CONSISTENCY_RATIO × W × gap_min / 60 + CONSISTENCY_TOL_WH` (proposal: ratio 2, tolerance 0.5 Wh). An hour with a flagged reading is invalid. One-sided: energy above what the measured power can deliver. | Must be fixed before we see which circuits it hits. Task 3 already proposed "> 2 × power" for NW Emerg. Lighting. |
| D3 | Energy = 0 while power > 0 (SE/SW Lighting) | Count and report per circuit; do **not** flag in v1.2. Ask the data owner. | A two-sided rule would also flag hand dryers, where sampled power is not a good reference. |
| D4 | Circuit exclusion | None by default. A circuit is dropped from **training** (it is still forecast and scored) if it has fewer than `MIN_TRAIN_HOURS` valid training hours (proposal: 168) **or** more than `MAX_FLAGGED_TRAIN_SHARE` of its training hours flagged by D2 (proposal: 0.5). Same rule for all 16. A circuit outside training can only be forecast by Chronos and by the pooled mode, and its results are reported as cold-start. | Expected to hit SE Plugs & Sockets: its energy/power ratio is 2.5–3.3 in every training week and 1.1–1.2 from 22 Sep. Keeping only its unflagged training hours would train on a biased sample of a broken level. | Answers "why do you keep NE HVAC?" with a rule, not a choice. With the gap rule alone, every circuit has 664–732 valid training hours (v1.0 data), so nobody is dropped unless the D2 flag removes a lot. |
| D5 | Reporting | Every circuit: MAE + `n_valid` on validation and test. Two summary tables: **core-8** (NE + NW, comparable with Sprint 2/3) and **all-16**. `ELIGIBILITY_SHARE` only marks circuits with < 90 % valid hours in the all-16 table. Each table has its own common mask (an hour counts only if every model has a target and a forecast); B1's one-week lag removes more SE/SW hours, so `n_valid` is always shown. | Teacher requires all circuits; core-8 keeps continuity and stays comparable with Sprint 2/3. |
| D6 | Selection metric | `mean_scaled_MAE` over **all 16** circuits. Also log core-8 and MAE in Wh, but they do not choose. | Fixed before tuning (Task 3 noted the hand dryer dominates the scaled mean). |
| D7 | Hybrid design | GBM inputs = current 15 features + Chronos q10, q50, q90 (÷ circuit scale), width (q90 − q10, ÷ scale) and `chr_ctx_h` (context hours actually available). Chronos context per horizon = the v1.2 frozen value from Phase 3. | The hybrid must be specified before its validation score is known. |
| D8 | Models that go to test | B1, B2, B3, Chronos, GBM, blend, hybrid. The leading model per horizon is chosen on validation only. | Avoids picking the winner on test. |
| D9 | Protocol note | Record that the test week was used in Sprint 2/3 and that v1.2 comes from the teacher's feedback (all circuits), not from test scores. Old results are kept. | Must be dated before any v1.2 run. |

**Output:** updated `README_parameters.md` (new rows: `CONSISTENCY_RATIO`, `CONSISTENCY_TOL_WH`,
`MIN_TRAIN_HOURS`, `MAX_FLAGGED_TRAIN_SHARE`, hybrid features; `THRESHOLD` marked removed), and `PROTOCOL_NOTE_v1.2.md` (D9).

---

## Phase 1 — Dataset v1.2 (`task7_pipeline.py`, `config.py`)

| ID | Step | Depends on | Check |
|---|---|---|---|
| P1.1 | `config.py`: `DERIVED_VERSION = "1.2"`, remove the row-count condition (or `THRESHOLD = 1`), add `CONSISTENCY_RATIO`, `CONSISTENCY_TOL_WH`, `MIN_TRAIN_HOURS`. | D1, D2, D4 | `run_task7.py` still loops over `THRESHOLD` 20–50 for the S10 sensitivity sheet: replace it with `ENERGY_MAX_GAP` 15 / 20 / 30. |
| P1.2 | S06: add per-reading flag `inconsistent` and hourly columns `energy_n_inconsistent`, `energy_inconsistent`. `energy_valid = has readings & no catch-up & no pre-outage & no inconsistent reading`. Also add `energy_spread_share` (share of the hour's readings with `energy_source = spread`). | P1.1 | `spread` is how the frozen dataset derived most SE/SW energy; the data report must show whether flags follow it. |
| P1.3 | S06: add `energy_zero_with_power` count per hour (reported only, D3). | P1.2 | — |
| P1.4 | S10: eligibility file no longer named after `THRESHOLD` (`S10_eligibility_v1.2.xlsx`); add columns `train_valid_hours`, `core` (≥ 90 % in val and test), `train_flagged_share`, `in_training` (both D4 conditions). Update `eligible_series()` to read `in_training`. | P1.2 | All 16 rows present. |
| P1.5 | Tests on toy data: (a) 12-min sampling, no gap > 15 → valid; (b) one reading at 3 × power → hour invalid; (c) hand-dryer-like spikes (energy < power) → still valid. | P1.2 | `pytest` green. |
| P1.6 | Run pipeline → `derived/Storey1_hourly_v1.2.parquet` + `_META.json`. | P1.5 | SHA-256 of source unchanged. |
| P1.7 | **Regression check:** NE/NW `energy_valid` in v1.2 vs v1.1 — list every hour that changed and why. Expected: only flagged inconsistent hours (e.g. NW Emerg. Lighting). | P1.6 | No unexplained change. |
| P1.8 | **Data report** `results/v1.2_data_report.xlsx`: per circuit and split — valid share, hours lost per reason (no data / gap / pre-outage / inconsistent), zero-with-power count, weekly energy ÷ power ratio, flagged share by `energy_source`. | P1.6 | This is the evidence for the teacher, and the input for the data-owner questions (how `spread` is computed; SE Plugs break around 22 Sep). |

---

## Phase 2 — Baselines on v1.2 (validation only)

| ID | Step | Depends on | Check |
|---|---|---|---|
| P2.1 | Run B1, B2, B3 for 16 circuits, 3 horizons, **validation**. | P1.6 | B2 medians from train only. |
| P2.2 | Per-circuit scale = training mean (`series_scale`); confirm every training circuit has one. | P1.6 | No `ValueError`. |

---

## Phase 3 — Chronos v1.2 (`chronos_model.py`, `run_chronos_tune.py`)

| ID | Step | Depends on | Check |
|---|---|---|---|
| P3.1 | Read circuits from `eligible_series()` instead of the Task 8 frozen config (currently hard-wired to the 8). | P1.4 | 16 circuits. |
| P3.2 | Validation forecasts for each `CTX_GRID` length (168, 336, 504, 672). One call per (circuit, issue time) gives leads 1–24, so +1h and +6h share calls. | P3.1 | Context hours < issue time (existing assert). |
| P3.2b | Count forecasts per circuit that are NaN (no valid hour in the context) or built on contexts with < 50 % valid hours. SE/SW have more gaps than the 8 circuits Chronos was tuned on. | P3.2 | Reported per circuit; nothing filled. |
| P3.3 | Choose context length per horizon by `mean_scaled_MAE` (D6) → `models/chronos_frozen_config_v1.2.json`. | P3.2 | Weights SHA-256 recorded. |
| P3.4 | **Forecast cache for the hybrid:** with the frozen context per horizon, forecast every **train and validation** issue time, all 16 circuits → `results/chronos_cache_v1.2.parquet` (`series_id, issue_time, lead, q10, q50, q90, ctx_h`). | P3.3 | Rows = issue times × 16 × 24. Test is **not** generated yet. |

Why Chronos forecasts on training hours are allowed: nothing in Chronos is fitted on our data, so a
forecast for a training hour is a true out-of-sample forecast. (Two models both fitted on our data would
need cross-fitting instead.)

Early training issue times have less context than late ones (data start 18 Aug). `chr_ctx_h` tells the GBM
how much context each forecast had.

---

## Phase 4 — GBM v1.2, standalone (`task8_model.py`, `run_task8_tune.py`)

| ID | Step | Depends on | Check |
|---|---|---|---|
| P4.1 | Re-run the existing 8-config grid × {pooled, per_series} on v1.2, 16 circuits. | P2.2 | Same `GBM_FIXED`, `SEED`. |
| P4.2 | Freeze → `models/task8_frozen_config_v1.2.json`. | P4.1 | Fit cutoff = first validation issue time. |

This is the reference: the hybrid only counts if it beats this on validation.

---

## Phase 5 — Combine (new: `hybrid_model.py`, `run_hybrid_tune.py`)

| ID | Step | Depends on | Check |
|---|---|---|---|
| P5.1 | **Blend check:** `w × GBM + (1 − w) × Chronos q50`, `w ∈ {0, 0.25, 0.5, 0.75, 1}`, chosen per horizon on validation. | P3.3, P4.2 | Cheap lower bar for the hybrid. |
| P5.2 | `build_features_hybrid()`: existing `build_features()` + join the cache on `(series_id, issue_time, lead)`; scale q10/q50/q90/width by circuit scale. | P3.4 | Assert cache `issue_time` = task `issue_time`; no NaN join for valid rows. |
| P5.3 | Unit test: shifting the cache by one hour must fail the join assert (leakage guard). | P5.2 | `pytest` green. |
| P5.4 | Tune the same GBM grid × {pooled, per_series} with hybrid features on validation → `models/hybrid_frozen_config_v1.2.json`. | P5.2 | Same selection metric (D6). |
| P5.5 | **Validation comparison** (no test): B1–B3, Chronos, GBM, blend, hybrid — all-16 and core-8, per circuit, per lead. Pick the leading model per horizon (D8). | P5.1, P5.4 | Written down and committed **before** Phase 6. |
| P5.6 | Feature importance (permutation, validation): does the hybrid use the Chronos inputs, and for which circuits? | P5.4 | Explains the result, chooses nothing. |

---

## Phase 6 — Test, once

| ID | Step | Depends on | Check |
|---|---|---|---|
| P6.1 | Generate Chronos test forecasts with the frozen context lengths; append to the cache. | P5.5 | Weights SHA-256 matches. |
| P6.2 | Run every frozen model from D8 once on test; common mask over all models. | P6.1 | Frozen-config SHA-256s match. |
| P6.3 | Tables: all-16, core-8, per circuit with `n_valid`, "without events" sensitivity (Task 8 definition). | P6.2 | Core-8 B1–B3 numbers compared with Sprint 2: differences explained by P1.7. |

---

## Phase 7 — Documentation and commit

| ID | Step | Output |
|---|---|---|
| P7.1 | Results README: what changed, data report summary, validation choice, test results, limitations. | `README_v1.2.md` |
| P7.2 | Teacher note (one page): why SE/SW are kept, the rules applied identically to all 16, hours lost per reason. | from `v1.2_data_report.xlsx` |
| P7.3 | Update `README_parameters.md` with the frozen v1.2 values. | — |
| P7.4 | Commit per phase (Phase 0 decisions → data → Chronos → GBM → hybrid → test), so the history shows that decisions came before results. Weights stay out of Git (`.gitignore`). | Git |

---

## Optional — waste flag (teacher: "predict **and prevent** waste")

Flag an hour when the actual energy is above the Chronos (or hybrid) upper forecast by a margin. The
q90 alone flags ~10 % of normal hours (Sprint 3), so the threshold is chosen on validation, then frozen and
applied to test. This turns the forecast into an alert per circuit and is the step that links the model to
waste prevention.

## Open points

- The teacher may ask for the 0-energy-with-power hours (D3); we only report them in v1.2.
- Chronos model size is still Small only; adding sizes is a validation-only check.
- Still one validation week and one test week; rolling evaluation remains the main improvement.
