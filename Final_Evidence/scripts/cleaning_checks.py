"""Data-cleaning checks for the final evidence pack (TBDA Group 2, 17 Nov 2026).

Check A - do the sensors flagged by the cleaning (sensor_quality_<ZONE>.csv) change the conclusions?
    Flagged: SW Lighting (counter_biased, counter runs at 0.707 of power) and the four circuits
    below the 1 Wh counter resolution (NE HVAC, NW Hand Dryer, SE Emerg. Lighting, SW Hand Dryer).
    A1  Task 6 test comparison re-run (same script, same hours) on: all 16 / without SW Lighting /
        without the 5 flagged circuits.
    A2  Model selection rule D10 (mean scaled MAE on the 15 training circuits, tie 0.005, then
        scaled RMSE) re-computed on the v1.3 validation forecasts with and without the flagged
        circuits. Candidates: Chronos, ChronosGBM, Blend (GBM v1.3 validation file not reproduced).

Check B - does the share of energy_Wh taken straight from the counter explain the per-circuit error?
    Share of rows by energy_source (counter / spread / power) on the 2025 training and test weeks,
    against the Blend v1.3 scaled MAE per circuit and the number of valid test hours.

Run from the repository root:  python Final_Evidence/scripts/cleaning_checks.py
Needs pandas, numpy, scipy, pyarrow. Writes Final_Evidence/analysis/cleaning_*.csv
"""
import io, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path.cwd()
OUT = ROOT / "Final_Evidence" / "analysis"
T6 = ROOT / "Task6_rev0_03-11"
V13 = ROOT / "TBDA_v1.3_ChronosGBM_29-10" / "results"
CLEAN_ZIP = ROOT / "CLEAN DATA all zones.zip"

FLAG_BIASED = {"SW|Lighting"}
FLAG_RESOLUTION = {"NE|HVAC", "NW|Hand Dryer", "SE|Emerg. Lighting", "SW|Hand Dryer"}
FLAGGED = FLAG_BIASED | FLAG_RESOLUTION
NOT_TRAINED = {"SE|Plugs & Sockets"}                     # rule D4
MODELS = ["ML_RandomForest", "ML_Linear", "ML_GBM_v1.3", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3",
          "ML_Blend_v1.3", "B1_last_week", "B2_weekday_hour_median", "B3_persistence"]
TRAIN_WEEKS = ("2025-08-19", "2025-09-22")               # task6_split_design.py
TEST_WEEK = ("2025-09-29", "2025-10-06")

scale = pd.read_csv(T6 / "data" / "task6_circuit_scale_train_mean_v1.2.csv").set_index("circuit")["scale_Wh"]


# ------------------------------------------------------------------ A1: test comparison
def run_task6(exclude, tag, tmp):
    pdir = Path(tmp) / tag
    pdir.mkdir()
    files = []
    for m in MODELS:
        d = pd.read_csv(T6 / "results" / "predictions" / f"{m}_test_predictions.csv")
        f = pdir / f"{m}_test_predictions.csv"
        d[~d["zone"].isin(exclude)].to_csv(f, index=False)
        files.append(str(f))
    env = dict(os.environ, OUT_DIR=str(pdir / "out"), SPLIT_LABEL="Test",
               SCALE_FILE=str(T6 / "data" / "task6_circuit_scale_train_mean_v1.2.csv"),
               EVENTS_FILE=str(T6 / "data" / "task6_events_test.csv"))
    subprocess.run([sys.executable, str(T6 / "task6_compare.py"), *files], env=env, check=True,
                   stdout=subprocess.DEVNULL)
    met = pd.read_csv(pdir / "out" / "metrics_with_CI.csv")
    pairs = pd.read_csv(pdir / "out" / "pairwise_differences.csv")
    best = pd.read_csv(pdir / "out" / "best_model_per_scope.csv")
    met, pairs, best = (x[x["scope"] == "all circuits"] for x in (met, pairs, best))
    rows = []
    for hz, g in met.groupby("horizon", sort=False):
        b = g.set_index("model")
        row = {"circuit_set": tag, "horizon": hz, "n_circuit_hours": int(b.loc["ML_Blend_v1.3", "n"]),
               "Blend_MAE_Wh": b.loc["ML_Blend_v1.3", "MAE_Wh"],
               "Blend_scaled_MAE": b.loc["ML_Blend_v1.3", "scaled_MAE"],
               "best_model_MAE": best[best.horizon == hz]["best_model"].iloc[0],
               "best_vs_second": best[best.horizon == hz]["difference"].iloc[0]}
        for base in ["B2_weekday_hour_median", "B3_persistence"]:
            p = pairs[(pairs.horizon == hz) & (pairs.model_A == "ML_Blend_v1.3") & (pairs.model_B == base)].iloc[0]
            short = base.split("_")[0]
            row[f"Blend_minus_{short}_MAE_Wh"] = p["MAE_A_minus_B"]
            row[f"CI_{short}"] = f"[{p['diff_lo']:.1f}, {p['diff_hi']:.1f}]"
            row[f"significant_vs_{short}_MAE"] = bool(p["significant"])
            row[f"significant_vs_{short}_scaledMAE"] = bool(p["sMAE_significant"])
        rows.append(row)
    return rows


