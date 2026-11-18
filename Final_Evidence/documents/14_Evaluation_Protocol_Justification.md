# Evaluation protocol — how models were compared and chosen, and what it costs

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 18 Nov 2026
**Authors:** Maxime (main author of this document) · Claude (co-author). The protocol itself was designed by the team in Task 6 (`task6.pdf`) and Phase 0 / v1.3 (`DECISIONS_v1.2.md`).
**Sources:** `CeDInt__Modelling_Problem_Specification.pdf` (spec), `task6.pdf`, `task6_split_design.py`, `TBDA_v1.3_ChronosGBM_29-10/config.py`, `DECISIONS_v1.2.md`, `PROTOCOL_NOTE_v1.2.md`, `models/model_choice_v1.3.json`, `Task6_rev0_03-11/RESULTS.md` and `results/task6_test_16circuits/`
**Related:** `08_Scope_Decision_2025_Only.md` (why 2025 only), `12_Data_Cleaning_Justification.md`, `12a_Cleaning_Checks.md`, `10_Evidence_Map.md`

> **Reading note.** This document justifies choices that already exist. It adds no new result. Every number comes from the files listed above; the file is named next to each claim.

## 1. Summary

- **Chronological split** of the 2025 regime: train 19 Aug–21 Sep, validation 22–28 Sep, test 29 Sep–5 Oct 2025 (UTC). Data after 5 Oct was left outside on purpose (`task6.pdf` §4).
- **Three horizons:** +1 h, +6 h and day-ahead (24 hourly values issued at 00:00 Madrid). The spec requires the 24-hour horizon; +1 h and +6 h were added in Task 6.
- **Metrics:** MAE primary, RMSE secondary, no MAPE (spec §6). The choice uses **scaled MAE** (MAE ÷ circuit training mean, mean over the 15 training circuits, D6).
- **Baselines** B1 / B2 / B3 are reported everywhere but can never be chosen (D10a).
- **Rule D10**, fixed on 29 Oct **before any v1.3 score**: best scaled MAE on validation, tie within 0.005, tie-break scaled RMSE, then the simpler model.
- **Final comparison:** every model on the same 1,911 test circuit-hours per horizon, with 95 % confidence intervals from a block bootstrap (`Task6_rev0_03-11`).

## 2. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### E1 — Chronological split, one week each for validation and test

- **Decision.** Train 19 Aug–21 Sep, validation 22–28 Sep, test 29 Sep–5 Oct 2025, boundaries in UTC (`config.SPLITS`). The partial first day (18 Aug) is excluded.
- **Why.** This is a forecasting problem: a random split would let the model learn from hours that come after the ones it predicts (`task6.pdf` §1). Seven days cover a full week, weekdays and weekend (`task6.pdf` §4).
- **Evidence.** Dates chosen after an hourly coverage analysis of every zone (`task6.pdf` §4, `task6_split_design.py`). The test week stays unseen during selection (spec §7, `task6.pdf` §8).
- **Alternative rejected.** Random or k-fold cross-validation (leaks the future). Several rolling test windows (not enough data: 8 weeks in total, 5 needed for training).
- **Weakness.** One validation week and one test week only. Many differences between the best models are therefore ties (`RESULTS.md` §6).

### E2 — Data after 5 October kept outside

- **Decision.** The hours from 6 Oct to the end of the data (13 Oct 2025) are not used for training, selection or scoring.
- **Why.** Written in `task6.pdf` §4: "Data after 5 October remain outside the first evaluation protocol and may be used later for additional analysis or Sprint 3 work." Validation and test were sized as two full weeks; the tail is less than a full week.
- **Evidence.** `task6.pdf` §4; `config.py` comment on `SPLITS` ("everything after 5 Oct is outside"). This answers the open point "why 6–13 Oct was left untouched" in `10_Evidence_Map.md` §3.
- **Alternative rejected.** Add the tail to the test week (an unequal second week, decided after the split) or to training (would shift every split).
- **Weakness.** The reserve was never used. It is the only data no model or person has looked at, so it could serve as a second, independent check of the frozen Blend v1.3. Not done.

### E3 — The test week is used once, at the end

