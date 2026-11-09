# Decisions for dataset v1.2 and the ChronosGBM model (Phase 0)

**Date:** 28 Oct 2026, written **before** any v1.2 dataset, model or score was produced.
**Trigger:** teacher feedback (all zones and circuits must be forecast; training data may be chosen if the
choice is logical, explained and documented; all model parameters listed in the README).

Values marked *proposal* are the defaults the code uses. If the team changes one, change it here and in
`config.py` **before** re-running, and say so in the commit message.

| ID | Decision | Value in code | Reason |
|---|---|---|---|
| D1 | Hour validity | `THRESHOLD = 1` (at least one reading, i.e. the row count is no longer a rule). `ENERGY_MAX_GAP = 15`, `ENERGY_TAIL_MAX = 5` unchanged. | `energy_Wh` after a gap covers the gap, so a sparse hour has a complete sum. The 15-min cap limits how much energy can move across an hour boundary. SE/SW were excluded by the row count, not by missing energy. |
| D2 | Inconsistent hours | An hour is invalid if `energy_Wh > CONSISTENCY_RATIO × W_mean + CONSISTENCY_TOL_WH`, with `CONSISTENCY_RATIO = 2`, `CONSISTENCY_TOL_WH = 1`. Checked only where `W_valid` (≥ 30 min of power coverage); otherwise the hour is kept and counted as unchecked. | Same definition Task 3 used for the NW Emerg. Lighting events ("energy > 2 × power"). One-sided: energy above what the measured power can deliver. 1 Wh = the counter resolution (NE/NW counter values are whole Wh), so tiny loads are not flagged for rounding. Hourly, not per reading, because `spread` energy is redistributed between readings and is only meaningful per hour. |
| D3 | Energy = 0 while power > 0 | Counted per hour (`energy_zero_with_power`, `W_mean > 1 W`), not flagged. | A two-sided rule would also hit hand dryers, whose sampled power is not a good reference. Question for the data owner. |
| D4 | Training set | A circuit is used for **training** if it has ≥ `MIN_TRAIN_HOURS = 168` valid training hours **and** ≤ `MAX_FLAGGED_TRAIN_SHARE = 0.5` of its checked training hours flagged by D2. Every circuit with 2025 data (16) is **forecast and scored** regardless. | One rule for all 16 circuits. A circuit with most of its training hours flagged has a broken level in training (expected: SE Plugs & Sockets, whose energy/power ratio is 2.5–3.3 in training and ~1.1 from 22 Sep); keeping only its unflagged hours would be a biased sample. |
| D4b | Circuits not in training | Forecast by Chronos (nothing fitted) and by the **pooled** GBM/hybrid (circuit code unseen → treated as a missing category). Reported separately as "cold-start". A circuit with fewer than 24 valid training hours has no scale and gets Chronos forecasts only. | Per-series models cannot forecast a circuit they were not trained on. |
| D5 | Reporting (used in point 8) | Per circuit: MAE and `n_valid`. Tables: **core-8** (the 8 NE/NW circuits of Sprint 2/3, fixed list `CORE_8`) and **all-16**. `ELIGIBILITY_SHARE = 0.90` only marks low-coverage circuits (`high_coverage` column). | Teacher requires all circuits; core-8 keeps continuity. |
| D6 | Selection metric | `mean_scaled_MAE` over the **training circuits** (D4) on validation. Core-8 and MAE in Wh are logged, not used to choose. | Fixed before tuning. Cold-start circuits cannot be forecast by every candidate, so they cannot select. |
| D7 | Hybrid ("ChronosGBM") | Inputs = the 15 Task 8 features + Chronos `chr_q10`, `chr_q50`, `chr_q90`, `chr_width` (q90 − q10), all ÷ circuit scale, + `chr_ctx_h` (valid hours in the Chronos context). Chronos context per horizon = the v1.2 frozen value. Same GBM grid (8 configs) × {pooled, per_series}, same fixed parameters and seed. | Specified before its validation score is known. Chronos forecasts for training hours are real out-of-sample forecasts because Chronos is not fitted on our data. |
| D7b | Blend check | `w × GBM + (1 − w) × Chronos q50`, `w ∈ {0, 0.25, 0.5, 0.75, 1}`, chosen per horizon on validation. | Cheap bar the hybrid must clear. |
| D8 | Models for the test run | B1, B2, B3, Chronos, GBM, blend, hybrid. Leading model per horizon chosen on validation. | Not run here (point 8). |
| D9 | Protocol note | See `PROTOCOL_NOTE_v1.2.md`. | — |

## What was looked at before these decisions

To be transparent: the hourly energy/power ratios per circuit and per week, and the valid-hour shares under
the gap rule, were computed on the v1.0/v1.1 hourly data and the frozen minute data while preparing this
note (28 Oct). No model was fitted or scored on v1.2 before this file was written. The threshold values
above come from Task 3 (ratio 2) and the counter resolution (1 Wh), not from those results.

