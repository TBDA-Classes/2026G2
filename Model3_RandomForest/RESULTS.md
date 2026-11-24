# Results — Model 3, random forest

CeDInt Storey 1 · Sprint 3 Task 1 · frozen and tested 27 October 2026

All numbers generated from the CSV files in `results/`. Lower is better everywhere.

**B1** = same hour last week · **B2** = weekday × hour median · **B3** = last observed hour

**scaled MAE** = each circuit's MAE ÷ its own training mean, averaged over circuits.
**WAPE** = total absolute error ÷ total actual energy.

---

## 1. Validation week (22–28 Sep 2025)

**scaled MAE — all 16 circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.5986 | 0.5222 | 0.3531 |   0.3142 |
| +6h       | 0.5968 | 0.5211 | 0.4744 |   0.408  |
| day-ahead | 0.5977 | 0.5217 | 0.36   |   0.4075 |

**scaled MAE — the 8 trained circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.5783 | 0.43   | 0.2904 |   0.2431 |
| +6h       | 0.5781 | 0.4315 | 0.4608 |   0.3348 |
| day-ahead | 0.5781 | 0.4302 | 0.3794 |   0.3308 |

**scaled MAE — the 8 circuits never trained on**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.6189 | 0.6144 | 0.4157 |   0.3853 |
| +6h       | 0.6156 | 0.6107 | 0.488  |   0.4813 |
| day-ahead | 0.6174 | 0.6132 | 0.3406 |   0.4842 |

**WAPE — all 16 circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.5856 | 0.4905 | 0.2504 |   0.2401 |
| +6h       | 0.5856 | 0.4911 | 0.4282 |   0.3485 |
| day-ahead | 0.5856 | 0.4909 | 0.3463 |   0.3467 |

---

## 2. Test week (29 Sep – 5 Oct 2025) — run once

**scaled MAE — all 16 circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.8937 | 0.7747 | 0.6302 |   0.6632 |
| +6h       | 0.8926 | 0.7743 | 1.2034 |   0.7488 |
| day-ahead | 0.8933 | 0.7745 | 0.7925 |   0.7498 |

**scaled MAE — the 8 trained circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 1.2663 | 1.1616 | 0.9257 |   1.0182 |
| +6h       | 1.2672 | 1.1625 | 1.8786 |   1.1397 |
| day-ahead | 1.2668 | 1.1621 | 1.1583 |   1.1366 |

**scaled MAE — the 8 circuits never trained on**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.5211 | 0.3877 | 0.3347 |   0.3082 |
| +6h       | 0.5179 | 0.386  | 0.5283 |   0.3579 |
| day-ahead | 0.5197 | 0.3869 | 0.4267 |   0.3629 |

**WAPE — all 16 circuits**

| horizon   |     B1 |     B2 |     B3 |   Forest |
|:----------|-------:|-------:|-------:|---------:|
| +1h       | 0.4975 | 0.4879 | 0.2143 |   0.2419 |
| +6h       | 0.4975 | 0.4879 | 0.4633 |   0.2997 |
| day-ahead | 0.4975 | 0.4879 | 0.345  |   0.2986 |

### Against the other models in the project

The 8 circuits every model covers, identical hours (167 per horizon).

**scaled MAE**

| horizon   |     B1 |     B2 |     B3 |    GBM |   Linear |   Forest |
|:----------|-------:|-------:|-------:|-------:|---------:|---------:|
| +1h       | 1.2663 | 1.1657 | 0.9295 | 1.0321 |   2.0803 |   1.0226 |
| +6h       | 1.2663 | 1.1657 | 1.8844 | 1.1737 |   1.275  |   1.1435 |
| day-ahead | 1.2663 | 1.1657 | 1.1612 | 1.1722 |   1.2592 |   1.1408 |

**WAPE (%)**

