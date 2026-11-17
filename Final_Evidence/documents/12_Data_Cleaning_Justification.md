# Data Cleaning — what we did, why, and what it costs

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Émile (main author) · Edoardo (co-author of the cleaning notebook) · Claude (co-author of this document)
**Notebook:** `Sensor_data_cleaning_Storey1_v4.ipynb` (run 7 Oct 2026, run IDs in `run_config_<ZONE>.csv`)
**Outputs:** `CLEAN DATA all zones.zip` — per zone: `clean_Storey1_<ZONE>_CLEAN_DATA.csv`, `audit_<ZONE>.csv.gz`, `correction_log_<ZONE>.csv`, `rules_<ZONE>.csv`, `counter_events_<ZONE>.csv`, `sensor_quality_<ZONE>.csv`, `run_config_<ZONE>.csv`
**Related:** `12a_Cleaning_Checks.md` (impact of the flagged sensors on results), `08_Scope_Decision_2025_Only.md` (why the model uses 2025 only), `TBDA_v1.3_ChronosGBM_29-10/DECISIONS_v1.2.md` (hourly validity rules D1–D5)

> **Reading note.** Every cleaning number in this document was recomputed from the output files listed above. Numbers on time handling (C10) and hourly rules (section 6) come from the documents cited there. Where the rule descriptions written inside the notebook give a different number, the output files are used and the difference is listed in section 7.

## 1. Summary

- The cleaning turns 4 Excel workbooks (18 sheets, 12 columns) into one clean table per zone: **1,273,456 rows** (405,382 historical 2020–2023, 868,074 from 2025), **one row per original timestamp**. Rows are only removed when a timestamp is duplicated or unreadable.
- **24 rules**, each with a written reason, the alternative we rejected and the evidence (`rules_<ZONE>.csv`). **3,023,497 individual values** were changed or flagged, and every one is in the audit file with its old and new value.
- The forecasting target **`energy_Wh` is built from the active energy counter (Er)**, not from power × time. Each row says where its value came from: 81 % straight from the counter in 2020–23, 46 % in 2025, where the counter difference is more often shared across a gap.
- Principle: **a wrong value becomes empty, not invented.** Values are only rebuilt where the risk is small (sign error, short gap in a power reading).
- The cleaning **flags but does not drop** doubtful sensors. Five 2025 circuits were flagged; `12a_Cleaning_Checks.md` shows removing them changes none of our conclusions.

## 2. The data we received

| Item | Value |
|---|---|
| Files | 4 workbooks (NE, NW, SE, SW), 18 sheets, one per circuit, same 12 columns |
| Columns | `Timestamp`, `W`, `I`, `Ea`, `Er`, `Pa`, `E Device type`, `Number of Edevices`, `Lum`, `Hum`, `Temp`, `Pres` |
| Periods | 2 Apr 2020 – 28 Feb 2023 (1 reading per hour) and 18 Aug – 13 Oct 2025 (about 1 reading per minute), about 900 days apart |
| Meters per sheet | 1 (RACK) to 92 (SW Lighting): **each sheet is the sum of many meters** |
| Main problems | negative power and counters, zeros used for missing values, counters that drop and recover, platform resets, one meter wired backwards, impossible values (Pa = 21 million W, 1,411 °C), environmental sensors absent in one zone |

The sum over many meters is the key fact behind several rules: when some meters do not answer, the total drops for a while and comes back. That is not a real drop in consumption.

## 3. Principles

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **Invent nothing** | A wrong value becomes empty (NaN). Rebuilt only where the risk is small: a sign flip on a correct magnitude, or a short gap in power, current or climate (C8). |
| P2 | **Lose nothing silently** | One function (`Fixer.apply`) makes every change: it writes the new value, records the old one in the audit file and sets a flag bit in a `<column>_flags` column. Data and log cannot drift apart. |
| P3 | **Structure before statistics** | Sensors that were never connected and the backwards meter are fixed first, so every later threshold is computed on corrected values. |
| P4 | **Flag, don't decide for the modeller** | Doubtful but possible readings are flagged and kept (confirmed peaks, P > S rows, counter resets). Doubtful sensors get a verdict, not a deletion. |
| P5 | **Same meaning in both periods** | Windows and gaps are set in hours and converted to rows per period. Exception: the code never uses fewer than 3 rows, so in the hourly 2020–23 data short windows become 3 hours (C8). |

