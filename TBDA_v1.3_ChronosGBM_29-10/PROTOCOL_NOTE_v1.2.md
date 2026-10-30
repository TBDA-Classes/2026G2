# Protocol note — dataset v1.2 (28 Oct 2026)

1. **The test week (29 Sep – 5 Oct 2025) has been used before.** Task 7 baselines, Task 8 GBM, the Sprint 3
   linear model and Chronos were each run once on it, on 8 circuits (NE + NW) of dataset v1.1.
2. **Why the data rules change now:** the teacher required forecasts for all zones and circuits, and allowed
   us to choose the training data if the choice is logical and documented. The row-count rule
   (`THRESHOLD = 30`) had excluded all SE and SW circuits. The new rules (`DECISIONS_v1.2.md`) are applied
   identically to all 16 circuits. They were not chosen by looking at test scores.
3. **What stays fixed:** splits, horizons, issue times, MAE, fit on training data only, configuration chosen on
   validation and frozen before test.
4. **Old results are kept** (v1.1 files and frozen configs are not overwritten; v1.2 files carry `_v1.2` in
   their names).
5. **For the 8 NE/NW circuits** the v1.2 validity changes only where the D2 flag removes hours; every changed
   hour is listed in `results/v1.2_nenw_validity_changes.csv`.
6. The single v1.2 test run happens after all v1.2 models are frozen (point 8, not part of this package).
