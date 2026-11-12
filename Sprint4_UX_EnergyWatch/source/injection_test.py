"""Synthetic anomaly-injection test of the detector (backlog PB-38).

Question answered: if a circuit used an extra X Wh every hour for D hours, how often would the dashboard raise an alert,
at each sensitivity?  The detector is the one of build_data.py, re-implemented here on data.json (same rule).

Design
  * Injection = additive surplus on the ACTUAL series only (forecast and normal range stay as produced by the model).
  * Magnitude  : 25 %, 50 %, 100 %, 200 % of the circuit's mean hourly load.
  * Duration   : 1, 3, 6 hours.
  * Time of day: occupied hours (weekdays 07-20 Madrid) or out of hours (nights, weekends).
  * Start      : every possible start hour of the 14-day window where all injected hours have a valid reading and
                 no real alert already overlaps them (so a hit is caused by the injection).
  * Hit        : an alert of that circuit overlaps the injected hours after injection. Also reported: severity High.
  * Quiet-data check: alerts per day on the unmodified data = what the user sees without any injection.
Limits: synthetic cases measure sensitivity, not the real false-alarm rate (real anomalies are unknown); the forecast
is not re-estimated after an injection, which is correct for an unforeseen event.
Usage: python injection_test.py [data.json]   (writes ../analysis/injection_*.csv and adds reliab.inject to data.json)
"""
import json, sys, itertools
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data.json"
D = json.loads(path.read_text()); N = D["meta"]["n"]; C = D["circuits"]
arr = lambda x: np.array([[np.nan if v is None else v for v in r] for r in x])
A, E, HI = arr(D["actual"]), arr(D["expected"]), arr(D["hi"]); ooh = np.array(D["ooh"], bool)
SENS = {k: (v["share"], v["floor"]) for k, v in D["meta"]["sens"].items()}
HIGH_KWH, HIGH_H, HIGH_OOH = 1.0, 6, 0.5

def alerts(a, k, frac, floor):
    """Return list of (start, end_exclusive, kwh, high) for circuit k on series a."""
    exc = np.clip(a - E[k], 0, None)
    flag = (a > HI[k]) & (exc >= max(floor, frac * C[k]["mean"])) & ~np.isnan(a)
    out, i = [], 0
    while i < N:
        if flag[i]:
            j = i
            while j + 1 < N and flag[j + 1]: j += 1
            kwh = exc[i:j + 1].sum() / 1000; n = j - i + 1; osh = ooh[i:j + 1].mean()
            out.append((i, j + 1, kwh, kwh >= HIGH_KWH or n >= HIGH_H or (osh >= .5 and kwh >= HIGH_OOH))); i = j + 1
        else: i += 1
    return out

MAGS, DURS = [0.25, 0.5, 1.0, 2.0], [1, 3, 6]
rows = []
for sname, (frac, floor) in SENS.items():
    for k, c in enumerate(C):
        base = alerts(A[k], k, frac, floor)
        real = np.zeros(N, bool)
        for s, e, *_ in base: real[s:e] = True
        for m, d in itertools.product(MAGS, DURS):
            for start in range(0, N - d + 1):
                win = slice(start, start + d)
                if np.isnan(A[k][win]).any() or real[win].any() or np.isnan(E[k][win]).any(): continue
                part = "out of hours" if ooh[win].all() else ("occupied" if (~ooh[win]).all() else None)
                if part is None: continue
                a2 = A[k].copy(); a2[win] += m * C[k]["mean"]
                hit = [al for al in alerts(a2, k, frac, floor) if al[0] < start + d and al[1] > start]
                rows.append(dict(sensitivity=sname, circuit=c["id"], magnitude=m, hours=d, period=part,
                                 detected=int(bool(hit)), high=int(any(h[3] for h in hit)), injected_kwh=m * c["mean"] * d / 1000))
R = pd.DataFrame(rows)
out = HERE.parent / "analysis"; out.mkdir(exist_ok=True)
R.to_csv(out / "injection_test_cases.csv.gz", index=False)

g = lambda cols: R.groupby(cols).agg(cases=("detected", "size"), detected_pct=("detected", "mean"), high_pct=("high", "mean")).reset_index()
S1 = g(["sensitivity", "magnitude", "hours"]); S2 = g(["sensitivity", "period", "magnitude"]); S3 = g(["sensitivity", "circuit"])
for s in (S1, S2, S3): s[["detected_pct", "high_pct"]] = (s[["detected_pct", "high_pct"]] * 100).round(1)
S1.to_csv(out / "injection_detection_by_magnitude_duration.csv", index=False)
S2.to_csv(out / "injection_detection_by_period.csv", index=False)
S3.to_csv(out / "injection_detection_by_circuit.csv", index=False)

# quiet-data reference: alerts per day on the real, unmodified data
quiet = []
for sname, (frac, floor) in SENS.items():
    n = sum(len(alerts(A[k], k, frac, floor)) for k in range(len(C)))
    quiet.append(dict(sensitivity=sname, alerts_14_days=n, alerts_per_day=round(n / 14, 1)))
pd.DataFrame(quiet).to_csv(out / "injection_quiet_data_alerts.csv", index=False)

# smallest sustained surplus (Wh per hour above the forecast) that raises an alert, per circuit and sensitivity:
# the surplus must exceed BOTH the sensitivity threshold and the distance from the forecast to the upper band limit
md = []
for sname, (frac, floor) in SENS.items():
    for k, c in enumerate(C):
        thr = max(floor, frac * c["mean"]); need = np.maximum(thr, HI[k] - E[k]); need = need[~np.isnan(need)]
        md.append(dict(sensitivity=sname, circuit=c["id"], mean_load_Wh=round(c["mean"], 1), threshold_Wh=round(thr, 1),
                       median_min_surplus_Wh=round(float(np.median(need)), 1), median_min_surplus_pct_of_mean=round(100 * float(np.median(need)) / c["mean"], 0),
                       binding="sensitivity floor" if np.median(thr - (HI[k] - E[k])[~np.isnan(HI[k] - E[k])] > 0) >= 0 and thr >= np.median(HI[k][~np.isnan(HI[k])] - E[k][~np.isnan(E[k])]) else "forecast band"))
MD = pd.DataFrame(md); MD.to_csv(out / "injection_minimum_detectable_surplus.csv", index=False)
summary = dict(min_detectable=json.loads(MD[MD.sensitivity.isin(["Strict","Balanced","Sensitive"])].to_json(orient="records")), by_mag_dur=json.loads(S1.to_json(orient="records")), by_period=json.loads(S2.to_json(orient="records")),
               quiet=quiet, n_cases=int(len(R) / len(SENS)))
D["reliab"]["inject"] = summary
path.write_text(json.dumps(D, separators=(",", ":")))
print(f"{len(R)} injected cases ({len(R)//len(SENS)} per sensitivity)")
print(S1[S1.sensitivity == "Balanced"].pivot(index="magnitude", columns="hours", values="detected_pct"))
print(S2[S2.sensitivity == "Balanced"].pivot(index="magnitude", columns="period", values="detected_pct"))
print(pd.DataFrame(quiet))
