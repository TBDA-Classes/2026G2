"""Model comparison (Task 6) — verification and robustness checks behind 22_Model_Comparison_Justification.md.

Run from the repository root:  python Final_Evidence/scripts/model_comparison_checks.py   (needs pandas, numpy, scipy)
Reads only Task6_rev0_03-11/ and TBDA_v1.3_ChronosGBM_29-10/models/blend_frozen_config_v1.3.json; writes
Final_Evidence/analysis/model_comparison/. Nothing is refitted or re-chosen.

  verification_checks.csv     structure, dates, no future information, same actual values, blend = frozen weights, RESULTS.md
  robust_block_seed.csv       pairwise verdicts with bootstrap blocks of 1-72 h and 5 seeds
  robust_diebold_mariano.csv  Diebold-Mariano test (Newey-West, lag 24 h) as a second significance test
  robust_blend_weights.csv    all 231 blend weight sets on validation and test (diagnostic only)
  robust_days.csv             test days on which the Blend has the lower MAE
  robust_selection.csv        validation -> test rank stability of the 6 ML models; best model per horizon
"""
import contextlib, io, json, os, re, sys
from math import erf, sqrt
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT = os.getcwd()
T6 = os.path.join(ROOT, "Task6_rev0_03-11"); P = os.path.join(T6, "results", "predictions")
OUT = os.path.join(ROOT, "Final_Evidence", "analysis", "model_comparison"); os.makedirs(OUT, exist_ok=True)
BLEND = json.load(open(os.path.join(ROOT, "TBDA_v1.3_ChronosGBM_29-10", "models", "blend_frozen_config_v1.3.json")))["horizons"]
os.environ["SCALE_FILE"] = os.path.join(T6, "data", "task6_circuit_scale_train_mean_v1.2.csv")
sys.path.insert(0, T6); import task6_compare as T
HZ = {1: "+1h", 6: "+6h", 24: "day-ahead"}
M16 = ["ML_RandomForest", "ML_Linear", "ML_GBM_v1.3", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3", "ML_Blend_v1.3",
       "B1_last_week", "B2_weekday_hour_median", "B3_persistence"]

# ---------------------------------------------------------------- verification
def load(f):
    d = pd.read_csv(f); d["target_hour"] = pd.to_datetime(d.target_hour, utc=True)
    d["issue"] = pd.to_datetime(d["issue_time"] if "issue_time" in d else d["issue_time_utc"], utc=True)
    d["circ"] = d["zone"] if d.zone.astype(str).str.contains(r"\|").all() else d["circuit_zone"]; return d
D = {f[:-4]: load(os.path.join(P, f)) for f in sorted(os.listdir(P)) if f.endswith(".csv")}
rows = []
def rec(check, ok, detail): rows.append({"check": check, "result": "OK" if ok else "PROBLEM", "detail": detail})
bad = [k for k, d in D.items() if d.circ.nunique() != (8 if ("v1.0" in k or "v1.1" in k) else 16)
       or len(d) != d.circ.nunique() * 168 * 3 or d.duplicated(["circ", "horizon_h", "target_hour"]).any()]
rec("Structure of the 22 prediction files", not bad, f"16 (or 8) circuits x 168 h x 3 horizons, no duplicates; problems: {bad or 'none'}")
SPL = {"test": ("2025-09-29", "2025-10-06"), "validation": ("2025-09-22", "2025-09-29")}
bad = [k for k, d in D.items() if not d.target_hour.between(pd.Timestamp(SPL[k.split('_')[-2]][0], tz="UTC"),
       pd.Timestamp(SPL[k.split('_')[-2]][1], tz="UTC") - pd.Timedelta(hours=1)).all()]
rec("Target hours inside the right split", not bad, f"test 29 Sep-5 Oct, validation 22-28 Sep (UTC); problems: {bad or 'none'}")
bad = []
for k, d in D.items():
    lead = ((d.target_hour - d.issue).dt.total_seconds() / 3600 + 1).round().astype(int)
    ok = (d.target_hour >= d.issue).all() and (lead == d.lead_h).all()
    ok &= (d[d.horizon_h == 24].issue.dt.tz_convert("Europe/Madrid").dt.hour == 0).all()
    if not ok: bad.append(k)
rec("No information from the future", not bad, f"issue time before target, lead consistent, day-ahead issued 00:00 Madrid; problems: {bad or 'none'}")
ref = D["ML_RandomForest_test_predictions"]; bad = []
for k, d in D.items():
    if k.endswith("test_predictions"):
        m = ref.merge(d, on=["circ", "horizon_h", "target_hour"], suffixes=("", "_o")); b = m.actual_Wh.notna() & m.actual_Wh_o.notna()
        if not np.allclose(m.loc[b, "actual_Wh"], m.loc[b, "actual_Wh_o"]): bad.append(k)
