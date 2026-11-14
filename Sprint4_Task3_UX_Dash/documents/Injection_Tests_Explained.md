# Injection tests: Dash dashboard vs Energy Watch – values explained and who wins

**TBDA Group 2 · CeDInt Storey 1 · Sprint 4 · 14 Nov 2026**

Two dashboards were built on the final model (Blend v1.3): the **Dash dashboard** (Sprint 4 Task 3, Edoardo) and
**Energy Watch** (Sprint 4 Task 4, Jules). Both flag hours where a circuit uses more (or less) energy than expected,
and both were checked with an **injection test**. This file explains what the numbers of the two tests mean and which
dashboard wins on each point.

The two tests are documented the same way:

| | Dash dashboard | Energy Watch |
|---|---|---|
| Report | [`documents/04_Detection_Validation_Dash.md`](04_Detection_Validation_Dash.md) | `Sprint4_Task4_Documentation/documents/04_Detection_Validation.md` |
| Results | `Sprint4_Task3_UX_Dash/analysis/injection_*_dash.csv` | `Sprint4_Task4_Documentation/analysis/injection_*.csv` |
| Script | `Sprint4_Task3_UX_Dash/engines/injection_test.py` | `Sprint4_UX_EnergyWatch/source/injection_test.py` |

---

## 1. What an injection test is

Only one real fault is confirmed in the data (NE HVAC left on, 3 Oct 2025, 11:00–14:00). One case cannot show how
well a detector works. So both tests **add artificial faults of known size and length to the real measurements**
(22 Sep – 6 Oct 2025, 16 circuits) and count how many the dashboard finds.

| Term | Meaning |
|---|---|
| Spike | Extra use added to a circuit: +25%, +50%, +100% or +200% of its mean hourly use (an appliance left on) |
| Drop | Use removed: −50% or −100% (−100% = circuit switched off or failed). Tested by the Dash dashboard only |
| Duration | The fault lasts 1, 3 or 6 consecutive hours |
| Found (%) | Share of injected faults where at least one hour was flagged |
| Alerts per day | Alerts raised on the **unmodified** data with the same setting: the workload the user sees, and a proxy for false alarms |
| Setting | The detector's sensitivity: Strict / Balanced / Sensitive (Energy Watch), interval level and minimum deviation (Dash) |

The two detectors use the same Blend v1.3 forecast. They differ in the **normal range** around it and in the
**threshold**:

| | Dash dashboard | Energy Watch |
|---|---|---|
| Normal range | Chronos-Bolt 10–90% band calibrated per circuit to hold 80 / 90 / 95% of the hours | Chronos-Bolt 10–90% band as it comes (about 80% of the hours) |
| Threshold | Excess ≥ minimum deviation (default 25 Wh) | Excess ≥ max(floor, share × circuit mean): Strict 40 Wh / 20%, Balanced 20 Wh / 10%, Sensitive 10 Wh / 5% |
| Default setting | 90% interval, 25 Wh | Balanced |
| Directions | Spikes and drops | Spikes only |

---

## 2. The two original tests

Each team ran its own test with its own case selection, so these two sections are **not directly comparable**
(section 3 is).

### 2.1 Energy Watch test (Jules)

About 43,500 spike cases per setting.

| Spike | Strict 1 h / 3 h / 6 h | Balanced 1 h / 3 h / 6 h | Sensitive 1 h / 3 h / 6 h |
|---|---|---|---|
| +25% | 19 / 24 / 26% | 23 / 27 / 29% | 31 / 37 / 40% |
| +50% | 29 / 32 / 34% | 39 / 44 / 46% | 41 / 43 / 46% |
| +100% | 46 / 49 / 51% | 47 / 49 / 51% | 59 / 62 / 64% |
| +200% | 52 / 53 / 54% | 64 / 65 / 66% | 75 / 77 / 78% |
| **Alerts per day** | **4.7** | **5.2** | **5.6** |