- **Decision.** All v1.3 models were frozen and the final model chosen on validation before the single v1.3 test run (`PROTOCOL_NOTE_v1.2.md` §3, §6).
- **Why.** A test week used to choose would no longer measure performance on unseen data.
- **Evidence.** `model_choice_v1.3.json` (choice of 29 Oct) precedes the Task 6 test comparison (3 Nov).
- **Weakness, stated openly.** The same test week had been used before, in Sprint 3, for the baselines, GBM v1.0, the linear model and Chronos on 8 NE/NW circuits of dataset v1.1 (`PROTOCOL_NOTE_v1.2.md` §1). Those earlier scores were known to the team when v1.2 / v1.3 were designed. The v1.2 data rules were not chosen by looking at test scores (§2 of the same note), but an indirect influence cannot be excluded.

### E4 — Three horizons: +1 h, +6 h, day-ahead

- **Decision.** +1 h (next hour), +6 h (the hour starting 5 h after issue) and day-ahead (24 hourly values issued at 00:00 Madrid) (`config.HORIZONS`, `task6.pdf` §3).
- **Why.** The spec requires hourly forecasts over **24 hours**, "to allow both the identification of variations during the day and the anticipation of the next day's workload" (spec §2). Task 6 added a short-term (+1 h) and a medium-term (+6 h) case to see how accuracy changes with lead time.
- **Evidence.** Test MAE of Blend v1.3: 22.2 / 34.7 / 34.2 Wh (`RESULTS.md` §1). The alert product uses the **day-ahead** forecast (`Sprint4_UX_EnergyWatch`, `Sprint4_Task3_UX_Dash`).
- **Alternative rejected.** Day-ahead only. It would have hidden that persistence is very hard to beat one hour ahead, which is useful to know.
- **Weakness.** At +1 h no model is significantly better than persistence (Blend −1.8 Wh, CI −4.7 to +2.6; `RESULTS.md` §2), and the product does not need a +1 h forecast. The +1 h horizon is evidence, not a product feature. Dropping it would not change the choice of Blend v1.3, which D10 picked at every horizon.

### E5 — Metrics: MAE in Wh to report, scaled MAE to choose

- **Decision.** MAE primary, RMSE secondary, MAPE not used (spec §6, `task6.pdf` §7). Selection uses scaled MAE: MAE of each circuit ÷ its training mean, averaged over the 15 training circuits (D6).
- **Why.** MAPE explodes near zero (hand dryers, emergency lighting). In Wh, NW Plugs & Sockets (about 563 Wh/h) would decide the choice alone; scaling gives every circuit the same weight (`DECISIONS_v1.2.md` D10).
- **Evidence.** Validation scaled MAE of Blend v1.3: 0.271 / 0.349 / 0.351 (`model_choice_v1.3.json`).
- **Alternative rejected.** MAE in Wh for selection (one circuit dominates); WAPE (same problem).
- **Weakness.** Scaling moves the weight to the smallest circuits. Without the 5 circuits flagged by the cleaning, the Blend's scaled MAE drops from 0.41–0.52 to 0.13–0.21, and NE HVAC alone makes more than half of the 16-circuit mean at +1 h (`12a_Cleaning_Checks.md`). MAE in Wh is the safer headline for the presentation.

### E6 — Baselines are references, never candidates

- **Decision.** B1 same hour last week and B2 weekday × hour median (both named in spec §6 and `task6.pdf` §6), plus B3 persistence. They are scored next to every model but cannot be chosen (D10a, option B).
- **Why.** The question is whether a model adds value over a simple rule. If a baseline is as good, the report says so instead of hiding it.
- **Evidence.** `model_choice_v1.3.json`: no baseline within the tie margin of the Blend on validation. On test, Blend beats B2 significantly at every horizon and persistence only at +6 h (`RESULTS.md` §2).
- **Alternative rejected (option A).** Let baselines compete. On the v1.2 validation forecasts, D10 would then have chosen **persistence** day-ahead (0.3708 vs Chronos 0.3661, inside the margin, lower RMSE) (`DECISIONS_v1.2.md` D10a).
- **Weakness.** Option B is a team choice. Day-ahead, persistence stays close: tie on test in Wh (CI −16.8 to +0.1 Wh).

### E7 — Selection rule D10, written before the scores

