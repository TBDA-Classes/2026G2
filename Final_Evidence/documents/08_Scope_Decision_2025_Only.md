# Scope Decision — why the final model is trained on 2025 only

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Jules (main author, Project Manager / Scrum Master) · Claude (co-author)
**Scripts:** `Final_Evidence/scripts/regime_comparison.py` · **Outputs:** `Final_Evidence/analysis/regime_comparison_by_circuit.csv`, `yearly_mean_by_circuit.csv`, `same_season_by_circuit.csv`, `profile_model_history_test.csv`, `profile_model_history_by_circuit.csv`

> **Reading note.** This document states the decision, the evidence for it, the evidence against it and what was *not* tested. The numbers in section 3 and 4 come from a quick exploratory harness (section 4), not from the official Task 6 comparison.

## 1. The decision

The final model (Blend v1.3) is trained, tuned and tested on the **2025 regime only** (readings from 18 Aug to 13 Oct 2025). The 2020–2023 data was cleaned (`CLEAN DATA all zones.zip`) but **not used for training, selection or testing**.

This was a **team choice**. It was made under time pressure, and it was **not validated by a combined-model experiment**. The teacher's forum reply (17 Nov) states that either option is acceptable if it is well defended, and that what counts is how well conclusions are supported by evidence and how openly limits are shown.

## 2. What the task specification requires (and does not)

From `CeDInt__Modelling_Problem_Specification.pdf` (sections on temporal regimes, data, and modelling):

- The historical (2020–2023) and recent (2025) data are **two distinct regimes**; there is **no continuous sequence** across the gap.
- Cumulative counters must **not be differenced across the gap**.
- A model that combines regimes is allowed only if it is **justified by validation evidence** and accounts for changes in sensors, operations and behaviour.

The specification **does not forbid** using the historical data, and it **does not require** 2025-only training. The 2025-only scope is therefore our decision, and the specification sets the standard of proof for the alternative (combined model).

## 3. Evidence that the two regimes differ

All values are in Wh per circuit-hour, hours with every reading valid. Source: `regime_comparison_by_circuit.csv`, `yearly_mean_by_circuit.csv`.

| Fact | Value |
|---|---|
| Gap between the regimes | last historical reading 28 Feb 2023, first 2025 reading 18 Aug 2025 → **about 900 days** |
| Valid circuit-hours | historical **405,237** vs 2025 **20,125** (about 20× more history) |
| Sampling | historical: 1 reading per hour; 2025: about 43 readings per hour (median 48) |
| Circuit missing in 2025 | SW RACK has history (2020–21) but **no 2025 data** |

**The level of the circuits is not stable, even inside the historical data** (mean Wh per hour, valid hours):

| Circuit | 2020 | 2021 | 2022 | 2023 (Jan–Feb) | 2025 |
|---|---|---|---|---|---|
| NW Plugs & Sockets | 699 | 1,084 | 1,484 | 2,753 | 685 |
| SE Lighting | 11 | 39 | 104 | 150 | 139 |
| SW Lighting | 26 | 211 | 192 | 372 | 72 |
| NW Lighting | 268 | 229 | 137 | 136 | 60 |
| NE Plugs & Sockets | 197 | 182 | 178 | 153 | 198 |

Ratio of the 2025 mean to the historical mean ranges from **0.13 to 2.32** across circuits (e.g. SW Hand Dryer 0.13, NW Lighting 0.30, NW Plugs 0.57, SE Lighting 2.32). The correlation between the mean 24-hour profiles of the two regimes is **below 0.5 for 10 of 16 circuits** (16 circuits have data in both regimes) and negative for 3 (NE Plugs, NW RACK, SE Plugs). Seasons also differ (the historical data covers every season, 2025 covers 8 weeks of late summer), so part of the difference is seasonal; the same-season table (`same_season_by_circuit.csv`, 18 Aug–13 Oct of each year) shows the same instability (NW Lighting 240 → 179 → 87 → 60; SE Lighting 10 → 56 → 128 → 139; SW Lighting 14 → 263 → 88 → 72).