**Strength:** any value in the output can be traced to its rule and original value (`audit_<ZONE>.csv.gz`, `excel_row` column). **Weakness:** P1 leaves more empty values than filling would; the hourly validity rules downstream then decide which hours can be used (section 6).

## 4. Decisions

Format of each block: **Decision · Why · Evidence · Alternative rejected · Weakness.**

### C1 — What the columns mean, and which one we forecast

- **Decision.** `W` = active power (W), `Pa` = apparent power (VA), **`Er` = cumulative active energy (Wh)**, `Ea` = cumulative apparent energy (VAh). The target is the interval difference of `Er`.
- **Why.** The files give no units or definitions. The meaning had to be tested, because forecasting apparent instead of active energy would inflate every value by 1 / power factor.
- **Evidence.**
  - On the two single-meter circuits (RACK), Pa / I = 227.6 V (NW) and 231.4 V (SW): mains voltage, so Pa = V × I = apparent power.
  - The Er counter matches active power: implied power / W = 0.93–1.005 on the reliable sensors (`sensor_quality_<ZONE>.csv`).
  - Apparent energy runs at 1 / power factor of active energy: on NE HVAC (2020–23) ΔEa / ΔEr has a median of 4.63, i.e. a power factor of about 0.22.
  - W ≤ Pa holds on 99.26 % of clean rows (P ≤ S).
  - Matches the course slide "Apparent Energy (Ea), Active Energy (Er)".
- **Alternative rejected.** Our first notebook version (v1) read W as reactive and Pa as active power, and used the Ea difference as target. The team's data dictionary of 5 Oct read the names literally (Ea = active, Er = reactive). The tests above contradicted both, so v2 changed the target from Ea to Er. The earlier versions were drafts and never reached the repository: the only notebook ever committed is v4 (6 Oct), which already uses Er, so every model was trained on active energy. The dictionary was corrected on 17 Nov.
- **Weakness.** Not confirmed by CeDInt (open point in `10_Evidence_Map.md`). The units (W, Wh) are still assumptions.

### C2 — How `energy_Wh` is built

- **Decision.** `energy_Wh` = difference between two valid readings of `Er` in the same period. If readings in between are empty, the difference is **shared across them in proportion to power** (`spread`). Only where no counter difference exists (after a reset, at the start of a period) is it estimated as mean power × time (`power`), and only for gaps up to 6 h. Every row carries an `energy_source` label.
- **Why.** The counter is the meter's own measurement of energy. Power is a snapshot at one instant, so power × time misses everything between snapshots (a hand dryer running 30 s between two readings).
- **Evidence.** Share of rows by source:

  | Period | counter | spread | power | unknown |
  |---|---|---|---|---|
  | 2020–2023 | 80.9 % | 9.3 % | 9.8 % | 0.03 % |
  | 2025 | 45.6 % | 50.9 % | 3.5 % | 0.02 % |

  In 2025, `power` rows carry 4.0 % of total energy.

  The check comparing counter and power is **not circular**: it uses only rows where power took no part in building the value (`counter`), and it tests the median ratio (bias), not the scatter.
- **Alternative rejected.**
  - Power × time everywhere: simpler, but it ignores the meter's own energy count and misses short loads.
  - Leaving gaps empty: loses energy that the counter did record.
- **Weakness.**
  - In 2025, half the rows get a shared-out value. The hourly total is still the counter's total, but how energy is split *within* the gap follows power, which is an assumption.
  - `12a_Cleaning_Checks.md` (check B) shows this does not make the scored hours less accurate. It does reduce how many hours are usable.

### C3 — Counter dips caused by meters that do not answer (`counter_partial`, `partial_power`)

- **Decision.** If the counter drops and comes back to its level within 24 h, the readings in the dip are emptied. If power also falls below 60 % of its 3-hour neighbourhood in those rows, power, current and apparent power are emptied too.
- **Why.** A sheet is the sum of up to 92 meters. When some do not answer, the total drops by their share and recovers when they return. A counter cannot really go down.
- **Evidence.**
  - 740,046 counter values emptied, 96 % of them in 2025 (per-minute data has many more dropouts).
  - All 12 automated checks pass after cleaning, including "Ea and Er never decrease inside a period".
  - The power rule needs two independent columns to agree (counter dips **and** power dips), which is a stronger signal than either alone.
- **Alternative rejected.**
  - Taking the absolute difference: would invent huge consumption.
  - Interpolating: would hide the dropout instead of recording it.
