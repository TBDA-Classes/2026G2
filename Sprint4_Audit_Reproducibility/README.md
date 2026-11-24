# Sprint 4 — Reproducibility audit

**Question.** Can every result we show be found, checked and produced again from the repository?

**Answer.** Yes for the results. 64 of the 72 automatic checks pass. Every number of the final model
(Task 6 test MAE 22.2 / 34.7 / 34.2 Wh, CIs, significance, ASHRAE 14, detection test, Dash band, Prophet, temperature)
is in its result file and comes out again when the scripts are run on another computer. The 8 checks that do not
pass are: 3 files that are not in the repository, 2 sentences in documents that quote a wrong number, and 3 very
small numeric differences between computers that do not change any conclusion.

Audit run on 18 Nov 2026, on the repository as it was that day.

## What is checked

The plan is the table `audit_checks.csv`: one line per check. It covers the 58 items of the product backlog
(`Sprint4_Task4_Documentation/documents/06_Backlog_Coverage.md`) and the 23 claims of the Evidence Map
(`Final_Evidence/documents/10_Evidence_Map.md`), which are the numbers of the final presentation.

Every check has one of three levels:

| Level | Question | Example |
|---|---|---|
| **L1 exists** | Is the file that a document talks about in the repository? | Every path written in the Evidence Map exists |
| **L2 matches** | Is the number in the document the number in the result file? | Blend test MAE 22.2 / 34.7 / 34.2 Wh in `metrics_with_CI.csv` |
| **L3 reproduces** | If we run the script again, do we get the same file? | Task 6 comparison, frozen model, detection test, Prophet, Chronos-Bolt |

Three more lines are **manual**: they cannot be checked from the files (for example, the commit dates on GitHub
that show the test week was used after the model choice).

To add a check, add a line to `audit_checks.csv`. The columns are explained at the end of this page.

## Rules of the audit