---

# Addendum — selection rule D10 and extended grid v1.3 (agreed 29 Oct 2026)

**Status: agreed by the team on 29 Oct 2026, before any v1.3 run** (`config.D10_AGREED`). Written after the v1.2
validation results (28 Oct). Scoring unchanged (D6). D10a: option B. D10b: margin 0.005 confirmed. D10c added.

| ID | Decision | Value in code | Reason |
|---|---|---|---|
| D10 | Selection rule, used (a) to choose the configuration inside every v1.3 grid and (b) to choose the final model per horizon | 1. Score = `mean_scaled_MAE` over the 15 training circuits on validation (D6), each candidate on **its own** forecasts. 2. Every candidate with score ≤ best + `D10_TIE_MARGIN = 0.005` is **tied**. 3. A tied candidate whose forecasts are identical to a simpler candidate's (max. difference < 1e-6 Wh on every row) is replaced by the simpler one. 4. Among the tied candidates the one with the lowest **mean scaled RMSE** wins (RMSE per circuit ÷ circuit training mean, mean over the 15 training circuits). 5. Equal RMSE: the simpler model. Simplicity order: B3 < B1 < B2 < Chronos < GBM < ChronosGBM < Blend. Inside one grid all configurations count as equally simple. | One validation week cannot separate models closer than about 0.005 (v1.2: blend vs GBM at +1h 0.0049, Chronos contexts within 0.003). A second, fixed criterion then decides instead of noise. RMSE penalises large misses, which matter for an energy forecast. Scaled (not Wh), so the weighting is the same as for the selection metric; in Wh NW Plugs & Sockets (563 Wh/h) would dominate. Identical forecasts → simpler model, so a blend with weight 0 is reported as what it is (Chronos). |
| D10a | **Decided: no (option B).** A baseline (B1–B3) cannot be chosen as the final model; only Chronos, GBM, ChronosGBM and Blend are candidates. | `D10_INCLUDE_BASELINES = False` | **Consequence, computed on the v1.2 validation forecasts (29 Oct):** at day-ahead B3 persistence scores 0.3708 vs Chronos 0.3661 (gap 0.0047, inside the margin) and has the lower scaled RMSE (0.736 vs 0.748). Under option A, D10 would have chosen **persistence** at day-ahead. With option B the baselines are benchmarks: they are reported next to the chosen model (D10c), and the report states plainly where a baseline is as good (`baselines_within_tie_margin` in `model_choice_v1.3.json`). |
| D10b | **Decided:** tie margin 0.005 | `D10_TIE_MARGIN = 0.005` | 0.005 ≈ the largest gap the v1.2 results show to be unstable. A larger margin means more ties decided by RMSE. |
| D10c | Baselines are **tracked** in every parameter evaluation (never used to choose) | Every v1.3 tuning log row gets `ref_B1/B2/B3_MAE` and `_RMSE` (same validation rows, same 15 circuits), `best_baseline`, `gap_to_best_baseline` (< 0 = better), `clearly_beats_best_baseline` (better by more than the tie margin) and, for GBM/hybrid/Chronos, `n_circuits_beating_B3`. Per-circuit baseline scores: `results/baseline_reference_v1.3.csv`. `model_choice_v1.3.csv` lists B1–B3 as non-candidate rows. | Allows a precise comparison: for every parameter combination one can see whether, by how much and on how many circuits it beats the baselines. B3 is close to Chronos at day-ahead (v1.2), so this must be visible, not only at the end. |
| D11 | Extended grid v1.3 (teacher: ≥ 100 combinations per model) | GBM and ChronosGBM: `learning_rate` {0.03, 0.05, 0.1, 0.2} × `max_leaf_nodes` {7, 15, 31, 63} × `min_samples_leaf` {10, 20, 50, 100} × `l2_regularization` {0, 1} = 128, pooled only. Chronos-Bolt: size {tiny, mini, small, base} × context {24 … 816 h, 13 values} × point {median, mean of the 9 quantiles} = 104. Blend: weights (GBM, ChronosGBM, Chronos) on a 0.05 grid summing to 1 = 231. All other settings as v1.2. | Pooled won every horizon for GBM and hybrid in v1.1 and v1.2; the per-series fits are dropped so that the grid spends its combinations on the tree parameters. Order of the runs is fixed: GBM and Chronos → hybrid (needs the frozen Chronos) → blend (needs all three) → final model (D10). |
| D12 | Weather data | Not in v1.3. Added afterwards only to the GBM part of the model chosen by D10, checked on validation only, before the test run. | Chronos-Bolt cannot take covariates. Adding weather to every grid would double the runs. |

**Unchanged:** dataset v1.2, splits, horizons, issue times, features, fixed GBM parameters, seed 0, training
circuits (D4), fit on training data only, test week used once at the end.
