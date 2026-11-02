# Linear model — test errors by hour of day, and the weight of two known events

Post-hoc description of the test results Mert published in `model1_LinearRegression_all16/`. **Nothing is tuned or
changed here**, and no model decision should be taken from it (sprint rule 3). It fills section 9 of
`Analysis Linear Model.pdf` (hour-of-day analysis) and gives numbers for the teacher's request to explain the
validation -> test jump.

Run from the repo root: `python docs/linear_error_by_hour/analysis_linear_by_hour.py`. It first reproduces the 16-circuit
test scores of Mert's README (0.613 / 0.831 / 0.838) and stops if they differ. Metric = the team's: per circuit
MAE / circuit training mean, then the mean over circuits.

## 1. How much of the test error comes from two events

Events (target day, UTC): NE|HVAC on 3 Oct and NW|Emerg. Lighting on 5 Oct. Together they are 48 scored hours per
horizon, 3.6 % of the 1 344 hours of the 8 circuits the model was trained on.

| Horizon | 16 circuits | trained 8 | unseen SE/SW 8 | trained 8 without the 2 days | 16 without the 2 days | validation (Mert, 16 circuits) |
|---|---|---|---|---|---|---|
| +1h | 0.613 | 0.907 | 0.319 | 0.323 | 0.321 | 0.340 |
| +6h | 0.831 | 1.289 | 0.373 | 0.583 | 0.478 | 0.392 |
| day-ahead | 0.838 | 1.297 | 0.379 | 0.595 | 0.487 | 0.395 |

- Those 48 hours produce **57-66 % of the whole error of the 8 trained circuits** (66 % at +1h, 57 % at +6h and day-ahead).
- Without them, the 16-circuit test score at +1h (0.321) is close to validation (0.340). At +6h and day-ahead it stays
  about 0.09 above validation (0.478 vs 0.392; 0.487 vs 0.395): the events explain most, not all, of the gap.
- The 16-circuit average hides two groups: the 8 trained circuits (0.907 at +1h) and the 8 unseen SE/SW circuits
  (0.319), which have only 35-89 % valid test hours. A low SE/SW score is not evidence that the model transfers well.

## 2. Error by Madrid hour of day (8 trained circuits, scaled MAE)

| Hours (Madrid) | +1h all | +1h without events | +6h all | +6h without events | day-ahead all | day-ahead without events |
|---|---|---|---|---|---|---|
| 00-05 | 0.513 | 0.447 | 0.533 | 0.469 | 0.531 | 0.472 |
| 06-11 | 1.343 | 0.319 | 2.010 | 0.737 | 2.003 | 0.744 |
| 12-17 | 1.348 | 0.318 | 2.059 | 0.786 | 2.078 | 0.804 |
| 18-23 | 0.425 | 0.207 | 0.554 | 0.340 | 0.576 | 0.360 |

- With the events, the mornings and afternoons (06-17 h) look 3-4 times worse than nights and evenings. That is the
  two events, not a daily rhythm: without them, at +1h the daytime blocks (0.32) are no worse than the night block (0.45).
- Without the events, the weakest single hours at +1h are 00 h and 01 h (0.93, 0.89) and 15 h (0.52); the best are
  10 h (0.13), 04 h and 16 h. At +6h and day-ahead the daytime blocks (06-17 h) are the hardest (0.74-0.80), the evening
  the easiest (0.34-0.36). Per-hour values: `by_hour.csv`; per block: `by_block.csv`; first table: `summary.csv`.

## Limits
- **Descriptive, one test week.** One week, two events: the shares above would change with another week.
- **Events are defined by the team's notes**, not detected here. Dropping them compares different hour sets.
- **Validation vs test is not like for like**: different weeks, and the settings were chosen on validation.
- Scale of each circuit = MAE / scaled MAE read from Mert's per-circuit file (one value per circuit and horizon).
- Dataset v1.1 as used by Mert; not the v1.2/v1.3 framework.
- Written with the help of Claude (Anthropic); submitted by Maxime (mlestrat).
