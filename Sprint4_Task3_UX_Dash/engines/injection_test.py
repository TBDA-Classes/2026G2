"""Injected-anomaly test of the dashboard's anomaly detector (spikes AND drops).

Why: only one real event is confirmed in the evaluation weeks (NE|HVAC left on, 3 Oct 2025), so it cannot tell how
well the detector works. The test adds artificial anomalies to the REAL measured series and checks whether the
detector of the dashboard (anomalies.py: same interval, same rule, same thresholds) finds them.

Design
  data        evaluation weeks 22 Sep – 5 Oct 2025, all 16 circuits, Blend v1.3 day-ahead + forecast interval
              (Chronos-Bolt band calibrated per circuit, data_layer.apply_intervals)
  levels      interval 80 / 90 / 95 %, minimum deviation 25 Wh (the dashboard default)
  spikes      add a constant +25 / +50 / +100 / +200 % of the circuit's mean hourly use
  drops       cut the measured use by 50 % or 100 % (= circuit switched off)
  duration    1, 3 or 6 consecutive hours
  timing      entirely in occupied hours (weekdays 07–20 h) or entirely out of hours (nights, weekends, holidays)
  start hours every start where all injected hours have a valid reading and no real anomaly is present
              (so a detection is caused by the injection); forecast and interval are left untouched, as they
              would be for an unforeseen event
  detected    at least one injected hour is flagged in the right direction; the level is the level of the
              anomaly that contains it (Critical / Moderate / Minor, same rule as the dashboard)
  quiet data  anomalies per day on the unmodified data = the alert load a user would see

    python Sprint4_Task3_UX_Dash/engines/injection_test.py        (a few seconds; writes Sprint4_Task3_UX_Dash/analysis/)

Output files follow the names of the Energy Watch test (Sprint4_Task4_Documentation/analysis/injection_*.csv) with
the suffix `_dash`, so the two can be read side by side and told apart; `sensitivity` = the detector setting, e.g. "90% · 25 Wh".
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "core"))   # settings, data_layer, anomalies


import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import anomalies as AN
import settings as S

OUT = S.VAL_DIR
LEVELS = (0.80, 0.90, 0.95)
MIN_DEV = AN.DEFAULTS["min_dev"]
# settings tested: the three interval levels at the default minimum deviation, plus a lower and a higher deviation
CONFIGS = [(0.80, MIN_DEV), (0.90, MIN_DEV), (0.95, MIN_DEV), (0.90, 10.0), (0.90, 50.0)]
SPIKES = (0.25, 0.50, 1.00, 2.00)
DROPS = (0.50, 1.00)
HOURS = (1, 3, 6)
KNOWN_EVENT = ("NE|HVAC", pd.Timestamp("2025-10-03 11:00"), pd.Timestamp("2025-10-03 14:00"))   # Madrid time


def _label(level: float, min_dev: float) -> str:
    return f"{level * 100:.0f}% · {min_dev:.0f} Wh"


def _level(dev_kwh: float, n: int) -> str:
    if abs(dev_kwh) >= 1 or n >= 6:
        return "Critical"
    if abs(dev_kwh) >= 0.25 or n >= 3:
        return "Moderate"
    return "Minor"


def run_level(level: float, MIN_DEV: float) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    f = AN.frame("eval", level)
    hrs, an = AN.detect(f, MIN_DEV, AN.DEFAULTS)
    per_day = f.groupby(f["time"].dt.normalize())["time"].nunique()
    days = int((per_day >= 20).sum())                                  # full days (14)
    quiet = {"level": level, "min_dev_Wh": MIN_DEV, "days": days, "alerts_14_days": len(an),
             "alerts_per_day": round(len(an) / days, 2),
             "spikes": int((an["kind"] == "Spike").sum()), "drops": int((an["kind"] == "Drop").sum()),
             "critical": int((an["level"] == "Critical").sum()),
             "interval_coverage_pct": round(AN.coverage(f) * 100, 1)}
    rows, mins = [], []
    for circ, g in f.groupby("circuit"):
        g = g.sort_values("target_utc").reset_index(drop=True)
        a, fc, lo, hi = (g[c].to_numpy(dtype=float) for c in ("actual", "forecast", "lo", "hi"))
        valid = ~np.isnan(a)
        ooh = g["night_weekend"].to_numpy()
        up0 = valid & (a > hi) & (a - fc >= MIN_DEV)                  # real anomaly hours (unmodified data)
        dn0 = valid & (a < lo) & (fc - a >= MIN_DEV)
        real = up0 | dn0
        mean = float(np.nanmean(a))
        n = len(a)
        # smallest surplus that flags each normal hour (spikes): must clear the interval AND the minimum deviation
        ok = valid & ~real
        need_band = hi[ok] - a[ok]
        need_dev = MIN_DEV - (a[ok] - fc[ok])
        need = np.maximum(need_band, need_dev)
        mins.append({"level": level, "min_dev_Wh": MIN_DEV, "circuit": circ, "mean_load_Wh": round(mean, 1),
                     "median_min_surplus_Wh": round(float(np.median(need)), 1),
                     "median_min_surplus_pct_of_mean": round(float(np.median(need)) / max(mean, 1e-9) * 100, 0),
                     "binding": "forecast interval" if np.median(need_band) >= np.median(need_dev)
                     else "minimum deviation",
                     "switch_off_detectable_pct": round(float(np.mean((lo[ok] > 0) & (fc[ok] >= MIN_DEV))) * 100, 1)})
        for d in HOURS:
            for s in range(0, n - d + 1):
                idx = slice(s, s + d)
                if not valid[idx].all() or real[max(0, s - 1):s + d + 1].any():
                    continue
                o = ooh[idx]
                if o.all():
                    period = "out of hours"
                elif (~o).all():
                    period = "occupied"
                else:
                    continue
                for kind, mags in (("Spike", SPIKES), ("Drop", DROPS)):
                    for m in mags:
                        a2 = a.copy()
                        if kind == "Spike":
                            a2[idx] = a[idx] + m * mean
                            flag = valid & (a2 > hi) & (a2 - fc >= MIN_DEV)
                        else:
                            a2[idx] = a[idx] * (1 - m)
                            flag = valid & (a2 < lo) & (fc - a2 >= MIN_DEV)
                        hit = flag[idx]
                        det = bool(hit.any())
                        lvl = ""
                        if det:                                    # the anomaly run that contains the injection
                            i0 = s + int(np.argmax(hit))
                            l, r = i0, i0
                            while l - 1 >= 0 and flag[l - 1]:
                                l -= 1
                            while r + 1 < n and flag[r + 1]:
                                r += 1
                            lvl = _level(float(np.sum(a2[l:r + 1] - fc[l:r + 1])) / 1000, r - l + 1)
                        rows.append((level, MIN_DEV, circ, kind, m, d, period, det, lvl,
                                     round(float(np.sum(np.abs(a2[idx] - a[idx]))) / 1000, 4)))
    cases = pd.DataFrame(rows, columns=["level", "min_dev_Wh", "circuit", "kind", "magnitude", "hours", "period", "detected",
                                        "anomaly_level", "injected_kwh"])
    return cases, quiet, pd.DataFrame(mins)


def known_event() -> list[dict]:
    out = []
    for level in LEVELS:
        f = AN.frame("eval", level)
        _, an = AN.detect(f, MIN_DEV, AN.DEFAULTS)
        c, t0, t1 = KNOWN_EVENT
        hit = an[(an["circuit"] == c) & (an["start"] < t1) & (an["end"] > t0)]
        out.append({"level": level, "event": "NE|HVAC left on, 3 Oct 2025 11:00–14:00", "detected": bool(len(hit)),
                    "anomaly": ", ".join(f"{r.id} ({r.level}, {r.dev_kwh:+.2f} kWh)" for r in hit.itertuples())})
    return out


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    allc, quiet, mins = [], [], []
    for level, md in CONFIGS:
        c, q, mn = run_level(level, md)
        allc.append(c), quiet.append(q), mins.append(mn)
        print(f"level {level:.2f}, min dev {md:.0f} Wh: {len(c):,} cases, {q['alerts_per_day']} anomalies/day on real data",
              flush=True)
    cases = pd.concat(allc, ignore_index=True)
    cases["critical"] = cases["anomaly_level"] == "Critical"
    cases.to_csv(OUT / "injection_test_cases_dash.csv.gz", index=False, compression="gzip")

    def summ(by):
        g = cases.groupby(by)
        return g.agg(cases=("detected", "size"), detected_pct=("detected", "mean"),
                     critical_pct=("critical", "mean")).reset_index().assign(
            detected_pct=lambda x: (x["detected_pct"] * 100).round(1),
            critical_pct=lambda x: (x["critical_pct"] * 100).round(1))

    def out(df, name):
        df = df.copy()
        df.insert(0, "sensitivity", [_label(l, m) for l, m in zip(df["level"], df["min_dev_Wh"])])
        df.to_csv(OUT / name, index=False)

    out(summ(["level", "min_dev_Wh", "kind", "magnitude", "hours"]), "injection_detection_by_magnitude_duration_dash.csv")
    out(summ(["level", "min_dev_Wh", "kind", "circuit"]), "injection_detection_by_circuit_dash.csv")
    out(summ(["level", "min_dev_Wh", "kind", "period", "magnitude"]), "injection_detection_by_period_dash.csv")
    out(summ(["level", "min_dev_Wh", "kind", "circuit", "magnitude"]), "injection_detection_by_circuit_magnitude_dash.csv")
    out(pd.concat(mins).assign(threshold_Wh=lambda x: x["min_dev_Wh"]), "injection_minimum_detectable_surplus_dash.csv")
    out(pd.DataFrame(quiet), "injection_quiet_data_alerts_dash.csv")
    ke = pd.DataFrame(known_event())
    ke.insert(0, "sensitivity", [_label(l, 25.0) for l in ke["level"]])
    ke.to_csv(OUT / "injection_known_event_check_dash.csv", index=False)
    meta = {"created_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "settings": CONFIGS, "spike_magnitudes": SPIKES, "drop_magnitudes": DROPS, "hours": HOURS,
            "cases_total": int(len(cases)), "seconds": round(time.time() - t0, 1)}
    (OUT / "injection_meta_dash.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