- **Weakness.**
  - The 24 h window and 60 % ratio are judgment values and were not sensitivity-tested.
  - In 2025, most `spread` values come from these dips.

### C4 — Counter resets, jumps, spikes, and the two periods

- **Decision.**
  - A drop that never recovers is a **reset**: the value is kept as a new valid level, and the step across it is not counted as consumption.
  - A rise larger than the maximum power allows, confirmed by the next 10 readings, is a **jump**: kept, not counted.
  - An isolated value that the next readings do not confirm is a **spike**: emptied.
  - A time gap over 90 days starts a new **period**. No differences or interpolation are ever taken across a period boundary.
- **Why.**
  - Resets come from the platform restoring an old saved value: the reading is valid, the difference across it is not.
  - The 90-day limit sits above a real 37-day outage inside 2020–23 (NW Emerg. Lighting / HVAC, June 2021, as noted in the notebook) and far below the ~900-day pause between campaigns.
- **Evidence.**
  - 1,003 reset and 1,226 jump values, all listed with date in `counter_events_<ZONE>.csv`; 459 spikes emptied.
  - Resets hit **17 series at the same timestamp** (8 Aug 2021 13:00 UTC): the cause is the platform, not the meters.
  - The specification also says not to difference counters across the gap.
- **Alternative rejected.** Emptying resets and jumps would discard correct readings and break every later difference.
- **Weakness.** The jump/spike test depends on a margin (3 × maximum power) and a 10-reading confirmation, both judgment values.

### C5 — Negative power

- **Decision.**
  - **NW Emerg. Lighting**: the whole series is multiplied by −1 (median power negative, 99.5 % of W readings negative, counter running backwards).
  - Elsewhere, a negative W, Pa or I whose size is in the sensor's normal range gets its **absolute value** (240,251 values).
  - A negative value whose size is an extreme outlier (above Q3 + 3 IQR) is emptied (109 values).
  - Negative counters are emptied (41,056).
- **Why.** These circuits only consume. A whole series running backwards means the current clamp is fitted the wrong way round. An isolated negative of normal size is a sign error on a correct magnitude.
- **Evidence.**
  - Reversed meter: the whole series (86,686 rows) corrected instead of deleted.
  - **Effect on the target is very small.** In 2025, 9.4 % of rows have a sign-corrected W, but the target comes from the counter. Only 8,279 of those rows use power to build `energy_Wh`, which is **0.075 % of 2025 energy**. In `spread` rows, W only decides how a counter total is split, not the total.
- **Alternative rejected.**
  - Deleting the reversed meter: loses a whole circuit for a wiring fault.
  - Emptying every negative: discards correct magnitudes.
  - Treating negatives as real (capacitive) power: W is active power, and these loads do not generate.
- **Weakness.**
  - On a sheet that sums many meters, a negative total may come from **one backwards meter inside the sum**. The true total is then not simply the absolute value.
  - The rule is exact for a single meter and an approximation for sums. It matters for the power columns, not for the target. Largest counts: NW Hand Dryer, SW Lighting, SW Hand Dryer.

### C6 — Zeros that mean "missing"

- **Decision.**
  - If W, Pa, I, Ea and Er are all exactly 0 in a row, all five are emptied (70,695 values).
  - A counter at exactly 0 in mid-series is emptied (36,990).
  - A zero contradicted by another column is emptied (145,399): Pa = 0 while Ea rises, W = 0 while Er rises, or I = 0 while Pa > 5 W.
  - **SE Projector** is left out entirely: all electrical columns are 0 in all 61,689 rows.
- **Why.** A cumulative counter cannot return to 0. If energy was counted, the device was consuming. A meter that never moves in five years is disconnected, not switched off.
- **Evidence.** NE HVAC: 22,474 of its 25,012 historical rows (89.9 %) have I = 0 while Pa > 5 W, which looks like a current-resolution floor, not a reading.
- **Alternative rejected.** Keeping the zeros: the model would learn switch-offs that never happened, and averages would drop.
- **Weakness.** Real zeros (load off, counter not moving) are kept. The rule only removes zeros that another column contradicts, so a zero with nothing to contradict it stays even if it is a dropout.

### C7 — Impossible values and outliers

