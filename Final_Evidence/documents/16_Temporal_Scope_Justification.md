# Why retain the recent-period model? Temporal scope and its evidential limits

**Maria Francesca Casillo · TBDA Group 2 · 21 November 2026**

## 1. Decision being supported

For the final delivery, retain the frozen Blend v1.3 built and selected within the recent 2025 regime. Present its evaluation as evidence about late summer and early autumn at CeDInt Storey 1, not as annual or winter validation.

Two decisions need separate explanations: **which regime to model**, and **where to place the chronological split inside that regime**. The evidence supports a controlled, reproducible recent-period study. It does not establish that excluding history maximises forecasting accuracy, or that these exact cut-offs are optimal.

The professor's reply of 17 November allows the team to choose its approach provided it can validate it adequately, support conclusions with evidence and present limitations openly. This is permission to defend a bounded scope, not evidence that the chosen scope is scientifically superior.

## 2. Evidence provenance and chronology

| Source | What it supports | What it does not establish |
|---|---|---|
| Modelling Problem Specification, §§2, 5, 7–8 | Treat historical and recent data as distinct regimes; no counter differencing across the gap; justify any combination using validation evidence | A prohibition on historical training or a requirement to use 2025 only |
| Sprint 2 `task6.pdf`, §4; `task6_split_design.py` | Recent 2025 as the main evaluation case; exact date proposal after coverage profiling; exclusion of the partial first day and post-test data from the first protocol | An optimisation of split dates or a minimum sufficient training duration |
| Model `config.py` and hourly dataset META | Exact UTC boundaries, regime filter and implementation parameters | A causal explanation of changes between years |
| `DECISIONS_v1.2.md`, `PROTOCOL_NOTE_v1.2.md` | Uniform validity and training-eligibility rules; fixed splits across later versions; disclosure of earlier test use | A completely untouched test throughout project development |
| Final Evidence documents 08 and 14, dated 17–18 November | Retrospective rationale and exploratory historical-profile evidence | Proof that all later arguments were the original reasons for choosing the dates |
| This package's script and CSVs | Recomputed counts, energy provenance and explicitly masked profile scores | A historical-plus-recent Blend comparison or winter performance |

Original historical-regime analyses were prepared by the authors credited in Final Evidence. This contribution audits and qualifies their use in the temporal decision.

## 3. What data were available, and what the model used

Cleaned data include historical readings from April 2020 to **28 February 2023, 23:00 UTC**, and recent readings starting **18 August 2025, 18:43 UTC**. The observed gap between the last historical and first recent record is **901.8215 days**. Recent measurements end on **13 October 2025, 14:00 UTC**. The recent grid spans 1,341 hours for each of 16 circuits.

Historical data were cleaned and later analysed; they were not included in the final Blend's local training and selection. SW RACK exists historically but has no recent data, so historical and recent inventories are not identical.

| Scope, UTC; last hour included | Calendar hours per circuit | Circuit-hour rows, all 16 | Valid energy pairs | Valid share |
|---|---:|---:|---:|---:|
| Training: 19 Aug 00:00–21 Sep 23:00 | 816 | 13,056 | 10,297 | 78.87% |
| Validation: 22 Sep 00:00–28 Sep 23:00 | 168 | 2,688 | 2,413 | 89.77% |
| Test: 29 Sep 00:00–5 Oct 23:00 | 168 | 2,688 | 2,316 | 86.16% |
| Before training: 18 Aug 18:00–23:00 | 6 | 96 | 88 | 91.67% |
| After test: 6 Oct 00:00–13 Oct 14:00 | 183 | 2,928 | 2,233 | 76.26% |

Source: `Final_Evidence/analysis/temporal_scope/split_validation_summary.csv`. Validity here is the frozen v1.2 `energy_Wh` mask. These are not fitted-model sample sizes or the official Task 6 common-model mask (1,911 test pairs per horizon). Training eligibility is a separate decision: 15 circuits are admitted; SE Plugs & Sockets has only 152 valid training hours and is handled as cold-start for forecasting.

The training window is **34 days**, not five complete weeks. Validation and test each contain 120 weekday and 48 weekend hours under UTC. Boundaries at 00:00 UTC correspond to **02:00 Madrid** in this window: do not describe them as midnight-to-midnight Madrid weeks. Day-ahead issue times remain a separate Madrid-local convention.

## 4. Why a recent-only regime is defensible

### 4.1 A measurement regime that the existing pipeline explicitly handles

