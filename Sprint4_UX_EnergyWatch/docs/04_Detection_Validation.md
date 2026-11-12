# Detection Validation — injected-anomaly test

**Backlog item:** PB-38 (detection performance on known events; false-alarm behaviour reported), PB-39 (alerts per day, trade-off between missed events and false alarms)
**Version:** 12 Nov 2026 · **Script:** `source/injection_test.py` · **Outputs:** `analysis/injection_*.csv`

## 1. Why this test
Only one real, confirmed event exists in the test week (NE HVAC left on, 3 Oct 2025), plus a series of NW emergency-lighting readings that are physically impossible (data issues, not waste). One event cannot show how well a detector works. The test therefore **adds artificial surpluses to the real data** and checks whether the detector finds them. This measures **sensitivity** (how much extra use is needed to alert). It does **not** measure the real false-alarm rate, because real anomalies in the data are not known.

## 2. Real known cases (reference)
| Case | Source | Result |
|---|---|---|
| NE HVAC running on 3 Oct 2025 | `Task6_rev0_03-11/data/task6_events_test.csv` | Detected at Strict, Balanced and Sensitive |
| NW emergency lighting 4–5 Oct (energy above what power allows) | same file | Shown as **data issues**, not alerts (by design) |

## 3. Method
| Element | Setting |
|---|---|
| Detector | The one of the dashboard (`build_data.py`), re-implemented on `data.json`. Same rule, same thresholds. |
| Injection | Add a constant surplus to the **actual** hourly series of one circuit. The forecast and the normal range are left untouched, as they would be for an unforeseen event. |
| Magnitude | 25 %, 50 %, 100 % and 200 % of the circuit's mean hourly load. |
| Duration | 1, 3 and 6 consecutive hours. |
| Time of day | Entirely inside occupied hours, or entirely out of hours. |
| Start hour | Every start hour of the 14-day window where all injected hours have a valid reading and no real alert overlaps (so a detection is caused by the injection). |
| Circuits | All 16. |
| Sensitivities | Strict, Balanced, Sensitive. |
| Cases | About 43,500 per sensitivity (43,324 to 43,724). |
| Detection | An alert on that circuit overlaps the injected hours after injection. "High" = that alert has High severity. |
| Quiet-data reference | Alerts per day on the unmodified data. |

## 4. Results

### 4.1 Share of injected cases detected (all circuits pooled)

| Extra use (% of circuit mean) | Strict 1 h / 3 h / 6 h | Balanced 1 h / 3 h / 6 h | Sensitive 1 h / 3 h / 6 h |
|---|---|---|---|
| +25 % | 19 / 24 / 26 % | 23 / 27 / 29 % | 31 / 37 / 40 % |
| +50 % | 29 / 32 / 34 % | 39 / 44 / 46 % | 41 / 43 / 46 % |
| +100 % | 46 / 49 / 51 % | 47 / 49 / 51 % | 59 / 62 / 64 % |
| +200 % | 52 / 53 / 54 % | 64 / 65 / 66 % | 75 / 77 / 78 % |

The pooled percentage is held down by circuits that cannot alert for small surpluses (next section). Time of day makes little difference (Balanced, +100 %: 48 % occupied, 49 % out of hours). Out-of-hours events more often reach High severity (23 % against 13 % at +100 %, Balanced).

### 4.2 Smallest surplus that raises an alert, per circuit (Balanced)
An hour alerts only if the surplus exceeds **both** the sensitivity threshold and the distance between the forecast and the upper band limit. `analysis/injection_minimum_detectable_surplus.csv` gives the median of that requirement per circuit.

| Group | Circuits | Smallest alerting surplus | Binding constraint |
|---|---|---|---|
| Stable, larger loads | NE Plugs & Sockets, NW Rack | about 20 Wh/h (≈ 11 % of mean) | sensitivity floor |
| Medium | SW Plugs & Sockets (56 Wh/h, 21 %), SE Plugs & Sockets (66 Wh/h, 36 %), NW HVAC (20 Wh/h, 38 %), SE HVAC (20 Wh/h, 48 %), SE Lighting (80 Wh/h, 54 %) | 20–80 Wh/h | floor or forecast band |
| Wide normal range | NW Plugs & Sockets (525 Wh/h, 66 %), NW Lighting (78 Wh/h, 108 %) | roughly the normal load itself | forecast band |
| Very small loads | NW and SW Emergency lighting, SE Emergency lighting, NE HVAC, SW Lighting, NW and SW Hand dryers (mean 0.8–12 Wh/h) | 20 Wh/h, which is 170 % to over 1,000 % of their normal use | sensitivity floor |

## 5. What this means
1. **Large, stable circuits are protected well.** A surplus of 10–35 % of normal load is enough on the main plug, rack and HVAC circuits.
2. **Small loads are deliberately not watched closely.** The Balanced floor of 20 Wh per hour ignores differences that are negligible in energy, so a hand dryer or emergency luminaire left on cannot raise an alert unless it uses far more than normal. This is the intended trade-off against alert fatigue (PB-39), and it is visible to the user in the Reliability screen.
3. **The Sensitive setting finds more** (64 % at +100 % over 6 h against 51 %), at the cost of about 0.4 more alerts per day on real data (5.6 against 5.2). Strict adds little protection against large surpluses (54 % at +200 %) but cuts the alert list to 4.7 per day.
4. **Wide forecast bands limit detection** on NW Plugs & Sockets and NW Lighting. Improving those forecasts is the Sprint 4 Task 1 priority.

## 6. Alerts per day on real data
| Sensitivity | Alerts in 14 days | Per day |
|---|---|---|
| Strict | 66 | 4.7 |
| Balanced | 73 | 5.2 |
| Sensitive | 78 | 5.6 |

Many of these alerts come from NW Plugs & Sockets (about 35 of 62 kWh of detected excess), a circuit that draws about 535 Wh per hour day and night. Whether this is waste or a permanent load is a question for UPM (`02_Assumptions_and_Decisions.md`, item U12).

## 7. Limits of the test
- Synthetic surpluses are constant and rectangular; real faults vary in shape.
- Windows are chosen where no real alert exists and every hour has valid data, so they underrepresent the busiest periods.
- The test says nothing about the share of **real** alerts that are false. That needs real events confirmed by the building team.
- Only 14 days of data are used.

## 8. How to repeat
```
python source/run_all.py          # or only: python source/injection_test.py (after build_data.py)
```
`injection_test.py` writes `analysis/injection_test_cases.csv.gz` (every case, compressed), the summary tables and the quiet-data table, and adds the summary to `data.json` for the Reliability screen.