|           |    B1 |    B2 |    B3 |   GBM |   Linear |   Forest |
|:----------|------:|------:|------:|------:|---------:|---------:|
| +1h       | 37.53 | 30.15 | 20.37 | 22.61 |    24.63 |    21.32 |
| +6h       | 37.53 | 30.15 | 49.2  | 30.77 |    28.05 |    27.99 |
| day-ahead | 37.53 | 30.15 | 34.07 | 30.13 |    28.11 |    27.71 |

---

## 3. Test week, circuit by circuit

**+1h**

| series_id          | trained on   |   coverage |   MAE (Wh) |   scaled MAE |   WAPE |   B3 scaled MAE |
|:-------------------|:-------------|-----------:|-----------:|-------------:|-------:|----------------:|
| NE|Plugs & Sockets | yes          |      1     |       3.12 |        0.016 |  0.016 |           0.024 |
| NW|RACK            | yes          |      1     |       3.13 |        0.017 |  0.017 |           0.024 |
| NW|HVAC            | yes          |      1     |      14.17 |        0.114 |  0.201 |           0.127 |
| NW|Plugs & Sockets | yes          |      1     |     191.9  |        0.341 |  0.25  |           0.325 |
| NW|Hand Dryer      | yes          |      1     |       0.52 |        0.594 |  0.816 |           0.645 |
| NW|Lighting        | yes          |      1     |      35.87 |        0.764 |  0.431 |           0.643 |
| NW|Emerg. Lighting | yes          |      1     |      27.74 |        2.408 |  0.704 |           2.284 |
| NE|HVAC            | yes          |      1     |      10.21 |        3.892 |  0.819 |           3.334 |
| SE|HVAC            | —            |      0.381 |       1.41 |        0.031 |  0.034 |           0.038 |
| SW|Emerg. Lighting | —            |      0.345 |       0.58 |        0.049 |  0.05  |           0.085 |
| SW|Plugs & Sockets | —            |      0.565 |      23.85 |        0.091 |  0.098 |           0.07  |
| SE|Plugs & Sockets | —            |      0.887 |      88.45 |        0.152 |  0.444 |           0.086 |
| SE|Emerg. Lighting | —            |      0.381 |       0.51 |        0.226 |  0.247 |           0.327 |
| SW|Lighting        | —            |      0.702 |      15.54 |        0.306 |  0.73  |           0.409 |
| SE|Lighting        | —            |      0.702 |      40.87 |        0.311 |  0.849 |           0.292 |
| SW|Hand Dryer      | —            |      0.464 |       1.55 |        1.3   |  1.062 |           1.37  |

**+6h**

| series_id          | trained on   |   coverage |   MAE (Wh) |   scaled MAE |   WAPE |   B3 scaled MAE |
|:-------------------|:-------------|-----------:|-----------:|-------------:|-------:|----------------:|
| NW|RACK            | yes          |      1     |       3.36 |        0.018 |  0.018 |           0.018 |
| NE|Plugs & Sockets | yes          |      1     |       3.89 |        0.02  |  0.02  |           0.02  |
| NW|HVAC            | yes          |      1     |      31.4  |        0.252 |  0.445 |           0.559 |
| NW|Plugs & Sockets | yes          |      1     |     250.12 |        0.443 |  0.326 |           0.788 |
| NW|Hand Dryer      | yes          |      1     |       0.74 |        0.842 |  1.163 |           1.105 |
| NW|Lighting        | yes          |      1     |      51.25 |        1.102 |  0.616 |           1.912 |
| NW|Emerg. Lighting | yes          |      1     |      28.86 |        2.503 |  0.732 |           2.966 |
| NE|HVAC            | yes          |      1     |      10.32 |        3.937 |  0.827 |           7.66  |
| SE|HVAC            | —            |      0.381 |       1.6  |        0.036 |  0.038 |           0.039 |
| SW|Emerg. Lighting | —            |      0.345 |       0.58 |        0.049 |  0.05  |           0.068 |
| SE|Plugs & Sockets | —            |      0.887 |      43.92 |        0.075 |  0.221 |           0.091 |
| SW|Plugs & Sockets | —            |      0.565 |      31.61 |        0.12  |  0.129 |           0.128 |
| SE|Emerg. Lighting | —            |      0.381 |       0.53 |        0.237 |  0.259 |           0.323 |
| SW|Lighting        | —            |      0.702 |      30.1  |        0.587 |  1.415 |           0.703 |
| SE|Lighting        | —            |      0.702 |      86.48 |        0.654 |  1.796 |           0.477 |
| SW|Hand Dryer      | —            |      0.464 |       1.32 |        1.105 |  0.908 |           2.397 |