rec("Same actual values in every file where valid", not bad, f"problems: {bad or 'none'}")
rec("No negative forecasts", not any((d.predicted_Wh < 0).any() for d in D.values()), "")
mx = 0
for s in ["test", "validation"]:
    k = ["circ", "horizon_h", "target_hour"]
    m = (D[f"ML_Blend_v1.3_{s}_predictions"].merge(D[f"ML_GBM_v1.3_{s}_predictions"], on=k, suffixes=("", "_g"))
         .merge(D[f"ML_ChronosGBM_v1.3_{s}_predictions"], on=k, suffixes=("", "_h")).merge(D[f"ML_Chronos_v1.3_{s}_predictions"], on=k, suffixes=("", "_c")))
    w = m.horizon_h.map(HZ).map(BLEND)
    est = w.map(lambda z: z["w_gbm"]) * m.predicted_Wh_g + w.map(lambda z: z["w_hybrid"]) * m.predicted_Wh_h + w.map(lambda z: z["w_chronos"]) * m.predicted_Wh_c
    mx = max(mx, float(np.abs(est - m.predicted_Wh).max()))
rec("Blend = frozen weighted average of its three parts", mx < 1e-6, f"max difference {mx:.1e} Wh (test and validation)")
mt = pd.read_csv(os.path.join(T6, "results", "task6_test_16circuits", "metrics_with_CI.csv")).query("scope == 'all circuits'")
txt = open(os.path.join(T6, "RESULTS.md")).read(); bad = []
for mod, nm in {"ML_Blend_v1.3": "Blend v1.3", "ML_Chronos_v1.3": "Chronos-Bolt v1.3", "ML_ChronosGBM_v1.3": "ChronosGBM v1.3",
                "ML_GBM_v1.3": "Gradient boosting v1.3", "ML_RandomForest": "Random Forest", "ML_Linear": "Linear Regression",
                "B3_persistence": "Baseline C", "B2_weekday_hour_median": "Baseline B", "B1_last_week": "Baseline A"}.items():
    line = [l for l in txt.split("\n") if l.startswith("| ") and nm in l][0]
    got = [float(x) for x in re.findall(r"\d+\.\d+", "|".join(line.split("|")[2:]))][:3]
    exp = [round(mt[(mt.model == mod) & (mt.horizon == h)].MAE_Wh.iloc[0], 1) for h in HZ.values()]
    if got != exp: bad.append(nm)
rec("Numbers of RESULTS.md = result CSV", not bad, f"main table, 9 models x 3 horizons; differences: {bad or 'none'}")
rec("Hours scored", sorted(mt.n.unique()) == [1911], "1,911 per horizon on 16 circuits = 71% of 2,688")
pd.DataFrame(rows).to_csv(os.path.join(OUT, "verification_checks.csv"), index=False)

# ---------------------------------------------------------------- robustness
def wide(split):
    with contextlib.redirect_stdout(io.StringIO()):
        w, _, _ = T.align([T.load(os.path.join(P, f"{m}_{split}_predictions.csv")) for m in M16])
    return w
W, V = wide("test"), wide("validation")
pairs = [("ML_Blend_v1.3", b) for b in ["B2_weekday_hour_median", "B3_persistence", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3",
                                        "ML_GBM_v1.3", "ML_RandomForest", "ML_Linear"]]
verdict = lambda lo, hi: "better" if hi < 0 else ("worse" if lo > 0 else "tie")
def boot(sub, a, b, block, seed, nb=2000):
    hrs = np.sort(sub.target_hour.unique()); pos = sub.target_hour.map({h: i for i, h in enumerate(hrs)}).to_numpy(); nh = len(hrs)
    ea = np.bincount(pos, np.abs(sub[a] - sub.actual_Wh), nh); eb = np.bincount(pos, np.abs(sub[b] - sub.actual_Wh), nh)
    n = np.bincount(pos, minlength=nh).astype(float); rng = np.random.default_rng(seed); d = np.empty(nb)
    for i in range(nb):
        st = rng.integers(0, nh, int(np.ceil(nh / block))); idx = ((st[:, None] + np.arange(block)[None, :]).ravel() % nh)[:nh]
        d[i] = (ea[idx].sum() - eb[idx].sum()) / n[idx].sum()
    return np.percentile(d, [2.5, 97.5])
def dm(sub, a, b, L=24):
    g = sub.assign(x=np.abs(sub[a] - sub.actual_Wh) - np.abs(sub[b] - sub.actual_Wh)).groupby("target_hour").x.mean().to_numpy()
    e = g - g.mean(); n = len(g); gam = [(e[k:] * e[:n - k]).sum() / n for k in range(L + 1)]
    var = gam[0] + 2 * sum((1 - k / (L + 1)) * gam[k] for k in range(1, L + 1)); z = g.mean() / np.sqrt(var / n)
    return z, 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
