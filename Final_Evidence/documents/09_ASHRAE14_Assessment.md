# ASHRAE Guideline 14 Assessment of Blend v1.3, by level

**TBDA Group 2 · CeDInt Storey 1 · Final-phase evidence pack** · 17 Nov 2026
**Authors:** Jules (main author) · Claude (co-author)
**Script:** `Final_Evidence/scripts/ashrae14_by_level.py` · **Outputs:** `Final_Evidence/analysis/ashrae14_by_level_test.csv`, `ashrae14_by_level_validation.csv` (all circuits, load types, zones, building, three horizons)

## 1. Why and how

The teacher asked on the forum (15–17 Nov) that results be checked against ASHRAE Guideline 14. That guideline is written for **calibrating building energy models**, with hourly criteria **CV(RMSE) ≤ 30 %** and **|NMBE| ≤ 10 %** (monthly: 15 % and 5 %). We apply the two criteria to **forecast errors** as a common reference. This is a **reference, not a certification**: a forecast at +1 h or day-ahead is a different task from a calibrated simulation.

| Item | Choice |
|---|---|
| Model | Blend v1.3 (frozen) |
| Hours scored | **the Task 6 common hours** (valid for all nine models): 1,911 circuit-hours per horizon on the test week (29 Sep–5 Oct 2025) and 1,873 on validation (22–28 Sep). The script reproduces the official Blend MAE (34.16 Wh day-ahead; official 34.2) |
| CV(RMSE) | 100 × RMSE / mean of the measurements |
| NMBE | reported with the **ASHRAE sign**, 100 × Σ(measured − forecast) / Σ measured. **Positive = the forecast is below the measurement.** (Dashboards and Task 6 use forecast − measured; the sign is opposite) |
| Zone and building totals | circuits summed per hour; only hours where **every** circuit of the zone (building: all 16) is in the common hours |

> **Consistency note.** `Sprint4_Task4_Documentation/analysis/accuracy_metrics_MAPE_CVRMSE.csv` uses a **wider mask (2,174 circuit-hours; 26 building hours)**, so its MAE (30.7 Wh day-ahead) differs from the official Task 6 MAE (34.2 Wh). This document and the final presentation use the official mask. Numbers quoted from the older file (e.g. building CV(RMSE) 6.3 / 14.2 / 15.4 %) should be replaced by the ones below.

## 2. Results on the test week

### 2.1 Pooled, zones, building

| Level | n hours | CV(RMSE) % +1 h | +6 h | day-ahead | NMBE % (ASHRAE sign) +1 h | +6 h | day-ahead |
|---|---|---|---|---|---|---|---|
| Pooled 16 circuit-hours | 1,911 | 68.7 | 99.5 | 102.1 | 4.7 | 6.9 | 2.5 |
| Zone NE (2 circuits) | 167 | 36.5 | 38.6 | 38.5 | 4.0 | 4.4 | 4.7 |
| Zone NW (6) | 149 | 27.4 | 40.6 | 41.6 | 7.3 | 11.5 | 6.1 |
| Zone SE (4) | **24** | 10.4 | 14.6 | 37.9 | −5.2 | −10.0 | −15.2 |
| Zone SW (4) | 42 | 5.1 | 9.5 | 7.8 | −2.4 | −4.0 | −2.5 |
| **Building (all 16)** | **12** | **6.7** | **17.6** | **19.5** | −3.7 | −0.2 | −9.4 |

Reading: against the hourly reference (30 % / 10 %), **the building total passes at all three horizons** (CV(RMSE) 6.7 / 17.6 / 19.5 %, |NMBE| ≤ 9.4 %), and **SW passes** everywhere. NE passes NMBE but never CV(RMSE) (36.5–38.6 %). NW passes only at +1 h (27.4 %, 7.3 %); at +6 h and day-ahead it fails CV(RMSE) (40.6 / 41.6 %), and at +6 h also NMBE (11.5 %). SE passes at +1 h and +6 h (the +6 h NMBE of −10.0 % is right on the limit) but fails day-ahead on both criteria (37.9 %, −15.2 %). **Pooled circuit-hours do not pass** (about 100 %): small, spiky circuits dominate the pooled CV(RMSE).

**Strong caveat on sample size:** the building total rests on **12 hours** and SE on **24 hours**, because few hours have every circuit valid. These two lines are indicative, not statistically solid.

### 2.2 By circuit (day-ahead, test week)