- **Read only.** The audit never changes a file of the repository. Level 3 runs the scripts in a copy of the
  repository (in the computer's temporary folder) and compares the new files with the original ones.
- **No old file can pass by mistake.** Before a script runs, the files it should create are deleted from the copy.
- **Tolerances are fixed before running.** Exact for files that should not change; small known differences are
  allowed where the team documented them (for example 0.0018 for retraining ChronosGBM, Stan for Prophet).
- **A failed check is a result, not an error of the audit.** It is listed with the reason, and the owner of the
  file decides what to change.

## Results

| Level | Pass | Fail | Total |
|---|---|---|---|
| L1 exists | 18 | 3 | 21 |
| L2 matches | 31 | 2 | 33 |
| L3 reproduces | 15 | 3 | 18 |
| **All automatic checks** | **64** | **8** | **72** |
| Manual (to check on GitHub or with CeDInt) | | | 3 |

Environment: Python 3.13, pandas 3.1, numpy 2.5, scikit-learn 1.9.1, Prophet 1.5.0, torch 2.15 (CPU),
chronos-forecasting 2.3.2, Windows. This is a different computer and newer library versions than the ones the
team used, which makes the level-3 result stronger.

**What reproduces (level 3).**

| Check | Result |
|---|---|
| Model unit tests, including the leakage asserts | pass |
| Task 6 comparison (6 runs, 18 result files) | identical |
| Hourly dataset rebuilt from `CLEAN DATA all zones.zip` | identical to the frozen dataset (21,456 rows) |
| Chronos-Bolt run again on the test week with the official weights | weights match the recorded SHA-256; forecasts within 0.0015 Wh |
| Detection test of the Dash app (7 files) | identical |
| Dash 90 % band on the test week | 89.9 / 91.4 / 90.7 %, as written |
| ASHRAE 14, traffic light, regime comparison, cleaning checks | identical |
| Energy Watch rebuild and the 17 documentation CSV files | identical; `data.json` fingerprint `4664a3f679443c6c` as recorded |
| Temperature experiment (Task 2), error diagnosis (Task 1), linear model by hour | identical |
| Prophet tests; Prophet re-run | tests pass; overall score 0.470 vs 0.472 (see finding 7) |

Full list: `results/audit_matrix.csv`. Summary with the backlog table: `results/audit_summary.md`.
The output of every level-3 script is written to `results/logs/` on your computer (not in git: it contains local
folder names).

## Findings (the 8 checks that do not pass)

Suggested changes are for the owner of each file. The audit did not change them.

**Missing from the repository**

1. **L1-17, L1-18 — usability test report (PB-51) and user guide with screenshots (PB-55).** The backlog says
   they are prepared by the team, but no file is in the repository yet. They should be added before 14 Dec.
2. **L1-03 — `Sprint4_Task3_UX_Dash/cache/ML_Blend_v1.3_test_recomputed.csv`.** The demo plan
   (`11_Deliverables_Index_Dash.md`) needs it on the demo computer, and the file is not in git (it is made by the
   **Run model** button). Risk for the demo on 30 Nov: press **Run model** once on the demo computer before the
   presentation.

**A document quotes a wrong number**

3. **L2-27 — Evidence Map, claim 18.** It says the temperature "gain" is 0.0007–0.0018. In the Task 2 report these
   two numbers are the differences found when ChronosGBM is retrained, not the effect of temperature. The effect of
   temperature on the Blend is +0.0068 (+1 h), +0.0080 (+6 h) and −0.0003 (day-ahead) scaled MAE
   (`Sprint4_Task2_Temperature/outputs/experiment_table.csv`). Suggested text: "Temperature (Open-Meteo): Blend worse
   at +1 h and +6 h, no change day-ahead (−0.0003 < 0.005)".
4. **L2-32 — Backlog PB-39.** It quotes 4.7 / 5.2 / 5.6 alerts per day. These are the Energy Watch numbers
   (`Sprint4_Task4_Documentation/analysis/injection_quiet_data_alerts.csv`). For the Dash app (the main
   dashboard) the numbers are 8.5 / 4.8 / 3.2 per day at the 80 / 90 / 95 % band
   (`Sprint4_Task3_UX_Dash/analysis/injection_quiet_data_alerts_dash.csv`), as the Evidence Map says.

**Very small differences between computers (no conclusion changes)**

5. **L3-03 — frozen Blend forecasts.** Run again with the frozen models, the forecasts differ from the stored ones
   by at most 0.00007 Wh (on values of about 1,500 Wh). The Dash README says "identical (5.7e-14 Wh)"; that is true
   on the computer where it was made, not on this one.
6. **L3-04 — `live_engine.py --check`.** For the same reason the self-test of the Dash app stops with an
   `AssertionError` on this computer: it asks for a difference below 1e-6 Wh and finds 0.00007 Wh. Suggestion for
   the owner: use a tolerance such as 0.001 Wh, so the check passes on other computers.
7. **L3-14 — Prophet.** The overall scores come out again (0.470 / 0.469 / 0.470 vs 0.473 / 0.472 / 0.472, within
   0.005) but two circuits move by up to 0.07 (NW Lighting, NW HVAC). The Prophet README already warns that Stan can
   give other numbers on another computer (the first run used Python 3.12, pandas 2.2, numpy 2.1). The conclusion
   (Prophet 0.47 vs Blend 0.27–0.35) does not change.

**Manual checks (not done by the scripts)**

- M-01: on GitHub, check that the Task 6 test files were committed after `model_choice_v1.3.json` (29 Oct).
- M-02: column meaning (Er / Ea) and units of W and I still need CeDInt's confirmation.
- M-03: same as finding 1.

## How to run

From the repository root, with the team environment plus Prophet and Chronos-Bolt:

```
pip install -r Sprint4_Audit_Reproducibility/requirements.txt
python Sprint4_Audit_Reproducibility/run_audit.py --quick     # levels 1 and 2, a few seconds
python Sprint4_Audit_Reproducibility/run_audit.py             # all levels, about 50 minutes (Prophet alone about 30)
python -m pytest -q Sprint4_Audit_Reproducibility/tests       # 5 unit tests of the audit code
```

One level-3 check can be run alone: `python Sprint4_Audit_Reproducibility/rerun_scripts.py L3-02`.

What you need:
- **Levels 1 and 2** (`--quick`): a clone of the repository and pandas, numpy, pyarrow. A few seconds.
- **Level 3**: Python 3.11 or newer, the packages of `requirements.txt` (1–2 GB with torch), internet the first
  time (Chronos-Bolt weights, about 250 MB) and about 50 minutes.
- Tested on Windows. The code uses only portable paths, so it should also work on macOS and Linux.
- On another computer, the checks of findings 5–7 may pass or fail: they measure very small differences between
  computers.
- Running the audit rewrites the files in `results/`. Commit them only if you want to publish a new audit run.

## Files

| File | Content |
|---|---|
| `audit_checks.csv` | The audit plan: one line per check |
| `common.py` | Small helpers: read the plan, compare numbers and tables |
| `check_files.py` | Level 1 (exists) |
| `check_numbers.py` | Level 2 (matches); includes rule D10 written again from `DECISIONS_v1.2.md` |
| `rerun_scripts.py` | Level 3 (reproduces) |
| `make_summary.py` | Puts the three levels together: `results/audit_matrix.csv`, `results/audit_summary.md` |
| `run_audit.py` | Runs everything in order |
| `tests/test_audit.py` | Unit tests on small made-up data |

## Columns of `audit_checks.csv`

| Column | Meaning |
|---|---|
| `check_id` | L1-.., L2-.., L3-.., M-.. |
| `level`, `type` | Level and kind of check (`exists`, `doc_paths`, `value`, `sha256`, `function`, `rerun`, `manual`) |
| `pb`, `claim` | Backlog items (PB-xx) and Evidence Map claims (EMxx) that the check supports |
| `what` | The check in one sentence |
| `file` | File(s) to read, or the original files to compare with (`;` between several; `*` allowed) |
| `filter`, `column` | For `value`: the row (`column=value;...`) and the column to read. For `function`: the name of the calculation |
| `expected`, `tolerance` | The value the document gives, and the largest difference accepted |
| `command`, `output` | For level 3: the command to run, and where it writes when that is not the original place |
| `note` | Anything a reader should know |

## Limits

- The audit checks that results are **consistent and reproducible**. It does not say that the modelling choices
  were the best ones.
- The zip of the repository has no git history, so the order of events (model chosen before the test run) is a
  manual check on GitHub.
- Some facts can only be confirmed by CeDInt (column meaning, units of W and I): they stay open points.

*Written with the help of Claude (Anthropic) and submitted by Lucía.*
