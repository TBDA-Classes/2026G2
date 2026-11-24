# Audit summary

Date: 2026-11-18  
Environment: Python 3.13.15 (Windows), pandas 3.1.1, numpy 2.5.5, scikit-learn 1.9.1, scipy 1.18.1, pyarrow 26.0.1, prophet 1.5.0, torch 2.15.0+cpu, chronos-forecasting 2.3.2, dash 4.5.0

## Results by level

| Level | PASS | FAIL | ERROR | NOT RUN | MANUAL | Total |
|---|---|---|---|---|---|---|
| L1 exists | 18 | 3 | 0 | 0 | 0 | 21 |
| L2 matches | 31 | 2 | 0 | 0 | 0 | 33 |
| L3 reproduces | 15 | 3 | 0 | 0 | 0 | 18 |
| manual | 0 | 0 | 0 | 0 | 3 | 3 |
| **All** | 64 | 8 | 0 | 0 | 3 | **75** |

## Checks that did not pass

| Check | Status | What | Expected | Obtained | Detail |
|---|---|---|---|---|---|
| L1-03 | FAIL | Every repository path cited in the Deliverables Index exists | 0 missing | 1 missing of 27 | Sprint4_Task3_UX_Dash/cache/ML_Blend_v1.3_test_recomputed.csv |
| L1-17 | FAIL | Task-based usability test report | found | not found | missing: *sabilit* |
| L1-18 | FAIL | User guide with screenshots | found | not found | missing: *ser*uide* |
| L2-27 | FAIL | Evidence Map says the temperature gain is 0.0007-0.0018; check against the Task 2 table | -0.0018 | -0.0003 |  |
| L2-32 | FAIL | Backlog PB-39 quotes 4.7 / 5.2 / 5.6 alerts per day: check against the Dash file | 4.7/5.2/5.6 | 8.5/4.79/3.21/6.14/4.5 |  |
| L3-03 | FAIL | Frozen models regenerate the stored Blend forecasts (test and validation) | same | 0 of 2 files the same | blend_test.csv: largest difference 6.71e-05 is above the tolerance 1e-06 / blend_validation.csv: largest difference 6.1e-05 is above the tolerance 1e-06 |
| L3-04 | FAIL | Live engine self-test passes | pass | script failed | see results/logs/L3-04.txt |
| L3-14 | FAIL | Prophet validation re-run (112 configurations) | same | 1 of 2 files the same | per_circuit_validation.csv: largest difference 0.0714 is above the tolerance 0.005 / comparison_validation.csv: same (15 rows, largest difference 0.0029) |

## Backlog items

| Item | Worst status | Checks |
|---|---|---|
| PB-01 | PASS | L1-04 |
| PB-02 | PASS | L1-04 |
| PB-03 | PASS | L1-04 |
| PB-04 | PASS | L1-05 |
| PB-05 | PASS | L1-05 |
| PB-06 | MANUAL | M-02 |
| PB-07 | paths only | L1-02 (the paths cited for this item exist) |
| PB-08 | paths only | L1-02 (the paths cited for this item exist) |
| PB-09 | paths only | L1-02 (the paths cited for this item exist) |
| PB-10 | paths only | L1-02 (the paths cited for this item exist) |
| PB-11 | paths only | L1-02 (the paths cited for this item exist) |
| PB-12 | MANUAL | M-02 |
| PB-13 | PASS | L1-06, L2-01, L2-02, L3-07 |
| PB-14 | MANUAL | L1-07, M-02 |
| PB-15 | PASS | L1-08, L3-10 |
| PB-16 | paths only | L1-02 (the paths cited for this item exist) |
| PB-17 | PASS | L1-08, L3-11 |
| PB-18 | paths only | L1-02 (the paths cited for this item exist) |
| PB-19 | paths only | L1-02 (the paths cited for this item exist) |
| PB-20 | PASS | L1-09 |
| PB-21 | FAIL | L1-10, L2-26, L2-27, L3-15 |
| PB-22 | PASS | L3-10 |
| PB-23 | PASS | L1-11, L3-01 |
| PB-24 | FAIL | L3-03, L3-04 |
| PB-25 | paths only | L1-02 (the paths cited for this item exist) |
| PB-26 | PASS | L1-12 |
| PB-27 | PASS | L1-12, L2-14, L3-02 |
| PB-28 | FAIL | L1-13, L2-24, L2-25, L3-13, L3-14 |
| PB-29 | PASS | L3-12 |
| PB-30 | PASS | L2-16, L3-05 |
| PB-31 | PASS | L1-14 |
| PB-32 | PASS | L3-18 |
| PB-33 | paths only | L1-02 (the paths cited for this item exist) |
| PB-34 | paths only | L1-02 (the paths cited for this item exist) |
| PB-35 | paths only | L1-02 (the paths cited for this item exist) |
| PB-36 | paths only | L1-02 (the paths cited for this item exist) |
| PB-37 | paths only | L1-02 (the paths cited for this item exist) |
| PB-38 | PASS | L1-15, L2-28, L2-29, L2-30, L3-06 |
| PB-39 | FAIL | L1-15, L2-31, L2-32, L3-06 |
| PB-40 | paths only | L1-02 (the paths cited for this item exist) |
| PB-41 | paths only | L1-02 (the paths cited for this item exist) |
| PB-42 | paths only | L1-02 (the paths cited for this item exist) |
| PB-43 | PASS | L1-16 |
| PB-44 | paths only | L1-02 (the paths cited for this item exist) |
| PB-45 | paths only | L1-02 (the paths cited for this item exist) |
| PB-46 | paths only | L1-02 (the paths cited for this item exist) |
| PB-47 | paths only | L1-02 (the paths cited for this item exist) |
| PB-48 | paths only | L1-02 (the paths cited for this item exist) |
| PB-49 | PASS | L1-19 |
| PB-50 | MANUAL | M-03 |
| PB-51 | FAIL | L1-17, M-03 |
| PB-52 | PASS | L1-19 |
| PB-53 | paths only | L1-02 (the paths cited for this item exist) |
| PB-54 | PASS | L1-04 |
| PB-55 | FAIL | L1-18, M-03 |
| PB-56 | PASS | L1-05 |
| PB-57 | FAIL | L1-03, L1-21, L3-07, L3-12 |
| PB-58 | PASS | L1-20 |