| Circuit | Mean (Wh) | MAE (Wh) | CV(RMSE) % | NMBE % (ASHRAE) | ≤ 30 % and ≤ 10 %? |
|---|---|---|---|---|---|
| NE Plugs & Sockets | 189.6 | 3.0 | 2.0 | −0.2 | yes |
| NW RACK | 187.1 | 2.4 | 1.7 | 0.1 | yes |
| NW Emerg. Lighting | 11.2 | 0.6 | 8.5 | 2.7 | yes |
| SW Emerg. Lighting | 11.6 | 0.6 | 6.6 | −1.4 | yes |
| SE HVAC | 41.8 | 1.0 | 3.7 | 0.5 | yes |
| SE Emerg. Lighting | 2.1 | 0.4 | 29.6 | −2.4 | yes |
| SE Plugs & Sockets | 190.2 | 24.9 | 17.4 | −7.7 | yes |
| SW Plugs & Sockets | 238.7 | 18.1 | 12.5 | 0.5 | yes |
| NW Plugs & Sockets | 763.4 | 250.9 | 57.8 | 4.8 | CV no, NMBE yes |
| NW HVAC | 70.7 | 28.9 | 82.8 | 12.6 | no |
| NW Lighting | 83.7 | 49.1 | 100.4 | 13.6 | no |
| NE HVAC | 12.5 | 10.3 | 620.2 | 78.8 | no (mean 12.5 Wh; near-zero denominator) |
| SE Lighting | 31.4 | 40.5 | 386.6 | −124.5 | no (3-day episode, section 4) |
| SW Lighting | 1.2 | 0.95 | 112.9 | 13.4 | no (mean ≈ 1 Wh) |
| NW Hand Dryer / SW Hand Dryer | 0.6 / 0.7 | 0.7 / 0.6 | 174.4 / 98.6 | 65.7 / 17.1 | no (mean < 1 Wh) |

**8 of 16 circuits pass both hourly criteria at day-ahead** (also 8 at +1 h, 7 at +6 h). The failures are the circuits with a very low or very irregular load (hand dryers, SW/NE low-use circuits), plus NW Plugs, NW HVAC, NW Lighting and SE Lighting.

### 2.3 Teacher's indicative targets (15 Nov), day-ahead

| Group | Target | Circuits | Result |
|---|---|---|---|
| Constant loads | CV(RMSE) ≤ 15 % | NW RACK 1.7, NW Emerg 8.5, SW Emerg 6.6, SE Emerg 29.6 | **3 of 4** |
| Plugs & Sockets | ≤ 30 % | NE 2.0, SE 17.4, SW 12.5, NW 57.8 | **3 of 4** |
| HVAC | 30–50 % with \|NMBE\| ≤ 10 % | SE 3.7 (NMBE 0.5), NW 82.8, NE 620.2 | **1 of 3** |
| Lighting, hand dryers | no numeric target (MAE and daily energy) | — | reported as MAE only |

**7 of 11 circuits with a numeric target meet it.** The four misses: SE Emerg. Lighting (mean 2 Wh), NW Plugs, NW HVAC, NE HVAC (mean 12.5 Wh).

## 3. Daily and monthly

- **Daily:** `Sprint4_Task4_Documentation/analysis/accuracy_daily_totals.csv` covers only **6 complete days** per split (and its own mask). Daily WAPE on the test week: RACK 0.2 %, NE Plugs 0.7 %, NW Emerg 2.4 %, NW Plugs 21.1 %, NW Lighting 29.6 %, NW HVAC 36.0 %. This is indicative only.
- **Monthly (ASHRAE 15 % / 5 %) cannot be assessed:** the test week is one week and the data spans 8 weeks.

## 4. What drives the failures

- **NW Plugs (52.4 %) and SE Lighting (23.5 %) are 75.9 % of the day-ahead validation error.** SE Lighting has one episode of about 470 Wh for about 3 days (26 Sep noon–29 Sep noon); the forecast lags it by about one day on each side (our reading: it relies on the values 24 h and 168 h before).
- The hourly criterion is hard for circuits whose mean is a few Wh (CV(RMSE) divides by a near-zero mean).

## 5. How to present this (suggested)

1. Show the zone / building table (2.1) first, with the n = 12 and n = 24 warnings.
2. Show 2.2 as "8 of 16 circuits pass; here is why the others do not".
3. State that ASHRAE 14 is a calibration standard used here as a **reference**, not a certification, and that the monthly criterion cannot be tested with 8 weeks.
4. Close with the teacher's targets: 7 of 11 met, 4 missed and why.