**Reading:** loads, occupancy and equipment changed between 2020 and 2025, and they also moved within 2020–2023. A model trained on old levels carries a risk of bias on the circuits that changed most.

## 4. Evidence that the history may still help (exploratory test)

Question: *if we ignore the model and only ask how well each training period predicts the 2025 test week (29 Sep–5 Oct), does old data help?*

Method: weekday × hour **median profile** per circuit, trained on different periods, scored on the 16 circuits of the test week (2,688 circuit-hours, horizon +1 h target values). This is a quick harness; it is **not** the official baseline B2 (which scores 43.7 Wh on the Task 6 common hours and uses its own training window).

| Training data | MAE (Wh), mean of 16 circuits |
|---|---|
| 2025 train weeks (19 Aug–21 Sep) | 55.3 |
| 2022, same season (18 Aug–13 Oct) | 43.1 |
| All 2020–2023, every season | 37.3 |
| 2025 train + 2020–22 same season | **35.1** |

Findings:

1. A profile trained on the old data predicts the 2025 test week **no worse, and on average better** than one trained on our 5 weeks of 2025.
2. **The gain comes mostly from one circuit.** SE Plugs & Sockets goes from 395 Wh (2025 train) to 66 Wh (combined). Without it, the means become **32.6 (2025 only) vs 33.1 (combined)**: no difference.
3. By circuit, the combined profile is better on **10 of 16** circuits and worse on **6** (for example NW RACK 3.5 → 22.8, NW Lighting 48 → 57, SE HVAC 4.7 → 6.7).
4. The final Blend (34.2 Wh day-ahead on the 1,911 official common hours) is lower than the best profile of this harness (38.2 Wh pooled, 2020–22 same season + 2025). The hours differ (2,688 vs 1,911), so this is **indicative only**; it does not show that history could not improve the Blend. It shows that **we cannot claim old data is useless**.

## 5. Position to present

> We trained on 2025 only because (a) the specification treats the two periods as separate regimes and asks for validation evidence before they are combined, (b) the ~900-day gap, the change of sampling and the level shifts of several circuits mean that comparability had to be tested before use, and (c) we had two weeks left after the mid-term review. We did **not** run the combined experiment. An exploratory test shows that history could help a simple profile model (mean MAE 55 → 35 Wh, but mostly through one circuit), so the decision is **a scope choice, not a proven result**. The protocol to test it is ready.

What we do **not** claim: that the old data is useless; that 2025-only is better than a combined model; that the model generalises beyond late summer.

## 6. Protocol to test a combined model (ready, not run)

| Step | Rule |
|---|---|
| Regimes | Historical = before 1 Jan 2024; recent = 2025 (`REGIME_CUT_UTC` in `task6_split_design.py`) |
| Features | `regime` flag; no cumulative-counter differencing across the gap; rolling inputs restarted after the gap (`new_period_gap_days: 90`) |
| Split | Same train / validation / test weeks as Task 6 (train 19 Aug–21 Sep, validation 22–28 Sep, test 29 Sep–5 Oct 2025); the history only adds training rows |
| Selection | Rule D10 (scaled MAE on the 15 training circuits, tie 0.005, simpler model wins) |
| Evidence | Same common hours, block bootstrap (24 h, 2,000 resamples); a regime is useful only if the CI of the MAE difference excludes 0 |
| Cost | Retraining Chronos-GBM and GBM on about 20× more rows; estimate 3–5 working days with validation (planning estimate) |

## 7. Last 8 days of 2025 (6–13 Oct, about 189 hours)

These hours are **not used for training, validation, test or tuning**. The reason for keeping them out is in `task6.pdf` §4 (see doc 14). They can be presented as a reserve **not used for training, selection or official scoring**; they are not untouched, because the Dash live page shows and forecasts them. Scoring the frozen Blend on them is a cheap extra check (not done yet).

## 8. Limits of this document

- The profile test uses one test week and a simple model; it says nothing about Chronos or GBM trained on history.
- Historical hours are hourly readings, 2025 hours aggregate about 43 readings; energy is comparable (Wh), noise is not.
- Level differences mix real changes and season effects.
