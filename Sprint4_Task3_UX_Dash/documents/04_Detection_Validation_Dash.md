# Detection Validation — injected-anomaly test (Dash dashboard)

**Sprint 4 · Task 3 (UX) · TBDA Group 2 · Dashboard by Edoardo** · updated 14 Nov 2026 (new forecast interval)
**Script:** `Sprint4_Task3_UX_Dash/engines/injection_test.py` · **Outputs:** `Sprint4_Task3_UX_Dash/analysis/injection_*_dash.csv`

Same structure and file names as the Energy Watch test, with the suffix `_dash` (Energy Watch: `Sprint4_Task4_Documentation/documents/04_Detection_Validation.md`,
`Sprint4_Task4_Documentation/analysis/injection_*.csv`), so the two can be read side by side.

## 1. Why this test

The dashboard flags an *anomaly* when a circuit's measured use leaves the forecast interval of Blend v1.3 (see
README §3c and §4). On the real data we know only one confirmed event, so we cannot say from real data alone how often
a fault would be found. The injection test answers that question. It adds artificial faults of known size and length
to the real measurements and checks, case by case, whether the dashboard finds them.

The questions:

1. How big and how long must an anomaly be before the dashboard finds it?
2. Which circuits can be watched reliably, and which cannot?
3. What does each detector setting cost in alerts per day on the real data?
4. Is the known real event found?

## 2. Method

| Item | Choice |
|---|---|
| Data | Evaluation weeks of dataset v1.2 (validation 22–29 Sep + test 29 Sep–6 Oct 2025, UTC), 16 circuits, Blend v1.3 day-ahead forecasts |
| Detector | Exactly the one in the app (`core/anomalies.detect`): forecast interval = Chronos-Bolt 10–90% band calibrated per circuit on the validation week (conformal, README §4), plus the minimum deviation `min_dev` |
| Spikes (appliance left on) | +25%, +50%, +100% and +200% of the circuit's mean hourly use, added to the measurement |
| Drops (circuit off / failed) | −50% and −100% of the measured use (−100% = switched off) |
| Durations | 1, 3 and 6 consecutive hours |
| Start hours | Every hour where the whole window has valid data and no real anomaly within ±1 hour, so a real event cannot be counted as a find |
| Timing | Occupied hours (weekdays 7–20, Madrid) vs out of hours (nights, weekends, holidays); windows that mix both are skipped |
| Found | At least one hour of the injected window is flagged, in the right direction (spike for spikes, drop for drops) |
| Critical | The flagged run reaches the Critical level (≥ 1 kWh or ≥ 6 h) |
| Settings tested | Interval 80%, 90% (default) and 95% with 25 Wh; 90% with 10 Wh and 50 Wh |
| Cases | **321,366** in total, computed in about 6 s |

Alerts per day are counted on the **unmodified** 14 full days with the same setting. That count is the workload a
user would actually see.

## 3. Results – default setting (90% interval, 25 Wh)

### 3.1 Share found by size and duration (all circuits)

| Injected change | 1 h | 3 h | 6 h |
|---|---|---|---|
| Spike +25% | 17.8% | 19.4% | 20.8% |
| Spike +50% | 24.2% | 29.0% | 32.3% |
| **Spike +100%** | 40.2% | 42.7% | **45.4%** |
| Spike +200% | 49.6% | 51.4% | 53.7% |
| Drop −50% | 23.1% | 25.4% | 27.4% |
| **Drop −100% (off)** | 43.9% | 44.9% | **46.1%** |

Longer and larger anomalies are found more often. Above +100% the share flattens near 50%. The reason is not the
size of the change: about half of the circuits are too small or too uncertain to be watched (§3.2).

### 3.2 By circuit (spike +100%, all durations)

| Circuit | Mean use (Wh) | Found | Smallest extra use seen (median) | What limits it |
|---|---|---|---|---|
| NE Plugs & Sockets | 188 | **100%** | 27 Wh (14%) | minimum deviation |
| NW RACK | 187 | **100%** | 25 Wh (13%) | minimum deviation |
| SW Plugs & Sockets | 263 | **100%** | 62 Wh (24%) | forecast interval |
| SE HVAC | 42 | **100%** | 25 Wh (60%) | minimum deviation |
| SE Plugs & Sockets | 183 | 96.5% | 109 Wh (60%) | forecast interval |
| NW HVAC | 52 | 83.7% | 27 Wh (51%) | minimum deviation |
| NW Plugs & Sockets | 792 | 64.6% | 676 Wh (85%) | forecast interval (very variable circuit) |
| NW Lighting | 72 | 25.5% | 121 Wh (168%) | forecast interval |
| SE Lighting | 147 | 1.9% | 258 Wh (176%) | forecast interval |
| NE HVAC, SW Lighting, emergency lights, hand dryers | 1–12 | 0% | 25 Wh (>200%) | minimum deviation: +100% of their mean is below 25 Wh |