- **Decision.** Best validation scaled MAE wins; every candidate within 0.005 is tied; ties go to the lowest scaled RMSE, then to the simpler model (`DECISIONS_v1.2.md` D10).
- **Why.** One validation week cannot separate models closer than about 0.005 (v1.2 gaps of 0.0049 and 0.003). RMSE then decides because large misses matter for energy. Writing the rule first prevents choosing after seeing the results; the scripts refuse to run until `config.D10_AGREED` is set (29 Oct, Emily and Alex).
- **Evidence.** D10 chose Blend v1.3 at every horizon (`model_choice_v1.3.json`). Weights GBM / ChronosGBM / Chronos-Bolt: 0.30 / 0.20 / 0.50 (+1 h), 0.10 / 0.35 / 0.55 (+6 h), 0.15 / 0.10 / 0.75 (day-ahead).
- **Alternative rejected.** Lowest MAE wins, no margin: day-ahead would have picked Chronos-Bolt alone (best validation MAE, 27.5 vs 28.8 Wh), which is weaker on test (36.2 vs 34.2 Wh) (`RESULTS.md` §4).
- **Weakness.** The day-ahead choice of Blend over Chronos depends on the 5 flagged circuits: without them Chronos wins by 0.008 (`12a_Cleaning_Checks.md` A2). The Blend still has the lowest day-ahead test MAE.

### E8 — Same hours for every model, and significance tests

- **Decision.** Task 6 scores every model on the hours valid for all of them: 1,911 circuit-hours per horizon (16 circuits). 95 % CIs come from a circular block bootstrap (24-hour blocks, 2,000 resamples, all circuits of an hour kept together); a difference counts only if its CI excludes 0.
- **Why.** Models with different missing hours would otherwise be compared on different questions (`task6.pdf` §8). Errors of consecutive hours are correlated, so hours cannot be resampled one by one.
- **Evidence.** `Task6_rev0_03-11/README.md`, `results/task6_test_16circuits/metrics_with_CI.csv`, `pairwise_differences.csv`.
- **Weakness.** With 7 days the bootstrap has only 7 independent blocks per week: intervals are wide and most top-model differences are ties.

### E9 — No information from the future

- **Decision.** Inputs only use values observed before the issue time; scaling, medians and every fitted transform use training data only (spec §4, `task6.pdf` §9).
- **Evidence.** The baseline medians (B2) and the circuit scales are computed on training hours only (`task6.pdf` §6, `task8_model.series_scale`). Prophet's test `test_train_frame_uses_training_hours_before_cutoff_only` checks the same rule for that experiment.
- **Weakness.** Observed weather was tested later as an input (Sprint 4 Task 2). It was not kept, so no future information reached the final model.

## 3. If we did it again

1. **Use the reserve (6–13 Oct)** as a second test week for the frozen Blend v1.3, with the same hours rule, before claiming any number.
2. **Decide the horizons with the product owner first.** The product needs day-ahead; +1 h could have been a short sensitivity check instead of a full horizon.
3. **Report MAE in Wh as the headline from the start**, and keep scaled MAE for selection only.
4. **Keep the test week untouched until the final model is frozen**, including in early sprints, so that E3 has no exception.
5. **With more data, use several test windows** (rolling origin) to narrow the confidence intervals.

## 4. Likely questions

| Question | Short answer |
|---|---|
| Why not a random split? | Forecasting: a random split would train on the future. |
| Why only one test week? | 8 weeks of data, 5 needed for training. We say it is small and report CIs. |
| Why were 6–13 Oct not used? | Task 6 left them outside the first protocol as a reserve; they were never used. |
| Is +1 h useful? | It shows persistence is hard to beat one hour ahead. The product uses day-ahead. |
| Why scaled MAE and not MAE? | In Wh one circuit decides the choice; scaling weights all circuits equally. MAE in Wh is reported. |
| Could a baseline have won? | Baselines were never candidates (D10a). Under the other option, persistence would have won day-ahead on v1.2. |
| Was the test week really unseen? | For the v1.3 choice, yes. In Sprint 3 it had been used on 8 circuits; we state it. |
| Are the differences real? | Block bootstrap: Blend beats the weekday median at every horizon and persistence only at +6 h. |