- **Decision.**
  - A power or current value over 1,000 × the sensor's typical size, or 20 × its 99.9th percentile, is emptied (2 values).
  - High values above Q3 + 3 IQR are **kept and flagged** if a second column confirms them (22,698), and emptied if nothing supports them (36,719).
  - Only high values are treated.
  - Rows where active power exceeds apparent power are flagged and left unchanged (13,500 values).
- **Why.**
  - Real peaks (a compressor starting) are the most informative moments for a consumption model.
  - A peak that current, power and the counter agree on is real; one column alone being extreme is a measurement error.
  - Low values are real nights and weekends.
- **Evidence.**
  - NW Plugs & Sockets, 5 Oct 2020 12:00: Pa = 21,190,380 for a circuit around 900 W.
  - k = 3 is the standard "far out" Tukey fence (k = 1.5 is the usual "outlier" fence).
- **Alternative rejected.**
  - Capping at the threshold (winsorising): invents a number and erases the difference between real peaks and errors.
  - A fixed 1.5 IQR: would remove many real peaks on cycling loads.
- **Weakness.**
  - The second "corrupted" value is NW Hand Dryer W = 2,752 W (31 Jan 2021). A hand dryer can really draw ~2.5 kW, so this one may have been a real reading. One value, no effect on results.
  - k = 3 was not sensitivity-tested.

### C8 — Filling short gaps

- **Decision.** Short gaps in Pa, W, I, Hum and Temp are filled linearly (506,432 values): up to 15 readings (15 minutes) in 2025 data, up to 3 readings in 2020–23 data. Counters, light level and presence are never interpolated. No filling across a period boundary.
- **Why.** Power and climate change continuously over minutes. Counters are handled by C2, which keeps the energy total exact. Light level jumps on and off. Presence is 0/1.
- **Alternative rejected.**
  - Longer gaps: would invent trends.
  - Model-based imputation: adds a model inside the data that the forecasting models would then partly learn.
- **Weakness.**
  - 15 minutes is a judgment value.
  - **The setting does not mean the same in both periods.** It is written as 15 minutes, but the code never uses fewer than 3 rows, so in the hourly 2020–23 data gaps of up to **3 hours** are filled (143,371 values, 83 % of them current `I`). The notebook's own description says 15 minutes in both periods; that is not what the code does.
  - Impact: none on the final model. These are power and current columns (not the target) in the historical period, which the model does not use. It matters if the historical data is used later.

### C9 — Environmental columns (Lum, Hum, Temp, Pres)

- **Decision.**
  - One environmental table per zone (the values are identical across sheets of a zone).
  - Zone NE has no environmental sensor (all four columns 0 in all 88,828 rows): emptied.
  - Hum and Temp both at 0 is a missing reading.
  - Temperature outside −10…60 °C is emptied.
  - Humidity more than 5 points from its 3-hour median is emptied.
  - `Pres` is treated as a 0/1 **presence** signal, not pressure.
- **Why.** 0 °C and 0 % humidity are impossible indoors.
- **Evidence.**
  - SW records up to **1,411 °C** on 1–7 Mar 2022 (140 readings): a contained sensor fault.
  - The −10 °C limit keeps the real cold of January 2021 (storm Filomena): 1,291 readings below 10 °C that month, minimum 3.8 °C.
  - Pres averages 0.00 at night and peaks around 11–12 h UTC: an occupancy curve.
- **Alternative rejected.** A narrow 10–35 °C band: would delete the real cold readings an energy model needs.
- **Weakness.**
  - Light-level maxima (4,603 NW, 11,027 SW) were not treated.
  - **None of the forecasting models uses these columns** (features are past energy and calendar only; weather comes from Open-Meteo, `Sprint4_Task2_Temperature`). Only the occupancy analysis of Sprint 4 uses `Pres`. The stakes of this part are low.

### C10 — Time (UTC and Madrid time)

*Task 1 and Task 2 of Sprint 2, done by teammates after the cleaning; summarised here because the cleaning output feeds them.*

- **Decision.** The original `Timestamp` is treated as **UTC** and kept as the key for sorting, differences and joins. A `timestamp_madrid` column (CET/CEST) is added for hour, weekday and holiday features.
- **Why.** Using local time as a key would create false duplicates in autumn and false gaps in spring at the clock changes.
- **Evidence.**
  - `Task2_Temporal_QA_compact.zip`: 0 invalid timestamps, 0 duplicates, 0 conversion mismatches.
  - 100 rows (50 pairs) share a Madrid wall-clock time at autumn clock changes but are different UTC instants, so they are not duplicates.
  - The historical data shows no clock-change jumps, consistent with UTC.