### 3.3 Occupied hours vs night/weekend (all durations)

| Change | Occupied | Out of hours |
|---|---|---|
| Spike +100% | 44.0% | 41.7% |
| Spike +200% | 50.1% | 51.7% |
| Drop −100% | 47.7% | 43.7% |

Timing makes little difference.

### 3.4 Known real event

NE|HVAC left on, 3 Oct 2025 11:00–14:00: **found at 80%, 90% and 95%** as a Critical spike of +1.63 kWh.

## 4. Choosing a setting – the trade-off

| Setting | Anomalies/day (real data) | Spike +100% 6 h found | Off 6 h found | Interval coverage (14 days) |
|---|---|---|---|---|
| 80% · 25 Wh | 8.50 | 48.1% | 47.0% | 82.2% |
| **90% · 25 Wh (default)** | **4.79** | **45.4%** | **46.1%** | 90.9% |
| 95% · 25 Wh | 3.21 | 41.6% | 39.3% | 95.5% |
| 90% · 10 Wh | 6.14 | 57.0% | 56.9% | 90.9% |
| 90% · 50 Wh | 4.50 | 39.9% | 35.4% | 90.9% |

- **90% · 25 Wh** is the default: it finds almost as much as 80% with 44% fewer alerts.
- **95%** is for a user who wants few alerts (3.2 per day) and accepts missing a few more faults.
- **10 Wh** is the most sensitive setting. It is the only one that can watch some of the small circuits, at the cost
  of about 1.4 more alerts per day.

The coverage on real data (82/91/96%) matches the nominal level, so the interval is well calibrated. The user can
change the setting in **Settings** (interval level and minimum deviation). The Performance page shows the results
for each one.

### Effect of the new interval (14 Nov 2026)

| Default setting (90% · 25 Wh) | Previous interval (symmetric) | New interval (calibrated Chronos band) |
|---|---|---|
| Anomalies per day on real data | 5.71 | **4.79** (−16%) |
| Spike +100% 6 h found | **48.9%** | 45.4% |
| Switched off 6 h found | 45.9% | **46.1%** |
| Test-week coverage, mean distance from 90% per circuit | 6.6 points | **3.9 points** |

The new interval gives about the same detection with fewer alerts and a coverage that is even across circuits.

## 5. Comparison with the Energy Watch app (Sprint 4 Task 4)

The numbers of the two published injection tests are not directly comparable (different cases, thresholds and alert
counting). A like-for-like test of both detectors on the same 59,448 cases is summarised in
[`Injection_Tests_Explained.md`](Injection_Tests_Explained.md). In short: at the same number of
alerts the two find spikes about equally well; only this dashboard detects switch-offs; and its interval is now the
better calibrated of the two, circuit by circuit.

## 6. Limits

- Only two weeks of data (14 full days), so the alerts per day have wide uncertainty.
- The interval is calibrated on the validation week, so that week is in-sample; the test week is not.
- Injected anomalies are clean rectangles; real faults can ramp up or come and go.
- Spikes are added on top of real use, so a forecast that is already wrong in that hour can hide or reveal them.
- Only one confirmed real event exists, so the real-world hit rate cannot be measured directly.
- The tiny circuits (hand dryers, emergency lights, NE HVAC, SW lighting) cannot be watched with a 25 Wh minimum
  deviation. A per-circuit minimum would fix this but needs more data to avoid false alerts.

## 7. How to repeat it

```bash
cd 2026G2
source .venv/bin/activate
python Sprint4_Task3_UX_Dash/engines/injection_test.py
```

The script writes into `Sprint4_Task3_UX_Dash/analysis/` (Energy Watch names + `_dash`; `sensitivity` =
the setting, e.g. "90% · 25 Wh"):

| File | Content |
|---|---|
| `injection_test_cases_dash.csv.gz` | Every case: setting, circuit, start, size, duration, found, level |
| `injection_detection_by_magnitude_duration_dash.csv` | Share found by size × duration (table 3.1) |
| `injection_detection_by_circuit_dash.csv`, `injection_detection_by_circuit_magnitude_dash.csv` | By circuit (table 3.2) |
| `injection_detection_by_period_dash.csv` | Occupied vs night/weekend (table 3.3) |
| `injection_minimum_detectable_surplus_dash.csv` | Smallest extra use the dashboard can see, per circuit |
| `injection_quiet_data_alerts_dash.csv` | Anomalies per day and interval coverage on the real data (table 4) |
| `injection_known_event_check_dash.csv` | Known real event (§3.4) |
| `injection_meta_dash.json` | Settings and run date |

In the dashboard, the **Re-run test** button on the Performance page runs the same script and reloads the charts.
