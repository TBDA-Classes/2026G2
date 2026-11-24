# Parameter table — Model 3, random forest

Requested by the data owner on 26 October: every value that can change a result, in one place.

**This file is also meant as a template.** If you are documenting another model, copy the
structure (§1–§4) and replace the values. Section 0 explains how.

---

## 0. How to use this as a template

### The one rule: parameters are not all the same kind

Putting them in a single list is how a data decision gets "tuned" by accident and silently
invalidates every comparison in the project. Sort every parameter into one of three types.

| Type | What it is | Who may change it | Cost of changing |
|---|---|---|---|
| **Protocol** | Defines the experiment: splits, horizons, target, metric | Whole team, as a recorded amendment | Nothing is comparable with anything else any more |
| **Data** | Decides which rows exist: thresholds, filters, eligibility | Whole team, with a dataset version bump | A new dataset version — **every model re-runs**, including frozen ones |
| **Model** | Hyperparameters of your own model | You, freely, on validation | Nothing outside your model |

### Status labels

- **frozen** — agreed, do not touch
- **open** — flagged, needs a team decision
- **tuned** — chosen on validation, with the search space recorded
- **spent** — a one-shot resource that has been used (the test week)

### Minimum each row needs

Parameter · value · where it lives · status · what changes if you change it.

For a **tuned** row, also record the values you searched — not just the winner. A reader
cannot judge a choice without knowing the alternatives, and "the winner was at the edge of the
grid" is only visible if the grid is written down.

### Why this matters, concretely

`THRESHOLD = 30` was a data parameter that lived only inside one `config.py` and one Excel
sheet. It excluded 8 of 16 circuits — half the floor — and nobody outside its author knew it
existed until 26 October. A visible parameter table makes that kind of decision impossible to
miss.

---

## 1. Protocol — never change

| Parameter | Value | Where | Status | If changed |
|---|---|---|---|---|
| `SPLITS.train` | 19 Aug – 22 Sep 2025 | `config.py` | frozen | All models refit |
| `SPLITS.validation` | 22 – 29 Sep 2025 | `config.py` | frozen | All selection decisions void |
| `SPLITS.test` | 29 Sep – 6 Oct 2025 | `config.py` | frozen | All final numbers void |
| `SPLIT_TZ` | UTC | `config.py` | frozen | Every split boundary moves |
| `HORIZONS` | +1h, +6h, day-ahead (24 leads) | `config.py` | frozen | Results not comparable |
| `ISSUE_TZ_DAY_AHEAD` | Europe/Madrid, 00:00 local | `config.py` | frozen | Changes which hours day-ahead covers |
| Target | `energy_Wh` | Task 5 spec | frozen | A different problem |
| Primary metric | MAE (RMSE secondary) | Sprint 3 plan | frozen | A different winner is possible |
| `SELECTION_METRIC` | `mean_scaled_MAE` | `config.py` | **open** | See §4 |
| Test-week use | once, after freezing | Sprint rule 3 | **spent 27 Oct** | Nothing here may change now. `results/task1_rf_TEST_ALREADY_RUN.txt` guards the script |
| `REGIME` | recent_2025 | `config.py` | frozen | 2020–2023 is a separate regime |

## 2. Data — changing one means a new dataset version

Current dataset: `Storey1_hourly_v1.1`, built from frozen source `v1.0`.

| Parameter | Value | Where | Status | What it controls |
|---|---|---|---|---|
| `THRESHOLD` | 30 readings/hour | `config.py` | **open** | Minimum minute-readings for an hour to be valid. **This one parameter excluded 8 of 16 circuits.** See §4 |
| `ELIGIBILITY_SHARE` | 0.90 | `config.py` | **open** | Share of valid hours a circuit needs in validation and test |
| `ENERGY_MAX_GAP` | 15 min | `config.py` | frozen | Outage catch-up guard: an hour containing a reading whose preceding gap exceeds this is invalid |
| `ENERGY_TAIL_MAX` | 5 min | `config.py` | frozen | Pre-outage guard: energy booked into a later catch-up row |
| `MAX_GAP` | 5 min | `config.py` | frozen | How long a W/I reading "holds" |
| `MIN_COVERAGE_MIN` | 30 min | `config.py` | frozen | Minutes of coverage needed for a valid hourly W/I mean |
| `REGIME_CUT_UTC` | 2024-01-01 | `config.py` | frozen | Boundary between the hourly and minute regimes |
| `HOLIDAY_COUNTRY` / `SUBDIV` | ES / MD | `config.py` | frozen | Holiday calendar. No holiday falls in the 2025 window |
| UPM academic calendar | not used | `upm_calendar.xlsx` | **open** | In the repository, never wired in |
| Weather variables | not used | `S1-B2 Data *.csv` | **open** | Madrid daily data in the repository. The backlog feedback calls these a Must |
| `DERIVED_VERSION` | 1.1 | `config.py` | frozen | Bump on any change above |

## 3. Model — tuned on validation

Chosen 27 October, scoring **all 16 circuits**, confirmed on three rolling-origin folds.
Method in §5.

