"""
CeDInt — Sprint 3, Task 6: final model comparison
==================================================

Compares any number of models on EXACTLY the same test hours.

INPUT
-----
One CSV per model in the folder `predictions/` (or paths given on the command line),
with at least: model, zone, circuit_zone, horizon_h, target_hour, actual_Wh, predicted_Wh.

The script tolerates the known format differences between teams:
- `zone` / `circuit_zone` swapped (the circuit is always the value containing "|")
- timestamps with or without "+0000"

WHAT IT DOES
------------
1. Normalises every file and checks it (duplicates, missing hours, same actual values).
2. Inner-joins all models on (circuit, horizon, target_hour) and keeps only the hours where
   a valid actual value exists -> every model is scored on identical rows.
3. MAE and RMSE (Wh) per model x horizon x group (all 16 circuits, trained NE/NW, unseen SE/SW)
   and per circuit.
4. 95% confidence intervals with a circular moving-block bootstrap:
   blocks of 24 consecutive test hours, all circuits of an hour kept together
   (errors are correlated in time and across circuits).
5. Paired comparison: CI of the MAE difference between every pair of models.
   If the CI does not contain 0, the difference is significant.
6. Best model per horizon and per zone (NE, NW, SE, SW) with the significance verdict.

RUN
---
pip install pandas numpy matplotlib
python task6_compare.py results/predictions/*_test_predictions.csv
"""

import sys
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd

N_BOOT = 2000
BLOCK_H = 24
SEED = 42
import os
OUT = Path(os.environ.get("OUT_DIR", Path(__file__).resolve().parent / "results" / "task6_comparison"))
HORIZON_NAME = {1: "+1h", 6: "+6h", 24: "day-ahead"}
SPLIT_LABEL = os.environ.get("SPLIT_LABEL", "Test")
SCALE_FILE = os.environ.get("SCALE_FILE")          # circuit,scale_Wh  -> scaled MAE (MAE / training mean)
EVENTS_FILE = os.environ.get("EVENTS_FILE")        # circuit,target_hour,event
EXCLUDE_EVENTS = os.environ.get("EXCLUDE_EVENTS") == "1"
TZ_LOCAL = "Europe/Madrid"
TRAINED_ZONES = {"NE", "NW"}