# ------------------------------------------------------------------ A2: selection rule D10
def d10(circuits, tag):
    preds = {"ML_Chronos": "chronos", "ML_ChronosGBM": "hybrid", "ML_Blend": "blend"}
    res = []
    for model, f in preds.items():
        d = pd.read_parquet(V13 / f"{f}_validation_predictions_v1.3.parquet")
        d = d[d.series_id.isin(circuits)].dropna(subset=["y_true", "y_pred"])
        e = d.assign(ae=(d.y_true - d.y_pred).abs(), se=(d.y_true - d.y_pred) ** 2)
        g = e.groupby(["horizon", "series_id"]).agg(mae=("ae", "mean"), mse=("se", "mean")).reset_index()
        g["s"] = g.series_id.map(scale)
        g = g.assign(smae=g.mae / g.s, srmse=np.sqrt(g.mse) / g.s)
        for hz, h in g.groupby("horizon"):
            res.append({"circuit_set": tag, "n_circuits": h.series_id.nunique(), "horizon": hz, "model": model,
                        "mean_scaled_MAE": h.smae.mean(), "mean_scaled_RMSE": h.srmse.mean()})
    r = pd.DataFrame(res)
    out = []
    for hz, h in r.groupby("horizon"):
        best = h.mean_scaled_MAE.min()
        h = h.assign(tied=h.mean_scaled_MAE <= best + 0.005)
        pick = h[h.tied].sort_values("mean_scaled_RMSE").model.iloc[0]
        out.append(h.assign(d10_pick=h.model == pick))
    return pd.concat(out)


# ------------------------------------------------------------------ B: energy source vs error
def energy_source_table():
    rows = []
    with zipfile.ZipFile(CLEAN_ZIP) as z:
        for zone in ["NE", "NW", "SE", "SW"]:
            name = next(n for n in z.namelist() if n.endswith(f"clean_Storey1_{zone}_CLEAN_DATA.csv"))
            d = pd.read_csv(io.BytesIO(z.read(name)), usecols=["sensor", "Timestamp", "energy_source"],
                            parse_dates=["Timestamp"])
            for period, (a, b) in {"train": TRAIN_WEEKS, "test": TEST_WEEK}.items():
                g = d[(d.Timestamp >= a) & (d.Timestamp < b)]
                hours = (pd.Timestamp(b) - pd.Timestamp(a)).total_seconds() / 3600
                for s, h in g.groupby("sensor"):
                    vc = h.energy_source.value_counts(normalize=True) * 100
                    rows.append({"circuit": f"{zone}|{s}", "period": period,
                                 "pct_counter": vc.get("counter", 0), "pct_spread": vc.get("spread", 0),
                                 "pct_power": vc.get("power", 0), "readings_per_hour": len(h) / hours})
    t = pd.DataFrame(rows).pivot(index="circuit", columns="period")
    t.columns = [f"{a}_{b}" for a, b in t.columns]
    mp = pd.read_csv(T6 / "results" / "task6_test_16circuits" / "metrics_per_circuit.csv")
    mp = mp[mp.model == "ML_Blend_v1.3"].copy()
    mp["sMAE"] = mp.MAE_Wh / mp.circuit.map(scale)
    err = mp.pivot(index="circuit", columns="horizon_h", values="sMAE")
    err.columns = [f"Blend_scaled_MAE_h{c}" for c in err.columns]
    t = t.join(err).join(mp.groupby("circuit").n.first().rename("valid_test_hours")).join(scale)
    t["quality_flag"] = ["counter_biased" if c in FLAG_BIASED else "below_resolution" if c in FLAG_RESOLUTION
                         else "ok" for c in t.index]
    return t.sort_values("pct_counter_test")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        a1 = (run_task6(set(), "all 16", tmp) + run_task6(FLAG_BIASED, "without SW Lighting", tmp)
              + run_task6(FLAGGED, "without 5 flagged", tmp))
    pd.DataFrame(a1).round(4).to_csv(OUT / "cleaning_flags_impact_test.csv", index=False)

    train = [c for c in scale.index if c not in NOT_TRAINED]
    a2 = pd.concat([d10(train, "15 training circuits (official)"),
                    d10([c for c in train if c not in FLAGGED], "training circuits without 5 flagged")])
    a2.round(4).to_csv(OUT / "cleaning_flags_impact_selection.csv", index=False)

    b = energy_source_table()
    b.round(2).to_csv(OUT / "cleaning_energy_source_vs_error.csv")
    for sub, tag in [(b, "16 circuits"), (b[b.quality_flag == "ok"], "11 ok circuits")]:
        rho_e, p_e = spearmanr(b.loc[sub.index, "pct_counter_test"], sub["Blend_scaled_MAE_h24"])
        rho_n, p_n = spearmanr(b.loc[sub.index, "pct_counter_test"], sub["valid_test_hours"])
        print(f"{tag}: counter share vs day-ahead scaled MAE rho={rho_e:.2f} (p={p_e:.2f}); "
              f"vs valid test hours rho={rho_n:.2f} (p={p_n:.3f})")
    print("written:", *sorted(p.name for p in OUT.glob("cleaning_*.csv")))


if __name__ == "__main__":
    main()