How to read it: with Balanced, a circuit using double its normal energy for 6 hours is found in 51% of cases, and the
user sees 5.2 alerts a day.

### 2.2 Dash dashboard test (Edoardo)

About 64,000 cases per setting, spikes and drops (new calibrated interval).

| Fault | 1 h | 3 h | 6 h |
|---|---|---|---|
| Spike +25% | 17.8% | 19.4% | 20.8% |
| Spike +50% | 24.2% | 29.0% | 32.3% |
| Spike +100% | 40.2% | 42.7% | **45.4%** |
| Spike +200% | 49.6% | 51.4% | 53.7% |
| Drop −50% | 23.1% | 25.4% | 27.4% |
| Drop −100% (off) | 43.9% | 44.9% | **46.1%** |

| Setting | Anomalies/day (spikes + drops) | Spike +100% 6 h | Off 6 h |
|---|---|---|---|
| 80% · 25 Wh | 8.50 | 48.1% | 47.0% |
| **90% · 25 Wh (default)** | **4.79** | **45.4%** | **46.1%** |
| 95% · 25 Wh | 3.21 | 41.6% | 39.3% |
| 90% · 10 Wh | 6.14 | 57.0% | 56.9% |
| 90% · 50 Wh | 4.50 | 39.9% | 35.4% |

How to read it: with the default, a circuit using double its normal energy for 6 hours is found in 45% of cases, a
circuit switched off for 6 hours in 46%, and the user sees 4.8 anomalies a day (3.6 spikes + 1.1 drops in the
same-case count of section 3).

### 2.3 Why the original numbers cannot be compared

- Different case sets (each test excludes different windows).
- Different alert counts: Energy Watch counts spikes only, Dash counts spikes and drops.
- Different thresholds (20 Wh vs 25 Wh), so a different trade-off between finding faults and raising alerts.

A detector can always find more faults by raising more alerts. The fair question is: **who finds more faults for the
same number of alerts?**

---

## 3. The same-case comparison

Both detectors were run on the **same 59,448 injected cases**, with the same "found" rule and alerts counted the
same way.

### 3.1 Default and sensitive settings

| Setting | Spikes found (all sizes) | +100% 6 h | +200% 6 h | Off 6 h | Spike alerts/day | Drop alerts/day |
|---|---|---|---|---|---|---|
| Energy Watch Balanced | **43.5%** | **46.4%** | **62.1%** | 0% | 5.21 | – |
| Dash 90% · 25 Wh | 32.6% | 41.1% | 48.5% | **41.9%** | **3.64** | 1.14 |
| Energy Watch Strict | 36.2% | 46.4% | 48.4% | 0% | 4.71 | – |
| Energy Watch Sensitive | **52.9%** | **60.8%** | **76.0%** | 0% | 5.57 | – |
| Dash 90% · 10 Wh | 47.1% | 55.5% | 74.7% | **55.4%** | **4.07** | 2.07 |

At the defaults Energy Watch finds 11 points more spikes, but with **43% more spike alerts**.

### 3.2 Same number of alerts (the fair test)

| Spike alerts per day | Dash | Energy Watch | Winner |
|---|---|---|---|
| ≈ 5.6 | 54.6% (+100% 6 h: 67.9%) | 52.9% (60.8%) | Dash, +1.7 (+7.1 on large faults) |
| ≈ 5.1 | 52.2% | 49.5% | Dash, +2.7 |
| ≈ 4.5 | 48.7% (62.3%) | 36.2% (46.4%), Strict at 4.7/day | **Dash, +12.5** |
| ≈ 5.0, test week only | 55.0% | 55.1% | Tie |
| ≈ 3.9, test week only | 49.3% | 34.1% | **Dash, +15** |

### 3.3 By circuit (spikes, all sizes, default settings)

