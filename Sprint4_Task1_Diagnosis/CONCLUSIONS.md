# Sprint 4 — Task 1: Shared conclusions and investigation priorities

**Model:** Blend v1.3  
**Scope:** Revised Part 1 performance analysis, Part 2 temporal analysis and Part 3 data conditions  
**Status:** Proposed shared conclusions for review by the three contributors

## 1. What the three contributions establish together

The diagnosis supports concentrating the next investigations on **NW Plugs & Sockets** and **SE Lighting**, while checking data validity and coverage before choosing model changes. The three contributions explain different aspects of these priorities: Part 1 measures the size and location of errors, Part 2 identifies their timing and recurrence, and Part 3 examines the associated data conditions and possible explanations.

| Shared conclusion | Evidence brought together | Implication for Sprint 4 |
|---|---|---|
| **NW Plugs & Sockets is the first absolute-error priority.** | Part 1 ranks it first by MAE and RMSE at every horizon. Part 2 identifies recurring night-time underprediction, especially at +6 h and day-ahead. Part 3 reports increased consumption relative to training. | Investigate whether recent elevated loads are insufficiently represented in the forecast inputs or training history, after checking source quality. The operational cause remains unconfirmed. |
| **SE Lighting needs targeted episode analysis.** | Part 1 ranks it second by MAE and RMSE at every horizon. Part 2 locates major afternoon misses on 22 and 24 September. Part 3 reports consumption-level changes and examines energy and power availability. | Check the measurements and forecast input windows for those episodes before deciding whether to address preprocessing, model responsiveness or both. |
| **Data availability affects how confidently circuit scores can be interpreted.** | Parts 1 and 2 report valid-pair counts. Part 3 distinguishes raw observations, valid hourly targets and hours shared by competing models, particularly for SE Plugs & Sockets. | Diagnose losses of valid hours separately from forecast error. Limited coverage alone does not demonstrate the cause of poor performance. |
| **The largest errors are not equally severe at every time or horizon.** | Part 1 provides separate horizon rankings. Part 2 distinguishes recurring NW night errors from concentrated SE afternoon episodes. Part 3 identifies different consumption and quality conditions across circuits. | Define improvements around a specific circuit, horizon and observed failure pattern, and check their effects elsewhere. |
| **Calendar and operational explanations remain provisional.** | Part 2 observes one weekend with higher NW Plugs errors. Part 3 retains checks on schedules, the academic calendar and building events. | Treat weekend, occupancy, equipment and schedule explanations as hypotheses until supported by additional evidence. |

In the available-pair validation analysis, NW Plugs & Sockets and SE Lighting together contribute **75.9% of the pooled day-ahead absolute-error sum**. This supports prioritising those circuits for investigation; it is not a percentage prediction error or an achievable improvement estimate.

## 2. Investigation priorities

The priorities below are proposals arising from the diagnosis. They do not imply that the checks or model changes have already been completed.

| Priority | Investigation | Immediate action | Decision it will support |
|---|---|---|---|
| **High** | NW Plugs & Sockets night underprediction | Compare the elevated-load episodes with training history, recent input values and quality records; ask the data owner about changes in overnight operation. | Whether to test features or a training strategy that respond faster to recent consumption levels. |
| **High** | SE Lighting afternoon misses | Inspect flags, energy reconstruction, missing power readings and forecast inputs for 15:00–16:00 Madrid time on 22 and 24 September. | Whether the observed misses require a data correction, a modelling experiment, or further operational evidence. |
| **Medium** | SE Plugs & Sockets coverage | Trace which hours are removed by hourly validity rules and which are lost through the common comparison mask; confirm training eligibility. | Which observations and circuit-level estimates can support a meaningful experiment. |
| **Secondary** | Other lighting and HVAC cases | Review the remaining Part 1 shortlist, including SW Lighting at +1 h, alongside Part 3's NW Lighting and HVAC findings. | Whether further targeted tests are justified, including the outdoor-temperature experiment under Task 2. |

## 3. Checks before model experiments

Three checks remain relevant before selecting a targeted model experiment:

- **SE Lighting measurement reliability:** inspect quality flags, energy reconstruction and available power readings for the afternoon episodes. Agreement between energy and power where both exist does not confirm every episode where measurements are missing or reconstructed.
- **Operational changes:** ask the data owner whether overnight loads or lighting schedules changed on NW Plugs & Sockets and SE Lighting. Consumption shifts are observed; their physical causes remain unconfirmed.
- **Validity rules and training eligibility:** clarify the remaining questions about dataset v1.2 exclusions and circuit eligibility, particularly for SE Plugs & Sockets, using the preprocessing rules and training configuration.

These checks help distinguish a data issue from a forecasting weakness and define an appropriate experiment.

### Methodological note

Parts 1 and 2 use Blend's available validation pairs; some Part 3 tables use the common hours scored across models. Part 2 defines night as 00:00–05:59 in Europe/Madrid, while some analyses cited in Part 3 use a different window. Scores and counts must retain their sample and time definitions; direct comparisons require aligned definitions. Part 3's additional calculations have not all been independently reproduced during consolidation.

## 4. What Task 1 provides to the next stage

Task 1 provides an evidence-based shortlist of weaknesses and a set of checks needed to interpret them. The next step is to resolve the priority data and operational questions, then define a small number of documented experiments against frozen Blend v1.3.

Each experiment should state the issue addressed, proposed change, data available at forecast issue time, evaluation sample and results by relevant horizon and circuit. Comparisons must use the same eligible observations and check whether improvements on a priority case introduce losses elsewhere.

The diagnosis primarily concerns the validation week of 22–28 September 2025 UTC. It is exploratory because this week has already supported model selection. Previously inspected test results in Part 3 remain context and must not guide new parameter, feature or weight choices. A further independent evaluation requires an agreed protocol and suitable data.

The supported conclusion is that **targeted investigation is justified**. Physical causes, the effectiveness of proposed improvements and any numerical reduction in error remain to be established. Detailed methods, tables and figures remain in the three individual contributions.