r1, r2 = [], []
for h, hn in HZ.items():
    s = W[W.horizon_h == h]
    for a, b in pairs:
        diff = np.abs(s[a] - s.actual_Wh).mean() - np.abs(s[b] - s.actual_Wh).mean()
        row = {"horizon": hn, "model": a, "vs": b, "MAE_diff_Wh": round(diff, 2)}
        for bl in [1, 6, 12, 24, 48, 72]: row[f"block_{bl}h"] = verdict(*boot(s, a, b, bl, 42))
        row["seeds_24h"] = "/".join(verdict(*boot(s, a, b, 24, sd)) for sd in range(5)); r1.append(row)
        z, p = dm(s, a, b); r2.append({"horizon": hn, "model": a, "vs": b, "DM_stat": round(z, 2), "p_value": round(p, 4),
                                       "DM_verdict": ("better" if z < 0 else "worse") if p < 0.05 else "tie"})
pd.DataFrame(r1).to_csv(os.path.join(OUT, "robust_block_seed.csv"), index=False)
pd.DataFrame(r2).to_csv(os.path.join(OUT, "robust_diebold_mariano.csv"), index=False)
grid = [(i / 20, j / 20, round(1 - i / 20 - j / 20, 2)) for i in range(21) for j in range(21 - i)]; r3 = []
for h, hn in HZ.items():
    for nm, Dd in [("validation", V), ("test", W)]:
        s = Dd[Dd.horizon_h == h]; y = s.actual_Wh.to_numpy(); G, Hh, C = (s[c].to_numpy() for c in ["ML_GBM_v1.3", "ML_ChronosGBM_v1.3", "ML_Chronos_v1.3"])
        mae = np.array([np.abs(a * G + b * Hh + c * C - y).mean() for a, b, c in grid]); cw = BLEND[hn]
        ci = grid.index((cw["w_gbm"], cw["w_hybrid"], round(cw["w_chronos"], 2)))
        r3.append({"horizon": hn, "set": nm, "chosen_weights": f'{cw["w_gbm"]}/{cw["w_hybrid"]}/{cw["w_chronos"]}', "MAE_chosen": round(mae[ci], 2),
                   "rank_of_chosen_of_231": int((mae < mae[ci]).sum() + 1), "best_weights": "/".join(map(str, grid[mae.argmin()])),
                   "MAE_best": round(mae.min(), 2), "MAE_equal_thirds": round(np.abs((G + Hh + C) / 3 - y).mean(), 2), "MAE_worst": round(mae.max(), 2)})
pd.DataFrame(r3).to_csv(os.path.join(OUT, "robust_blend_weights.csv"), index=False)
r4 = []
for h, hn in HZ.items():
    s = W[W.horizon_h == h].copy(); s["day"] = s.target_hour.dt.tz_convert("Europe/Madrid").dt.date
    full = s.groupby("day").size() >= 100
    for b in ["B2_weekday_hour_median", "B3_persistence", "ML_GBM_v1.3", "ML_Chronos_v1.3"]:
        win = s.groupby("day").apply(lambda d: np.abs(d["ML_Blend_v1.3"] - d.actual_Wh).mean() < np.abs(d[b] - d.actual_Wh).mean())[full]
        r4.append({"horizon": hn, "vs": b, "days_Blend_better": int(win.sum()), "days": int(full.sum())})
pd.DataFrame(r4).to_csv(os.path.join(OUT, "robust_days.csv"), index=False)
ML = [m for m in M16 if m.startswith("ML")]; r5 = []
for h, hn in HZ.items():
    v, t = V[V.horizon_h == h], W[W.horizon_h == h]
    mv = {m: np.abs(v[m] - v.actual_Wh).mean() for m in ML}; mtt = {m: np.abs(t[m] - t.actual_Wh).mean() for m in ML}
    pick = min(mv, key=mv.get)
    r5.append({"horizon": hn, "spearman_val_vs_test": round(spearmanr([mv[m] for m in ML], [mtt[m] for m in ML]).correlation, 2),
               "best_on_val_by_MAE_Wh": pick, "its_test_MAE": round(mtt[pick], 2), "Blend_test_MAE": round(mtt["ML_Blend_v1.3"], 2),
               "best_on_test": min(mtt, key=mtt.get), "best_test_MAE": round(min(mtt.values()), 2)})
pd.DataFrame(r5).to_csv(os.path.join(OUT, "robust_selection.csv"), index=False)
print("written to", OUT)