**day-ahead**

| series_id          | trained on   |   coverage |   MAE (Wh) |   scaled MAE |   WAPE |   B3 scaled MAE |
|:-------------------|:-------------|-----------:|-----------:|-------------:|-------:|----------------:|
| NW|RACK            | yes          |      1     |       3.39 |        0.018 |  0.018 |           0.019 |
| NE|Plugs & Sockets | yes          |      1     |       3.77 |        0.019 |  0.02  |           0.022 |
| NW|HVAC            | yes          |      1     |      31.76 |        0.255 |  0.45  |           0.303 |
| NW|Plugs & Sockets | yes          |      1     |     247.09 |        0.438 |  0.322 |           0.578 |
| NW|Hand Dryer      | yes          |      1     |       0.74 |        0.847 |  1.168 |           0.939 |
| NW|Lighting        | yes          |      1     |      50.32 |        1.076 |  0.605 |           1.126 |
| NW|Emerg. Lighting | yes          |      1     |      28.86 |        2.504 |  0.732 |           2.381 |
| NE|HVAC            | yes          |      1     |      10.31 |        3.934 |  0.827 |           3.898 |
| SE|HVAC            | —            |      0.381 |       1.36 |        0.03  |  0.033 |           0.04  |
| SW|Emerg. Lighting | —            |      0.345 |       0.56 |        0.047 |  0.048 |           0.077 |
| SE|Plugs & Sockets | —            |      0.887 |      41.18 |        0.071 |  0.207 |           0.06  |
| SW|Plugs & Sockets | —            |      0.565 |      34.71 |        0.132 |  0.142 |           0.146 |
| SE|Emerg. Lighting | —            |      0.381 |       0.53 |        0.235 |  0.257 |           0.349 |
| SW|Lighting        | —            |      0.702 |      30.67 |        0.601 |  1.442 |           0.416 |
| SE|Lighting        | —            |      0.702 |      89.51 |        0.68  |  1.859 |           0.718 |
| SW|Hand Dryer      | —            |      0.464 |       1.32 |        1.108 |  0.908 |           1.607 |

---

## 4. Parameter search

**Stage 1 — grid.** 60 configurations per horizon, scored on all 16 circuits.

Best per criterion, showing why `absolute_error` was kept:

| horizon   |   absolute_error |   squared_error |
|:----------|-----------------:|----------------:|
| +1h       |           0.314  |          0.3533 |
| +6h       |           0.42   |          0.4897 |
| day-ahead |           0.4236 |          0.493  |

Top 5 per horizon:

*+1h*

|    | max_depth   |   min_samples_leaf |   max_features |   sMAE_all16 |   sMAE_trained8 |   sMAE_unseen8 |
|---:|:------------|-------------------:|---------------:|-------------:|----------------:|---------------:|
|  0 | 12.0        |                 30 |              1 |       0.314  |          0.2467 |         0.3813 |
|  1 | None        |                 30 |              1 |       0.314  |          0.2467 |         0.3813 |
|  2 | 8.0         |                 30 |              1 |       0.3149 |          0.2472 |         0.3826 |
|  3 | None        |                 60 |              1 |       0.3157 |          0.2402 |         0.3911 |
|  4 | 12.0        |                 60 |              1 |       0.3157 |          0.2402 |         0.3912 |