| Circuit | Energy Watch Balanced | Dash 90% · 25 Wh | Better |
|---|---|---|---|
| NE Plugs & Sockets, NW Rack | 100% | 100% | Tie |
| SW Plugs & Sockets | 93.7% | 88.2% | Energy Watch |
| SE Plugs & Sockets | 80.8% | 58.9% | Energy Watch |
| NW Plugs & Sockets | 66.1% | 44.3% | Energy Watch |
| SE Lighting | 64.1% | 16.4% | Energy Watch |
| NW Lighting | 45.1% | 21.4% | Energy Watch |
| SE HVAC | 72.6% | 51.1% (95.8% at 10 Wh) | Energy Watch at default |
| NW HVAC | 61.8% | 55.1% (78.5% at 10 Wh) | Energy Watch at default |
| Emergency lights, NE HVAC, SW Lighting, hand dryers | 0–25% | 0–3% | Energy Watch (lower floor, 20 Wh) |

Energy Watch finds more per circuit because its band is narrower: it holds about 80% of the hours (71% on SE
Lighting), the Dash interval 90%. A narrower band catches more injected faults but also flags more normal hours,
which is why it raises more alerts.

### 3.4 Calibration of the normal range (test week, not used for calibration)

| | Hours inside (total) | Mean distance from the target, per circuit |
|---|---|---|
| Energy Watch band (target 80%) | 83.4% | 4.8 points |
| Dash interval 80% | 82.8% | 7.0 points |
| **Dash interval 90% (default)** | **90.7%** | **3.9 points** |

### 3.5 Known real event

NE HVAC left on, 3 Oct 2025: all 3 hours flagged by **every setting of both dashboards**.

---

## 4. Who wins in what

| Criterion | Winner | Why |
|---|---|---|
| Spikes found at the default settings | **Energy Watch** | +11 points, but 43% more alerts |
| Spikes found at the same number of alerts (≈ 5/day) | **Tie** | 52–55% each |
| Spikes found when few alerts are wanted (≈ 4/day) | **Dash** | +12 to +15 points |
| Large faults (+100% for 6 h) at the same alert budget | **Dash** | +7 to +16 points |
| Small faults (+25–50%) | **Energy Watch** | Narrower band |
| Fewer alerts for the user | **Dash** | 3.6 vs 5.2 spike alerts/day at the defaults |
| Switch-offs and failures (drops) | **Dash** | 42–55% found; Energy Watch cannot detect them |
| Variable circuits (SE/NW Plugs, SE/NW Lighting) | **Energy Watch** | Narrower 80% band |
| Very small circuits (emergency lights, hand dryers) | **Energy Watch** | 20 Wh floor instead of 25 Wh |
| Calibration at the default level | **Dash** | 90.7% total, 3.9 points per circuit |
| Calibration at 80% | **Energy Watch** | 4.8 vs 7.0 points per circuit |
| Known real event | **Tie** | Found by every setting |

### Overall

**The Dash dashboard wins overall, by a small margin on spikes and clearly on everything else.**

- For spikes, the two detectors are equally good at about 5 alerts a day. Energy Watch's higher default score comes
  from a more sensitive default, not from a better detector.
- When the user wants fewer alerts, the Dash dashboard finds clearly more faults.
- Only the Dash dashboard detects switch-offs and failures.
- Energy Watch keeps a real advantage on the four most variable circuits and on very small loads.

---

## 5. Limits of both tests

- Only 14 days of data; alerts per day have wide uncertainty.
- Alerts on real data are a proxy for false alarms: real anomalies are not labelled.
- Injected faults are clean rectangles; real faults can ramp up or come and go.
- The Dash interval is calibrated on the validation week, so that week is in-sample; the test-week results are not.
- Only one confirmed real event exists.

## 6. How to repeat

```bash
# Dash injection test
python Sprint4_Task3_UX_Dash/engines/injection_test.py

# Energy Watch injection test
python Sprint4_UX_EnergyWatch/source/injection_test.py
```