# ---------------------------------------------------------------- 1. load + normalise
def load(path):
    d = pd.read_csv(path)
    need = {"model", "zone", "circuit_zone", "horizon_h", "target_hour",
            "actual_Wh", "predicted_Wh"}
    missing = need - set(d.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")

    # the circuit is the column whose values contain "|"
    if d["zone"].astype(str).str.contains(r"\|").all():
        circuit, area = d["zone"], d["circuit_zone"]
    else:
        circuit, area = d["circuit_zone"], d["zone"]

    out = pd.DataFrame({
        "model": d["model"].astype(str),
        "circuit": circuit.astype(str),
        "zone": area.astype(str),
        "horizon_h": d["horizon_h"].astype(int),
        "target_hour": pd.to_datetime(d["target_hour"], utc=True),
        "actual_Wh": pd.to_numeric(d["actual_Wh"], errors="coerce"),
        "predicted_Wh": pd.to_numeric(d["predicted_Wh"], errors="coerce"),
    })
    if "lead_h" in d.columns:
        out["lead_h"] = d["lead_h"]

    dup = out.duplicated(["circuit", "horizon_h", "target_hour"]).sum()
    print(f"{Path(path).name}: model={out.model.iloc[0]}, rows={len(out):,}, "
          f"circuits={out.circuit.nunique()}, duplicates={dup}, "
          f"rows with actual={out.actual_Wh.notna().sum():,}")
    if dup:
        raise ValueError(f"{path}: duplicated (circuit, horizon, hour) rows")
    return out


# ---------------------------------------------------------------- 2. align
def align(frames):
    key = ["circuit", "zone", "horizon_h", "target_hour"]
    base = frames[0][key + ["actual_Wh"] + (["lead_h"] if "lead_h" in frames[0] else [])]
    wide = base.copy()
    checks = []
    for f in frames:
        name = f.model.iloc[0]
        m = wide.merge(f[key + ["actual_Wh", "predicted_Wh"]], on=key, how="inner",
                       suffixes=("", "_other"))
        both = m.actual_Wh.notna() & m.actual_Wh_other.notna()
        same_actual = np.isclose(m.loc[both, "actual_Wh"], m.loc[both, "actual_Wh_other"]).mean()
        same_missing = (m.actual_Wh.isna() == m.actual_Wh_other.isna()).mean()
        checks.append({"model": name, "rows_matched": len(m),
                       "same_actual_values_%": round(100 * same_actual, 2),
                       "same_missing_hours_%": round(100 * same_missing, 2)})
        m.loc[m.actual_Wh_other.isna(), "actual_Wh"] = np.nan        # keep only hours valid in EVERY file
        wide = m.drop(columns="actual_Wh_other").rename(columns={"predicted_Wh": name})
    models = [f.model.iloc[0] for f in frames]
    before = len(wide)
    wide = wide.dropna(subset=["actual_Wh"] + models).reset_index(drop=True)
    if EXCLUDE_EVENTS:
        ev = pd.read_csv(EVENTS_FILE); ev["target_hour"] = pd.to_datetime(ev.target_hour, utc=True)
        k = wide.set_index(["circuit", "target_hour"]).index.isin(ev.set_index(["circuit", "target_hour"]).index)
        print(f"Excluding {k.sum():,} rows of known events ({EVENTS_FILE})")
        wide = wide[~k].reset_index(drop=True)
    wide["group"] = np.where(wide.zone.isin(TRAINED_ZONES), "NE/NW circuits", "SE/SW circuits")
    print(f"\nAligned rows: {before:,} -> {len(wide):,} with a valid actual for every model")
    return wide, models, pd.DataFrame(checks)


# ---------------------------------------------------------------- 3-5. metrics + bootstrap
_SCALE = {}
def load_scale():
    if not SCALE_FILE:
        return None
    if "s" not in _SCALE:
        _SCALE["s"] = pd.read_csv(SCALE_FILE).set_index("circuit")["scale_Wh"]
    return _SCALE["s"]


def block_indices(hours, rng):
    """Circular moving-block bootstrap over the ordered list of test hours."""
    n = len(hours)
    n_blocks = int(np.ceil(n / BLOCK_H))
    starts = rng.integers(0, n, n_blocks)
    idx = (starts[:, None] + np.arange(BLOCK_H)[None, :]).ravel() % n
    return idx[:n]


def evaluate(sub, models, rng_seed):
    """Point MAE/RMSE + bootstrap CIs for every model and every pair difference."""
    hours = np.sort(sub.target_hour.unique())
    hour_pos = {h: i for i, h in enumerate(hours)}
    pos = sub.target_hour.map(hour_pos).to_numpy()
    y = sub.actual_Wh.to_numpy()
    err = {m: sub[m].to_numpy() - y for m in models}

    # per-hour sums so each bootstrap draw is cheap
    n_h = np.bincount(pos, minlength=len(hours)).astype(float)
    abs_h = {m: np.bincount(pos, np.abs(err[m]), len(hours)) for m in models}
    sq_h = {m: np.bincount(pos, err[m] ** 2, len(hours)) for m in models}
    y_h = np.bincount(pos, np.abs(y), len(hours))

    scale = load_scale()
    if scale is not None:
        circ = sub.circuit.to_numpy(); cats = np.unique(circ); ci = np.searchsorted(cats, circ)
        sc = scale.reindex(cats).to_numpy()
        cell = pos * len(cats) + ci; ncell = len(hours) * len(cats)
        n_hc = np.bincount(cell, minlength=ncell).reshape(len(hours), len(cats)).astype(float)
        abs_hc = {m: np.bincount(cell, np.abs(err[m]), ncell).reshape(len(hours), len(cats)) for m in models}
        def smae(a, n):
            with np.errstate(invalid="ignore", divide="ignore"):
                return np.nanmean((a / n) / sc)
        boot_smae = {m: np.empty(N_BOOT) for m in models}
    rng = np.random.default_rng(rng_seed)
    boot_mae = {m: np.empty(N_BOOT) for m in models}
    boot_rmse = {m: np.empty(N_BOOT) for m in models}
    boot_wape = {m: np.empty(N_BOOT) for m in models}
    for b in range(N_BOOT):
        idx = block_indices(hours, rng)
        n = n_h[idx].sum()
        for m in models:
            boot_mae[m][b] = abs_h[m][idx].sum() / n
            boot_rmse[m][b] = np.sqrt(sq_h[m][idx].sum() / n)
            boot_wape[m][b] = 100 * abs_h[m][idx].sum() / y_h[idx].sum()
            if scale is not None:
                boot_smae[m][b] = smae(abs_hc[m][idx].sum(0), n_hc[idx].sum(0))

    rows = []
    for m in models:
        rows.append({
            "model": m, "n": len(sub),
            "MAE_Wh": np.abs(err[m]).mean(),
            "MAE_lo": np.percentile(boot_mae[m], 2.5),
            "MAE_hi": np.percentile(boot_mae[m], 97.5),
            "RMSE_Wh": np.sqrt((err[m] ** 2).mean()),
            "RMSE_lo": np.percentile(boot_rmse[m], 2.5),
            "RMSE_hi": np.percentile(boot_rmse[m], 97.5),
            "WAPE_%": 100 * np.abs(err[m]).sum() / np.abs(y).sum(),
            "WAPE_lo": np.percentile(boot_wape[m], 2.5),
            "WAPE_hi": np.percentile(boot_wape[m], 97.5),
        })
        if scale is not None:
            rows[-1].update({"scaled_MAE": smae(abs_hc[m].sum(0), n_hc.sum(0)),
                             "sMAE_lo": np.percentile(boot_smae[m], 2.5), "sMAE_hi": np.percentile(boot_smae[m], 97.5)})
    pairs = []
    for a, b in combinations(models, 2):
        diff = boot_mae[a] - boot_mae[b]
        point = np.abs(err[a]).mean() - np.abs(err[b]).mean()
        lo, hi = np.percentile(diff, [2.5, 97.5])
        p = 2 * min((diff <= 0).mean(), (diff >= 0).mean())
        pairs.append({"model_A": a, "model_B": b, "MAE_A_minus_B": point,
                      "diff_lo": lo, "diff_hi": hi, "p_value": min(p, 1.0),
                      "significant": not (lo <= 0 <= hi),
                      "better": (a if point < 0 else b) if not (lo <= 0 <= hi) else "tie"})
        if scale is not None:
            d2 = boot_smae[a] - boot_smae[b]; lo2, hi2 = np.percentile(d2, [2.5, 97.5])
            pairs[-1].update({"sMAE_A_minus_B": smae(abs_hc[a].sum(0), n_hc.sum(0)) - smae(abs_hc[b].sum(0), n_hc.sum(0)),
                              "sMAE_diff_lo": lo2, "sMAE_diff_hi": hi2, "sMAE_significant": not (lo2 <= 0 <= hi2)})
    return pd.DataFrame(rows), pd.DataFrame(pairs)


def best_with_verdict(metrics, pairs):
    best = metrics.sort_values("MAE_Wh").iloc[0].model
    second = metrics.sort_values("MAE_Wh").iloc[1].model
    p = pairs[((pairs.model_A == best) & (pairs.model_B == second))
              | ((pairs.model_A == second) & (pairs.model_B == best))].iloc[0]
    out = [best, second, ("significant" if p.significant else "not significant (tie)")]
    if "scaled_MAE" in metrics:
        o = metrics.sort_values("scaled_MAE"); bs, ss = o.iloc[0].model, o.iloc[1].model
        q = pairs[((pairs.model_A == bs) & (pairs.model_B == ss)) | ((pairs.model_A == ss) & (pairs.model_B == bs))].iloc[0]
        out += [bs, ss, "significant" if q.sMAE_significant else "not significant (tie)"]
    return out


# ---------------------------------------------------------------- 6. run
def main(paths):
    OUT.mkdir(exist_ok=True)
    print("=" * 70 + "\nLOADING\n" + "=" * 70)
    frames = [load(p) for p in paths]
    wide, models, checks = align(frames)
    print("\nConsistency checks (vs the first file):")
    print(checks.to_string(index=False))
    checks.to_csv(OUT / "alignment_checks.csv", index=False)

    all_metrics, all_pairs, best_rows = [], [], []
    seed = SEED
    scopes = [("all circuits", lambda d: d),
              ("NE/NW circuits", lambda d: d[d.group == "NE/NW circuits"]),
              ("SE/SW circuits", lambda d: d[d.group == "SE/SW circuits"])]
    scopes += [(f"zone {z}", (lambda z: lambda d: d[d.zone == z])(z))
               for z in sorted(wide.zone.unique())]

    for h in sorted(wide.horizon_h.unique()):
        for scope, f in scopes:
            sub = f(wide[wide.horizon_h == h])
            if sub.empty:
                continue
            seed += 1
            met, pairs = evaluate(sub, models, seed)
            met.insert(0, "scope", scope)
            met.insert(0, "horizon", HORIZON_NAME.get(h, h))
            pairs.insert(0, "scope", scope)
            pairs.insert(0, "horizon", HORIZON_NAME.get(h, h))
            all_metrics.append(met)
            all_pairs.append(pairs)
            r = best_with_verdict(met, pairs)
            row = {"horizon": HORIZON_NAME.get(h, h), "scope": scope, "best_model": r[0], "second": r[1], "difference": r[2]}
            if len(r) > 3:
                row.update({"best_by_scaled_MAE": r[3], "second_scaled": r[4], "difference_scaled": r[5]})
            best_rows.append(row)

    metrics = pd.concat(all_metrics, ignore_index=True)
    pairs = pd.concat(all_pairs, ignore_index=True)
    best = pd.DataFrame(best_rows)

    # per-circuit point metrics (no CI: too few hours for some circuits)
    per_circuit = (wide.melt(id_vars=["circuit", "zone", "horizon_h", "actual_Wh"],
                             value_vars=models, var_name="model", value_name="pred")
                   .assign(ae=lambda d: (d.pred - d.actual_Wh).abs(),
                           se=lambda d: (d.pred - d.actual_Wh) ** 2)
                   .groupby(["horizon_h", "zone", "circuit", "model"])
                   .agg(n=("ae", "size"), MAE_Wh=("ae", "mean"), RMSE_Wh=("se", "mean"))
                   .assign(RMSE_Wh=lambda d: np.sqrt(d.RMSE_Wh)).reset_index())

    long = (wide.melt(id_vars=["circuit", "zone", "group", "horizon_h", "target_hour", "actual_Wh"] + (["lead_h"] if "lead_h" in wide else []),
                      value_vars=models, var_name="model", value_name="pred")
            .assign(ae=lambda d: (d.pred - d.actual_Wh).abs()))
    loc = long.target_hour.dt.tz_convert(TZ_LOCAL)
    long["hour_local"] = loc.dt.hour
    long["day_type"] = np.where(loc.dt.weekday >= 5, "weekend", "weekday")
    long["date_local"] = loc.dt.date.astype(str)
    long["horizon"] = long.horizon_h.map(HORIZON_NAME)
    sc = load_scale()
    if sc is not None:
        long["sae"] = long.ae / long.circuit.map(sc)
    def tab(by, fn):
        cols = {"MAE_Wh": ("ae", "mean")} | ({"scaled_MAE_mean_rows": ("sae", "mean")} if sc is not None else {})
        t = long.groupby(by + ["model"], observed=True).agg(n=("ae", "size"), **cols).reset_index()
        t.round(3).to_csv(OUT / fn, index=False)
    tab(["horizon", "hour_local"], "error_by_hour_of_day.csv")
    tab(["horizon", "day_type"], "error_by_day_type.csv")
    tab(["horizon", "date_local"], "error_by_date.csv")
    if "lead_h" in long:
        da = long[long.horizon == "day-ahead"].copy()
        da["hours_ahead"] = pd.cut(da.lead_h, [0, 3, 6, 12, 18, 24], labels=["1-3", "4-6", "7-12", "13-18", "19-24"])
        cols = {"MAE_Wh": ("ae", "mean")} | ({"scaled_MAE_mean_rows": ("sae", "mean")} if sc is not None else {})
        da.groupby(["hours_ahead", "model"], observed=True).agg(n=("ae", "size"), **cols).reset_index().round(3).to_csv(OUT / "error_day_ahead_by_hours_ahead.csv", index=False)
    # circuits where each model beats each baseline / each other model (per-circuit MAE)
    pc = long.groupby(["horizon", "circuit", "model"]).ae.mean().unstack()
    wins = []
    for hz, g in pc.groupby(level=0):
        for a in models:
            for b in models:
                if a != b:
                    wins.append({"horizon": hz, "model": a, "vs": b, "circuits_better": int((g[a] < g[b]).sum()), "circuits": len(g)})
    pd.DataFrame(wins).to_csv(OUT / "circuit_wins.csv", index=False)

    metrics.round(4).to_csv(OUT / "metrics_with_CI.csv", index=False)
    pairs.round(4).to_csv(OUT / "pairwise_differences.csv", index=False)
    best.to_csv(OUT / "best_model_per_scope.csv", index=False)
    per_circuit.round(2).to_csv(OUT / "metrics_per_circuit.csv", index=False)

    pd.set_option("display.width", 160)
    print("\n" + "=" * 70 + "\nMAE / RMSE WITH 95% CI (block bootstrap, 24h blocks)\n" + "=" * 70)
    show = metrics[metrics.scope.isin(["all circuits", "NE/NW circuits", "SE/SW circuits"])]
    print(show.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
    print("\n" + "=" * 70 + "\nPAIRWISE MAE DIFFERENCES (A - B, negative = A better)\n" + "=" * 70)
    print(pairs[pairs.scope == "all circuits"].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\n" + "=" * 70 + "\nBEST MODEL\n" + "=" * 70)
    print(best.to_string(index=False))

    plot(metrics, models)
    print(f"\nResults in {OUT}")


def plot(metrics, models):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    scopes = [s for s in ["all circuits", "NE/NW circuits", "SE/SW circuits"] if s in set(metrics.scope)]
    horizons = list(dict.fromkeys(metrics.horizon))
    fig, axes = plt.subplots(1, len(scopes), figsize=(5.5 * len(scopes), 4.4), sharey=False, squeeze=False)
    axes = axes[0]
    width = 0.8 / len(models)
    for ax, sc in zip(axes, scopes):
        for j, m in enumerate(models):
            r = metrics[(metrics.scope == sc) & (metrics.model == m)].set_index("horizon").loc[horizons]
            x = np.arange(len(horizons)) + j * width
            ax.bar(x, r.MAE_Wh, width, label=m,
                   yerr=[r.MAE_Wh - r.MAE_lo, r.MAE_hi - r.MAE_Wh], capsize=3)
        ax.set_xticks(np.arange(len(horizons)) + width * (len(models) - 1) / 2, horizons)
        ax.set_title(sc)
        ax.set_ylabel(f"{SPLIT_LABEL} MAE (Wh), 95% CI")
        ax.grid(axis="y", alpha=.3)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "mae_with_ci.png", dpi=150)


if __name__ == "__main__":
    files = sys.argv[1:] or sorted(str(p) for p in (Path(__file__).parent / "results" / "predictions").glob("*_test_predictions.csv"))
    if len(files) < 2:
        sys.exit("Give at least two prediction CSVs.")
    main(files)