*+6h*

|    | max_depth   |   min_samples_leaf |   max_features |   sMAE_all16 |   sMAE_trained8 |   sMAE_unseen8 |
|---:|:------------|-------------------:|---------------:|-------------:|----------------:|---------------:|
|  0 | None        |                 60 |            0.5 |       0.42   |          0.3451 |         0.495  |
|  1 | 12.0        |                 60 |            0.5 |       0.4203 |          0.3439 |         0.4966 |
|  2 | 8.0         |                 60 |            0.5 |       0.4211 |          0.346  |         0.4962 |
|  3 | 4.0         |                 30 |            0.5 |       0.4216 |          0.3442 |         0.499  |
|  4 | 4.0         |                 60 |            0.5 |       0.4221 |          0.3488 |         0.4954 |

*day-ahead*

|    | max_depth   |   min_samples_leaf |   max_features |   sMAE_all16 |   sMAE_trained8 |   sMAE_unseen8 |
|---:|:------------|-------------------:|---------------:|-------------:|----------------:|---------------:|
|  0 | None        |                 60 |            0.5 |       0.4236 |          0.3451 |         0.5021 |
|  1 | 12.0        |                 60 |            0.5 |       0.4239 |          0.3451 |         0.5026 |
|  2 | 8.0         |                 60 |            0.5 |       0.4255 |          0.3464 |         0.5046 |
|  3 | 4.0         |                 60 |            0.5 |       0.4262 |          0.3533 |         0.499  |
|  4 | 6.0         |                 60 |            0.5 |       0.4276 |          0.3478 |         0.5075 |

**Stage 2 — seed repetition.** 5 seeds per configuration, to separate real differences from noise.

*+1h*

|    | depth   |   min_samples_leaf |   max_features |    mean |     std |      se | within 1 SE   |
|---:|:--------|-------------------:|---------------:|--------:|--------:|--------:|:--------------|
|  0 | None    |                 60 |              1 | 0.31445 | 0.00077 | 0.00034 | True          |
|  1 | 12      |                 60 |              1 | 0.31445 | 0.00077 | 0.00034 | True          |
|  2 | 8       |                 60 |              1 | 0.31503 | 0.00072 | 0.00032 | False         |
|  3 | None    |                 30 |              1 | 0.31503 | 0.0006  | 0.00027 | False         |
|  4 | 12      |                 30 |              1 | 0.31509 | 0.00066 | 0.00029 | False         |
|  5 | 8       |                 30 |              1 | 0.31587 | 0.0006  | 0.00027 | False         |

*+6h*

|    | depth   |   min_samples_leaf |   max_features |    mean |     std |      se | within 1 SE   |
|---:|:--------|-------------------:|---------------:|--------:|--------:|--------:|:--------------|
|  0 | 12      |                 60 |            0.5 | 0.42062 | 0.00188 | 0.00084 | True          |
|  1 | 8       |                 60 |            0.5 | 0.42065 | 0.00191 | 0.00085 | True          |
|  2 | None    |                 60 |            0.5 | 0.42089 | 0.00168 | 0.00075 | True          |
|  3 | 4       |                 60 |            0.5 | 0.42134 | 0.00241 | 0.00108 | True          |
|  4 | 6       |                 60 |            0.5 | 0.42161 | 0.00258 | 0.00116 | False         |
|  5 | 4       |                 30 |            0.5 | 0.42239 | 0.00291 | 0.0013  | False         |

*day-ahead*