- **Weakness.** UTC is inferred from the data, not from system documentation. The clock change is not exercised in our 2025 test weeks (PB-16).

### C11 — Sensor verdicts and automated checks

- **Decision.**
  - Each sensor gets an energy verdict: `ok` if the counter's implied power is within ±10 % of W, `below_resolution` if median power is under 5 W (close to the 1 Wh counter step), `counter_biased` otherwise.
  - Sensors are never dropped automatically.
  - The run stops if any of 12 automated checks fails (the notes printed with them are information only).
- **Why.** Dropping is a modelling decision. The cleaning reports; the modeller decides.
- **Evidence.**
  - Verdicts for 2025: `counter_biased` for SW Lighting (0.707); `below_resolution` for NE HVAC, NW Hand Dryer, SE Emerg. Lighting and SW Hand Dryer.
  - All checks pass: one row per original timestamp; no duplicates; counters never decrease within a period; no negative power; humidity in (0, 100]; temperature in range; presence only 0/1; no infinite values.
- **Weakness.**
  - Nobody downstream read the verdicts; all 16 circuits were trained and scored alike.
  - `12a_Cleaning_Checks.md` measured the effect: conclusions unchanged, but the day-ahead selection margin of the Blend over Chronos relies on the flagged circuits.
  - For SW Lighting we cannot tell whether the counter or the power reading is wrong. That circuit also has 18,881 sign-corrected power rows (C5), so the "counter bias" may partly be a power problem.

## 5. Results in numbers

Changes by rule (values, all zones; from `audit_<ZONE>.csv.gz`):

| Rule | 2020–23 | 2025 | Action |
|---|---|---|---|
| `counter_partial` | 29,851 | 710,195 | emptied |
| `interpolated` | 143,371 | 363,061 | filled (2025: ≤ 15 min; 2020–23: ≤ 3 readings) |
| `sign_inverted` | 115,582 | 315,775 | × −1 (NW Emerg. Lighting) |
| `env_sensor_absent` | 100,048 | 255,264 | emptied (zone NE) |
| `partial_power` | 6,965 | 303,138 | emptied |
| `negative_recovered` | 31,538 | 208,713 | absolute value |
| `zero_is_missing` | 138,608 | 6,791 | emptied |
| `all_zero_reading` | 11,530 | 59,165 | emptied |
| `env_reading_missing` | 1,860 | 65,923 | emptied |
| `counter_negative` | 26,586 | 14,470 | emptied |
| `counter_zero` | 36,317 | 673 | emptied |
| `outlier_nulled` / `outlier_kept` | 11,828 / 13,455 | 24,891 / 9,243 | emptied / flagged only |
| `pf_implausible` | 1,282 | 12,218 | flagged only |
| `counter_reset` / `counter_jump` / `counter_spike` | 922 / 1,078 / 246 | 81 / 148 / 213 | kept / kept / emptied |
| others (`hum_isolated`, `temp_impossible`, `negative_nulled`, `corrupted_value`) | 241 | 2,227 | emptied |
| **Total** | **671,308** | **2,352,189** | **3,023,497** |

Per-circuit provenance of `energy_Wh` and the per-circuit verdicts: `sensor_quality_<ZONE>.csv`, `Final_Evidence/analysis/cleaning_energy_source_vs_error.csv`.

## 6. What happens after the cleaning (owned by other tasks)

- **Hourly dataset and validity rules** (`DECISIONS_v1.2.md`, D1–D5): minute values are summed to hours. An hour is valid if it has at least one reading and no gap over 15 minutes inside it. It is flagged if its energy exceeds 2 × mean power + 1 Wh.
  - Earlier versions (v1.0/v1.1) required at least 30 minute-readings per hour, and a circuit needed 90 % valid hours to be modelled. SE and SW reached only 35–89 %, so they were excluded: the 8-vs-16 circuits mismatch.
  - v1.2 dropped the 30-reading rule because, with C2, the energy after a gap already covers the gap: SE/SW had fewer *readings*, not missing *energy*.
- **2025-only scope** for training: `08_Scope_Decision_2025_Only.md`. The historical data was cleaned with the same rules and is ready if a combined model is tested.
- **Impact of the flagged sensors and of the energy source**: `12a_Cleaning_Checks.md`.

## 7. Weaknesses and open points