| Parameter | Searched | Chosen | Status | Notes |
|---|---|---|---|---|
| `criterion` | squared_error, absolute_error | **absolute_error** | tuned | Re-tested under the all-16 objective: wins by 12–16 % at every horizon |
| mode | pooled, per_series | **pooled** | tuned | Won at every horizon |
| Circuit identity | with, without | **without (design B)** | decided | Same accuracy on unseen circuits (0.3835 vs 0.3857), one fewer parameter, nothing special happens when a circuit is added later |
| `max_depth` | 4, 6, 8, 12, None | **12** (+1h) · **4** (+6h, day-ahead) | tuned | Partly redundant with leaf size: at leaf 60, depth 12 and unlimited score identically to five decimals because trees never get that deep |
| `min_samples_leaf` | 10, 30, 60, 100, 150, 250, 400, 600, 900, 1400 | **100** (+1h) · **250** (+6h, day-ahead) | tuned | Interior optimum, checked in both directions. At the long horizons the score improves to 250 then degrades |
| `max_features` | 0.33, 0.5, 1.0 | **1.0** (+1h) · **0.5** (+6h, day-ahead) | tuned | Irrelevant at +1h, matters at the long horizons |
| `n_estimators` | 100 vs 300 compared | 300 | frozen | A compute budget, not a hyperparameter. Searching at 100 gives an identical ranking and scores within 0.15 %, three times faster |
| `bootstrap` | — | True | frozen | Required for the bagging effect |
| `random_state` / `SEED` | — | 0 | frozen | Seed-to-seed sd is 0.1–0.2 % of the score |
| Training set | — | the 8 clean NE/NW circuits | decided 27 Oct | Predicts all 16. This is the "logical, explained, documented" choice the data owner asked for |
| Features | — | 15, from `task8_model.FEATURES` | frozen | Shared with the GBM and linear model so the comparison is like-for-like |

**The further ahead the forecast, the simpler the model must be.** At +1h the best model has
depth 12 and sees every feature at each split. At day-ahead it has depth 4 with at least 250
samples per leaf — about 16 leaves over 5,665 rows, barely more than a lookup table. The saved
models show it directly: 1,222 KB at +1h against 364 KB at day-ahead.

## 4. Open parameters needing a team decision

**`SELECTION_METRIC`.** `mean_scaled_MAE` divides each circuit's error by its own training
mean, so every circuit counts equally. `NW|Hand Dryer` averages 0.9 Wh/h and contributes
41–44 % of the score; `NW|Plugs & Sockets` at 563 Wh/h contributes 19–21 %. In an earlier round
this chose a different winner than an energy-weighted metric did. Current practice: select on
`mean_scaled_MAE` so the numbers stay comparable with the other models, and report WAPE
alongside. Task 3 should fix one definition.

**`THRESHOLD` = 30 and `ELIGIBILITY_SHARE` = 0.90.** Together these excluded SE and SW — half
the floor. Measured since:

- SE and SW sample more slowly than NE and NW, and the gap widens during working hours: NE/NW
  hold 50 readings per hour all day, SE drops to 30 at midday, SW to 25.
- Their gaps stay short: median longest gap 12–13 min in the hours that fail, against 90 min
  for the rare NE/NW failures, which are genuine outages.
- `Er` is cumulative, so short gaps should not lose energy. A rule on longest gap instead of
  reading count moves SE from 76.3 % to 90.1 % valid hours and SW from 74.7 % to 89.0 %.
- Readings inconsistent with their own power channel follow circuits, not zones:
  `SE|Plugs & Sockets` 13.6 %, `NE|HVAC` 4.6 % (a circuit we keep), `SE|HVAC` 0.0 %,
  `SW|Plugs & Sockets` 0.0 %.

Proposed for Sprint 4, **not** this sprint: replace the count rule with a gap rule, and apply
any circuit-level exclusion uniformly across all 16. Changing it now rebuilds the dataset and
forces every frozen model in the project to re-run.

## 5. How the model parameters were chosen

Four stages, because one number from one week is not evidence.

1. **Grid search** — 60 configurations per horizon, scored on all 16 circuits.
2. **Seed repetition** — leading configurations re-run across 5 seeds. Seed noise came out at
   0.1–0.2 % of the score against top-6 spreads of 0.6–2.7 %, so most of those gaps are real,
   but not all.
3. **One-standard-error rule** — among configurations within one standard error of the best,
   take the simplest. At +1h only two qualified, and they are the same model; at day-ahead only
   one did.
4. **Rolling-origin confirmation** — three expanding-window folds inside the training period
   (fit 19 Aug–31 Aug, 19 Aug–7 Sep, 19 Aug–14 Sep; score the following week each time). The
   official validation week is never fitted on, and the test week was untouched until step 4.

### A trap this caught, worth copying

The folds first **reversed** the ranking at +6h and day-ahead — the configuration chosen on the
official week came last across the folds, a clean inversion.

The cause was not the model. `min_samples_leaf` is an absolute count, and the folds train on
2,007–4,553 rows against 5,653 for the real model, so a leaf of 250 is 12.5 % of fold 1 but
4.4 % of the full training set. The folds were penalising large leaves for a reason unrelated
to forecasting. Re-running with the leaf expressed as a **fraction of training rows** removed
the inversion completely, and the folds then agreed with the official week at every horizon.

**If you compare across training windows of different sizes, express every size-dependent
parameter relative to the data — otherwise the comparison measures the window, not the model.**