Historical rows typically arrive hourly; the median positive spacing is 60 minutes. Recent rows typically arrive at minute spacing. The final pipeline explicitly selects the recent regime and constructs hourly targets with gap, end-of-hour and energy–power consistency rules.

Both cleaned periods use a field named `energy_Wh` with active-energy semantics, supported by the cleaning documentation. Identical units alone do not establish identical measurement quality or statistical behaviour. The cleaned target may come from a counter difference, a power-weighted allocation (`spread`) or a power fallback. Recomputed source-row shares differ:

| Energy source | Historical | Recent |
|---|---:|---:|
| Counter | 80.92% | 45.55% |
| Spread | 9.27% | 50.92% |
| Power | 9.78% | 3.51% |

Source: `energy_source_summary.csv`; percentages are shares of rows, not energy or information. These differences require harmonisation and checks before historical rows are treated as interchangeable training observations. The hourly gap rule of the minute-level pipeline cannot simply be applied to hourly history: a normal 60-minute historical spacing would exceed the 15-minute guard.

**Implication:** using the existing validated recent-period representation gives an internally specified comparison. It does not prove that a separate, appropriate historical representation could not improve the model. The archive and META integrity check does not independently validate all upstream cleaning assumptions.

### 4.2 Historical levels and profiles require a transferability check

The team's descriptive tables show substantial circuit-level changes, including within the same August–October season across years. This reduces, but does not eliminate, seasonal confounding. Differences may reflect real operations, occupancy, sampling, counter processing, missingness or several factors together. Descriptive shifts do not identify their cause and are not a formal structural-break test.

The long gap means continuity cannot be assumed or created by forward filling. Historical training remains possible, but needs explicit regime handling, comparable targets, restarted lag/rolling contexts and validation of its added value. The specification requires that evidence; the team did not complete such an experiment for Blend.

### 4.3 A stable evaluation contract

Keeping the documented split across later model versions allows comparisons under fixed temporal targets. It avoids replacing the reported experiment with a new training population and then treating previous model selection and uncertainty estimates as automatically applicable.

For the final delivery, retaining the frozen model therefore preserves the experiment that has actually been evaluated and reproduced. Available time is a feasibility consideration, not evidence that history is harmful. A combined model could be a better model; it would need its own controlled development and evaluation.

## 5. Why these particular windows?

- **Start on 19 August:** the available recent data begin partway through 18 August. Starting at the next complete UTC day avoids a partial common training day. This is a documented design choice, not proof that the six earlier hours have no value.
- **34 training days:** most of the initial evaluation span is allocated to fitting while retaining two consecutive full UTC weeks for selection and evaluation. This provides several weekly repetitions but is short and partly covers August. There is no demonstrated statistical minimum of 34 days or five weeks, and no learning-curve study proving sufficiency.
- **One week each for validation and test:** each window contains all weekdays and a weekend under the fixed UTC convention. Chronological order represents forecasting later observations from earlier information. A random row split would not represent that deployment question and can allow future information into fitting.
- **No overlapping target windows:** configuration literals, META and observed split labels agree. This verifies the split structure, not all possible feature leakage.
- **Post-test tail:** Task 6 explicitly left it outside the first protocol for possible later analysis. It contains 183 hours, so it is not defensible to say it was excluded because it is shorter than a week. Nor is it defensible to say it was never examined: Dash documents live-engine forecasts for that period. It may support a separately labelled frozen-model diagnostic, provided exposure and prior use are disclosed. It cannot prove winter performance.

No alternative split-date search or rolling-origin study establishes that 22 September and 29 September are optimal boundaries. Their defensibility is consistency, weekly evaluation structure and documented chronology, with explicit uncertainty due to the small evaluation sample.

## 6. Evidence against blanket exclusion of history

The existing exploratory harness uses weekday × UTC-hour median profiles under different training histories. This package recomputes four alternatives on **the same 2,316 measurable test circuit-hours**, using the existing Blend test file's actuals. There are 2,688 possible target pairs; the remaining 372 lack actual values and are not scored.

| Profile training data | Pooled MAE, Wh | Mean of circuit MAEs, Wh |
|---|---:|---:|
| Recent training window | 57.16 | 55.28 |
| All historical seasons | 40.39 | 37.30 |
| Historical August–October | 38.62 | 35.40 |
| Recent + historical August–October | 38.17 | 35.13 |

Sources: `historical_profile_check.csv`; original method in `Final_Evidence/scripts/regime_comparison.py`.