| # | Point | Status |
|---|---|---|
| W1 | Column meanings (Er active, Ea apparent) and units not confirmed by CeDInt | Open, question for the sponsor |
| W2 | Thresholds (k = 3, 24 h, 60 %, 10 readings, 15 min, 90 days) set by judgment, not sensitivity-tested | Open; a test of the counter rules on 2025 would show how much the hourly target moves |
| W3 | Absolute value of a negative *sum* of meters is an approximation (C5) | Effect on the target measured: 0.075 % of 2025 energy |
| W4 | Sensor verdicts not used downstream | Measured in `12a_Cleaning_Checks.md`: conclusions unchanged; day-ahead selection margin sensitive |
| W5 | SE/SW 2025 data: half or more of the energy rows are shared-out counter differences | Accuracy on scored hours not worse; fewer usable hours (`12a`, check B) |
| W6 | Some evidence numbers written inside the notebook's rule descriptions (`rules.csv`) come from an earlier run and do not match the outputs | See below; this document uses the outputs |
| W7 | Notebook run by hand in Colab, one workbook at a time; the raw workbooks are not in the repository | Reproducible from `run_config` and the notebook, given the raw files |

**Rule descriptions that do not match the outputs (W6):**

| Rule | Notebook text | Output files |
|---|---|---|
| `sign_inverted` | "would throw away 216,000 usable rows" | 86,686 rows (431,357 values) |
| `negative_nulled` | "keeps 97,185 recoverable values while discarding only 99" | 240,251 recovered, 109 emptied |
| `temp_impossible` | "534 rows" | 140 zone-level readings (the notebook likely counted per sheet) |
| `temp_impossible` (alternative) | "7,935 cold readings, 6,571 in January 2021" | 1,571 zone-level readings below 10 °C, 1,291 in January 2021 (same reason) |
| `pf_implausible` | "0.52 % of rows, concentrated in SE Lighting (7.8 %)" | 0.53 % overall; highest SW Hand Dryer 3.8 %, SE Lighting 0.7 % |
| `interpolated` | "means 15 minutes in both eras" | 15 readings in 2025, but 3 readings (3 hours) in 2020–23, because of a minimum of 3 rows in the code |
| `counter_negative` | "82,101 negative counter cells before cleaning" | Not reproducible from the outputs (raw files needed) |

## 8. If we started over

1. **Ask the sponsor first** for column meanings, units and the meter list per sheet. Most of our test work (C1) was done to replace one email.
2. **Run as one script** on all four workbooks, with the raw files hashed and stored with the outputs, instead of a Colab notebook run by hand.
3. **Sensitivity-test the counter thresholds** before handing over, and report how much the hourly target moves.
4. **Make the verdicts part of the contract**: the hand-over note should state which circuits are flagged and what the modellers must do with them.
5. **Clean only what the model uses first** (2025 energy), then extend; the environmental and historical cleaning took time and is not used by the final model.
6. **One branch from day 1.** Our clean data sat on a separate branch for two weeks, which is how part of the team missed the verdicts and the README that explained the SE/SW exclusion.

## 9. Likely questions and short answers

| Question | Answer |
|---|---|
| How did you clean the data? | 24 documented rules, each with reason, rejected alternative and evidence. Wrong values become empty, never invented. Every change is in an audit file with old and new value. |
| How did you handle negative power? | One meter wired backwards: whole series flipped. Isolated negatives of normal size: absolute value. Extreme negatives: emptied. It barely touches the target: 0.075 % of 2025 energy. |
| How is `energy_Wh` built? | Difference of the active energy counter. Across gaps, the counter difference is shared in proportion to power. Power × time only after a reset or at a period start (4 % of 2025 energy). |
| Why the counter and not power × time? | The counter is the meter's own energy measurement; power is a snapshot and misses short loads between readings. |
| How do you know Er is active energy? | Pa / I gives mains voltage, ΔEr matches W, ΔEa / ΔEr = 1 / power factor, and the course slide. Not yet confirmed by the sponsor. |
| Why not fill gaps with interpolation or a model? | Filling invents data. Short power gaps are filled (15 minutes in 2025); energy is never interpolated because the counter already gives the exact total. |
| Did you delete outliers? | Only those no other column supports. Peaks confirmed by a second column or by the counter are kept. |
| What did you not do? | No threshold sensitivity test; sponsor confirmation still missing; sensor verdicts were not used by the models (checked afterwards: conclusions unchanged). |
