"""Build the data file of the TBDA CeDInt-SEF dashboard (data.json / data.js).

Inputs (all read-only, produced by the team):
  * Task6 predictions   : Task6_rev0_03-11/results/predictions/ML_Blend_v1.3_{validation,test}_predictions.csv
  * Chronos-Bolt band   : TBDA_v1.3_ChronosGBM_29-10/results/chronos_{validation,test}_predictions_v1.3.parquet  (q10, q50, q90)
  * Hourly dataset v1.2 : TBDA_v1.3_ChronosGBM_29-10/derived/Storey1_hourly_v1.2.parquet  (quality flags)
Output: data.json   (everything the dashboard shows; no model is run at display time)

Method (documented decisions, see docs/02_Assumptions_and_Decisions.md):
  expected = Blend v1.3 day-ahead forecast (issued 00:00 Europe/Madrid)
  normal range = Chronos-Bolt v1.3 q10-q90 band (observed coverage ~80-82 %)
  alert hour = actual above the upper limit AND excess >= max(floor Wh, share x circuit mean load)
  consecutive alert hours of one circuit = one alert; data-quality-flagged hours never raise alerts
  occupied = weekdays (not public holidays) 07:00-20:00 Europe/Madrid (validated against the NW/SE motion detectors)
"""
import json, argparse
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent      # package folder; the repository root is one level up
REPO = ROOT.parent
ap = argparse.ArgumentParser()
ap.add_argument("--model-dir", default=str(REPO / "TBDA_v1.3_ChronosGBM_29-10"))
ap.add_argument("--task6-dir", default=str(REPO / "Task6_rev0_03-11" / "results" / "predictions"))
ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "data.json"))
args = ap.parse_args()
MD, T6 = Path(args.model_dir), Path(args.task6_dir)

START = pd.Timestamp("2025-09-22 00:00", tz="UTC"); END = pd.Timestamp("2025-10-06 00:00", tz="UTC")
IDX = pd.date_range(START, END, freq="h", inclusive="left"); N = len(IDX)
SENS = {"Strict": (0.20, 40.0), "Balanced": (0.10, 20.0), "Sensitive": (0.05, 10.0)}   # (share of circuit mean load, floor in Wh)
HIGH_KWH, HIGH_H, HIGH_OOH_KWH = 1.0, 6, 0.5
OCC_START, OCC_END = 7, 20
LABELS = {"Lighting": "Lighting", "Emerg. Lighting": "Emergency lighting", "Plugs & Sockets": "Plugs & sockets", "HVAC": "HVAC",
          "Hand Dryer": "Hand dryers", "RACK": "IT rack"}

# ---------------------------------------------------------------- forecasts + band
frames = []
for s in ["validation", "test"]:
    b = pd.read_csv(T6 / f"ML_Blend_v1.3_{s}_predictions.csv")
    b = b[b.horizon_h == 24].copy(); b["t"] = pd.to_datetime(b.target_hour, utc=True)
    c = pd.read_parquet(MD / "results" / f"chronos_{s}_predictions_v1.3.parquet")
    c = c[c.horizon == "day-ahead"].copy(); c["t"] = pd.to_datetime(c.target_time, utc=True)
    m = b.merge(c[["series_id", "t", "q10", "q50", "q90"]], left_on=["zone", "t"], right_on=["series_id", "t"], how="left")
    frames.append(m.rename(columns={"zone": "sid", "actual_Wh": "actual", "predicted_Wh": "expected"})[["sid", "t", "actual", "expected", "q10", "q90"]])
F = pd.concat(frames); F = F[(F.t >= START) & (F.t < END)]
sids = sorted(F.sid.unique(), key=lambda s: (["NW", "NE", "SW", "SE"].index(s.split("|")[0]), s))
F["hi"] = F[["q90", "expected"]].max(axis=1); F["lo"] = np.minimum(F.q10, F.expected).clip(lower=0)   # expected always inside the band
F["expected"] = F.expected.clip(lower=0)

# ---------------------------------------------------------------- quality flags
H = pd.read_parquet(MD / "derived" / "Storey1_hourly_v1.2.parquet")
H = H[(H.hour_utc >= START) & (H.hour_utc < END)].set_index(["series_id", "hour_utc"])
def reason(sid, t):
    if (sid, t) not in H.index: return "No readings (sensor gap)"
    r = H.loc[(sid, t)]
    if r.energy_inconsistent: return "Energy higher than the measured power allows"
    if r.energy_catch_up: return "Energy caught up after a gap in readings"
    if r.energy_pre_outage: return "Reading interrupted before an outage"
    if not r.energy_valid: return "Reading failed the validity rules"
    return "Missing value"

# ---------------------------------------------------------------- calendar / occupancy
loc = IDX.tz_convert("Europe/Madrid")
hol = np.zeros(N, bool)   # no public holiday in the window (config HOLIDAY ES/MD)
occ = (loc.dayofweek < 5) & (loc.hour >= OCC_START) & (loc.hour < OCC_END) & ~hol
ooh = ~occ

def fmt(t):  # local time label
    t = pd.Timestamp(t).tz_convert("Europe/Madrid"); return t.strftime("%a %d %b %H:%M")