|    | depth   |   min_samples_leaf |   max_features |    mean |     std |      se | within 1 SE   |
|---:|:--------|-------------------:|---------------:|--------:|--------:|--------:|:--------------|
|  0 | 4       |                 60 |            0.5 | 0.42502 | 0.00244 | 0.00109 | True          |
|  1 | None    |                 60 |            0.5 | 0.42694 | 0.00205 | 0.00092 | False         |
|  2 | 12      |                 60 |            0.5 | 0.42712 | 0.00217 | 0.00097 | False         |
|  3 | 8       |                 60 |            0.5 | 0.42733 | 0.00179 | 0.0008  | False         |
|  4 | 6       |                 60 |            0.5 | 0.4284  | 0.0011  | 0.00049 | False         |
|  5 | 4       |                 30 |            0.5 | 0.432   | 0.00265 | 0.00119 | False         |

**Extending `min_samples_leaf` past the grid edge.** 60 was the largest value in the grid and it won, so the search was extended in both directions until the score turned.

| horizon   |     60 |    100 |    150 |    250 |      400 |      600 |      900 |     1400 |
|:----------|-------:|-------:|-------:|-------:|---------:|---------:|---------:|---------:|
| +1h       | 0.3146 | 0.3144 | 0.3147 | 0.3366 | –        | –        | –        | –        |
| +6h       | 0.4201 | 0.4146 | 0.4104 | 0.4092 |   0.4218 |   0.4254 |   0.4787 |   0.501  |
| day-ahead | 0.4263 | 0.4206 | 0.4174 | 0.4073 |   0.4187 |   0.4236 |   0.4771 |   0.5002 |

– = not run. At +1h the score had already turned by 250, so the larger values were only
needed at the long horizons, where it was still improving.

**Stage 3 — rolling-origin folds.** Three expanding windows inside the training period, leaf size expressed as a fraction of training rows.

*+6h*

| cfg          |   fold1 |   fold2 |   fold3 |   mean |
|:-------------|--------:|--------:|--------:|-------:|
| d4 leaf2.7%  |  0.3763 |  0.4186 |  0.3429 | 0.3793 |
| d4 leaf4.4%  |  0.3817 |  0.4322 |  0.3497 | 0.3878 |
| d12 leaf1.8% |  0.3848 |  0.4239 |  0.3598 | 0.3895 |
| d12 leaf1.1% |  0.4006 |  0.4239 |  0.356  | 0.3935 |

*day-ahead*

| cfg          |   fold1 |   fold2 |   fold3 |   mean |
|:-------------|--------:|--------:|--------:|-------:|
| d4 leaf2.7%  |  0.3844 |  0.417  |  0.3484 | 0.3833 |
| d4 leaf4.4%  |  0.38   |  0.4295 |  0.3524 | 0.3873 |
| d12 leaf1.1% |  0.4045 |  0.4237 |  0.3576 | 0.3953 |
| d12 leaf1.8% |  0.4048 |  0.4285 |  0.3745 | 0.4026 |

---

## 5. Where each number comes from

| File | Contents |
|---|---|
| `task1_rf_final_summary.csv` | Validation week, summary by model and horizon |
| `task1_rf_final_per_circuit.csv` | Validation week, every circuit |
| `task1_rf_test_summary.csv` | Test week, summary by model and horizon |
| `task1_rf_test_per_circuit.csv` | Test week, every circuit |
| `task1_rf_test_comparison.csv` | Test week against GBM, linear and the baselines, same hours |
| `task1_rf_test_predictions.parquet` | Every test-week forecast |
| `step3_stage1_grid.csv` | All 180 configurations tried |
| `step3_stage2_seeds.csv` | Seed repetition |
| `step3_stage3_rolling.csv`, `step3_rolling_fractional.csv` | Rolling-origin folds, before and after the fractional-leaf fix |
| `step3_leaf_extension.csv`, `step3_leaf_extension2.csv` | Pushing `min_samples_leaf` past the grid edge |
| `step3_official_vs_folds.csv` | Official week against fold means |
| `task1_rf_all16_per_circuit.csv` | Step 1, design A vs design B |
| `task1_rf_TEST_ALREADY_RUN.txt` | Guard — the test week is spent |