Pooled MAE weights each valid pair equally. The mean of circuit MAEs weights each circuit equally. These differ because valid counts differ. Without SE Plugs & Sockets, recent-only versus combined scores are **32.61 versus 33.08 Wh** by mean circuit MAE (**35.58 versus 36.40 Wh** pooled). The large overall gain is therefore concentrated in the circuit excluded from Blend's training eligibility.

Three limits matter:

1. Profile training uses cleaned hourly sums whose constituent energy readings are all nonmissing. This is **not the final v1.2 gap/consistency validity policy**. In particular, the raw recent profile includes SE Plugs training values that the final pipeline largely invalidates. A diagnostic for Blend would first need compatible validity and eligibility rules.
2. The historical comparison was made after the test week had been inspected. It is retrospective evidence, not independent model-selection evidence. It is not used here to choose a new training period.
3. This is not a retrained combined Blend. Its scores must not be directly compared with Blend's official MAE on 1,911 common-model pairs to assert superiority of either approach.

**Conclusion:** history may help; no blanket rejection is justified. Conversely, this profile experiment is insufficient to establish that adding history would improve the frozen Blend under its actual protocol.

## 7. Winter: the limitation that the decision cannot remove

The recent training, validation and test contain no local winter observations. Historical winter records exist; they are separated from the current regime by years and cannot automatically validate current winter operation.

Heating, lighting schedules, occupancy and weather may differ in winter. It is not established that every monitored electrical circuit increases in winter or that the monitored HVAC circuits capture the building's complete heating demand. Higher total consumption alone is not the only risk: operating patterns and the relation between inputs and targets may change.

The temperature experiment on the same late-summer/autumn data does not establish that weather is irrelevant in winter. Chronos being pretrained externally does not substitute for validation on this building's winter measurements. Aggregate error confidence intervals and calibrated prediction bands within the evaluation window likewise do not establish annual coverage.

Thus the product may be presented as a demonstrated forecasting and decision-support prototype in the evaluated regime. Year-round accuracy, winter alert reliability and annual savings cannot be claimed from this evidence.

## 8. Decision summary: strengths, limitations and next validation

| Aspect | Strength supporting the decision | Limitation or trade-off |
|---|---|---|
| **Data preparation** | The recent-period pipeline defines hourly aggregation and validity rules explicitly. | Historical data require a compatible preparation process before integration. |
| **Temporal continuity** | Training and evaluation stay within the recent campaign, avoiding artificial continuity across the approximately 902-day gap. | Potentially useful historical information is excluded from local training. |
| **Evaluation design** | Fixed chronological windows support traceable comparisons and include weekdays and weekends. | Only one validation week and one test week; the exact boundaries are not proven optimal. |
| **Training history** | The 34-day window provides several repetitions of weekly behaviour. | Limited history, partly covering August, may not represent other operating conditions. |
| **Seasonal coverage** | Conclusions can be clearly bounded to the evaluated late-summer and early-autumn period. | Winter and annual performance remain unvalidated. |
| **Historical-data evidence** | The exploratory comparison identifies where historical information may help. | It does not establish whether historical training would improve Blend. |
| **Final delivery** | Retaining the frozen model preserves the evaluated, reproducible experiment. | Reproducibility does not demonstrate that recent-only training is the best possible choice. |

The team retains the frozen recent-only Blend for this delivery, with historical-data integration as a substantive research extension. A proper extension should predefine alternatives and validity rules, compare recent-only and combined training on identical validation targets, prevent gap-crossing features and fit all transforms on training only. Any new choice needs a genuinely later, uninspected evaluation period where available; the previously used test week must not be relabelled untouched. Evaluate multiple chronological windows and a local heating season before claiming annual transferability.

## 9. Reporting clarifications and limitations

- The v1.3 choice was frozen before its reported test run, according to project records. The same test week had already been used on v1.1 by earlier models; `PROTOCOL_NOTE_v1.2.md` discloses this. Dataset checks do not establish Git chronology or eliminate indirect influence from earlier results.
- All available recent data (18 Aug–13 Oct) are distinct from the actual fitting/selection/testing windows (19 Aug–5 Oct).
- The training window contains 34 days. The 189 outside hours comprise 183 hours after the test and six initial hours before training.
- The historical-profile target grid contains 2,688 circuit-hours; only 2,316 have actual values and contribute to error. The supplied script makes this denominator explicit.
- Macro circuit MAE and pooled MAE use different weighting and are reported separately.
- Retrospective data differences justify caution; they do not establish that equipment changed or that the original period choice was optimal.

Reproduction instructions and file index: [16a_Temporal_Scope_Reproduction.md](16a_Temporal_Scope_Reproduction.md).
