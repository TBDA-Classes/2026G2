# Sprint 4 — Task 1: Model Diagnosis

## Purpose

This task investigates the errors of **Blend v1.3**, the forecasting model selected at the end of Sprint 3.

The objective is to understand where and when the model performs poorly, examine the data conditions associated with those errors, and identify a small number of issues to investigate during Sprint 4.

The analysis covers hourly energy forecasts for 16 electrical circuits across four building zones — NE, NW, SE and SW — at three forecasting horizons: +1 h, +6 h and day-ahead.

## Organisation of the work

The diagnosis is divided into three complementary contributions.

| Part | Main question | Work carried out |
|---|---|---|
| **1 — Performance analysis** | Where does the model make errors? | Calculate MAE, RMSE and valid observation counts by zone, circuit and horizon. Identify the worst-performing cases. |
| **2 — Temporal analysis** | When and how does the model make errors? | Examine hourly patterns, night versus other hours, weekdays versus weekends, and overprediction and underprediction. Investigate NW Plugs & Sockets and SE Lighting episodes. |
| **3 — Data conditions and possible explanations** | Which data conditions accompany the errors? | Examine training and validation coverage, missing or reconstructed measurements, data quality and changes in consumption levels. Separate evidence from hypotheses and outstanding checks. |

## Data and evaluation approach

The Part 1 and Part 2 use the saved Blend v1.3 validation predictions from Sprint 3 Task 6, covering 22–28 September 2025 in UTC.

Both analyse available actual/prediction pairs and exclude missing actual values without replacing them with zero. Part 2 converts target timestamps to Europe/Madrid for calendar-based analysis.

Part 3 combines validation results with coverage and data-quality evidence. Previously reported test results are identified separately and used as context.

Some Part 3 tables use the common observation mask from the Task 6 model comparison. Their scores and observation counts are therefore not directly interchangeable with the available-pair analyses in Parts 1 and 2. Night-time definitions also differ between some analyses and are documented in the reports.

This task analyses existing forecasts. It does not retrain the model or change its parameters or Blend weights.

## Main findings

- **NW Plugs & Sockets** is the largest contributor to absolute validation error, with recurring night-time underprediction.
- **SE Lighting** is another major contributor, including large afternoon misses concentrated on specific dates.
- Differences in observation coverage and consumption levels need to be considered when interpreting circuit-level results.
- Operational explanations remain hypotheses until supported by data-quality checks or confirmation from the data owner.

The detailed evidence, numerical results and limitations are provided in the individual contributions.

## Files and reading order

1. **Part 1 report:** performance tables and cases requiring investigation.
2. **Part 2 report:** temporal patterns, supporting tables and annotated figures.
3. **Part 3 report:** data conditions, possible explanations and outstanding checks.
4. **CONCLUSIONS.md:** shared conclusions, investigation priorities and outstanding checks from the three contributions.