circuits, A, E, LO, HI, DQ = [], [], [], [], [], []
issues = []
for k, sid in enumerate(sids):
    g = F[F.sid == sid].drop_duplicates("t").set_index("t").reindex(IDX)
    z, l = sid.split("|")
    circuits.append(dict(id=sid, zone=z, load=l, label=LABELS.get(l, l), mean=float(np.nanmean(g.actual))))
    A.append([None if np.isnan(v) else round(float(v), 1) for v in g.actual])
    E.append([None if np.isnan(v) else round(float(v), 1) for v in g.expected])
    LO.append([None if np.isnan(v) else round(float(v), 1) for v in g.lo])
    HI.append([None if np.isnan(v) else round(float(v), 1) for v in g.hi])
    miss = g.actual.isna().values
    # data-quality issues: runs of missing actual with the same reason
    rs = [reason(sid, t) if m else "" for t, m in zip(IDX, miss)]
    i = 0
    while i < N:
        if rs[i]:
            j = i
            while j + 1 < N and rs[j + 1] == rs[i]: j += 1
            issues.append(dict(c=k, s=i, e=j + 1, reason=rs[i])); i = j + 1
        else: i += 1

# ---------------------------------------------------------------- detection for the 3 sensitivities
def explain(c, s, e, exc_kwh, ooh_share):
    when = f"{fmt(IDX[s])} to {(IDX[e - 1] + pd.Timedelta(hours=1)).tz_convert('Europe/Madrid').strftime('%H:%M')}"
    where = "mostly outside occupied hours" if ooh_share >= .5 else "during occupied hours"
    return (f"{c['label']} in zone {c['zone']} used {exc_kwh:.1f} kWh more than expected between {when}, {where}. "
            f"The measurement itself is valid, so this is a candidate for unnecessary use.")

det = {}
for name, (frac, floor) in SENS.items():
    ev, hrs = [], []
    for k, c in enumerate(circuits):
        a, ex, hi = (np.array([np.nan if v is None else v for v in x]) for x in (A[k], E[k], HI[k]))
        excess = np.clip(a - ex, 0, None)
        above = (a > hi) & (excess >= max(floor, frac * c["mean"])) & ~np.isnan(a)
        i = 0
        while i < N:
            if above[i]:
                j = i
                while j + 1 < N and above[j + 1]: j += 1
                sl = slice(i, j + 1); n = j - i + 1
                kwh = excess[sl].sum() / 1000; osh = float(ooh[sl].mean())
                high = kwh >= HIGH_KWH or n >= HIGH_H or (osh >= .5 and kwh >= HIGH_OOH_KWH)
                eid = len(ev)
                ev.append(dict(id=f"A{eid + 1:03d}", c=k, s=i, e=j + 1, n=n, actual=round(float(a[sl].sum()) / 1000, 3),
                               expected=round(float(ex[sl].sum()) / 1000, 3), excess=round(float(kwh), 3), peak=round(float(excess[sl].max()), 1),
                               ooh=round(osh, 2), sev="High" if high else "Warning", why=explain(c, i, j + 1, kwh, osh)))
                for h in range(i, j + 1): hrs.append([k, h, round(float(excess[h]), 1), eid])
                i = j + 1
            else: i += 1
    # order: High first then by excess, ids re-numbered
    order = sorted(range(len(ev)), key=lambda q: (ev[q]["sev"] != "High", -ev[q]["excess"]))
    remap = {old: new for new, old in enumerate(order)}
    ev2 = []
    for new, old in enumerate(order):
        d = dict(ev[old]); d["id"] = f"A{new + 1:03d}"; ev2.append(d)
    hrs = [[h[0], h[1], h[2], remap[h[3]]] for h in hrs]
    det[name] = dict(events=ev2, hours=hrs)

# ---------------------------------------------------------------- reliability + context tables
def rd(n):
    p = REPO / "Sprint4_Task4_Documentation" / "analysis" / n
    return pd.read_csv(p) if p.exists() else None
acc = rd("accuracy_metrics_MAPE_CVRMSE.csv"); band = rd("band_coverage_chronos.csv"); stb = rd("standby_baseline_by_circuit.csv")
occp = rd("occupancy_profile_by_hour.csv"); wi = rd("W_I_vs_energy.csv"); bcirc = rd("band_coverage_by_circuit_test.csv")
def recs(df): return [] if df is None else json.loads(df.round(2).to_json(orient="records"))

known = {}
for name in SENS:
    k = next(i for i, c in enumerate(circuits) if c["id"] == "NE|HVAC")
    probe = pd.Timestamp("2025-10-03 10:00", tz="UTC")
    hit = [e for e in det[name]["events"] if e["c"] == k and IDX[e["s"]] <= probe < IDX[e["e"] - 1] + pd.Timedelta(hours=1)]
    known[name] = bool(hit)

data = dict(
    meta=dict(t0=int(START.timestamp() * 1000), n=N, model="Blend v1.3", band="Chronos-Bolt v1.3 q10-q90", occ=[OCC_START, OCC_END],
              sens={k: dict(share=v[0], floor=v[1]) for k, v in SENS.items()}, known_event_detected=known),
    circuits=circuits, actual=A, expected=E, lo=LO, hi=HI, ooh=[int(x) for x in ooh], issues=issues, det=det,
    reliab=dict(accuracy=recs(acc), band=recs(band), band_circuit=recs(bcirc), standby=recs(stb), occupancy=recs(occp), wi=recs(wi)),
)
Path(args.out).write_text(json.dumps(data, separators=(",", ":")))
tot = sum(len(v["events"]) for v in det.values())
print(f"{N} hours x {len(sids)} circuits; events:", {k: len(v['events']) for k, v in det.items()}, "issues:", len(issues), "known event NE|HVAC 3 Oct:", known)
