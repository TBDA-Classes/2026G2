"""Sprint 4 - Task 2: does outdoor temperature improve Blend v1.3?

Steps
  1. Get hourly outdoor temperature for CeDInt (Open-Meteo) and save it in data/.
  2. Quality checks on the temperature data -> outputs/temperature_qa.csv
  3. Retrain the two GBM parts of Blend v1.3 (GBM and ChronosGBM) twice, with the FROZEN v1.3 parameters:
       E0 = original inputs (reproduces Blend v1.3)
       E1 = original inputs + 2 temperature inputs
     Chronos and the Blend weights are not changed (decision D12: weather only enters the GBM parts).
  4. Compare E0 and E1 on the VALIDATION week only (22-28 Sep 2025). The test week is not used.

Run from this folder, with this folder placed in the root of the group repository:
    python task2_temperature.py
or point to the repository explicitly:
    python task2_temperature.py --repo "path/to/2026G2-main"
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import requests

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=str(HERE.parent), help="root folder of the group repository (2026G2-main)")
REPO = Path(ap.parse_args().repo).resolve()
CODE = REPO / "TBDA_v1.3_ChronosGBM_29-10"
sys.path.insert(0, str(CODE))

import config as C  # noqa: E402  (team code, unchanged)
from task7_baselines import load_derived, eligible_series, forecast_tasks  # noqa: E402
from task8_model import FEATURES, _series_frames, fit_cutoff, training_frame, build_features, series_scale, \
    GBMForecaster  # noqa: E402
from hybrid_model import HYBRID_FEATURES, load_cache, build_features_hybrid  # noqa: E402
from selection import scaled_scores  # noqa: E402

DATA, OUT = HERE / "data", HERE / "outputs"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
H = pd.Timedelta(hours=1)
KEY = ["series_id", "horizon", "issue_time", "target_time", "lead"]
TIE_MARGIN = C.D10_TIE_MARGIN          # 0.005 scaled MAE: smaller differences are treated as "no change" (rule D10)

# ---------------------------------------------------------------- 1. temperature data
CEDINT_LAT, CEDINT_LON = 40.4044, -3.8368          # CeDInt, Campus de Montegancedo (Pozuelo de Alarcon)
URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
PARAMS = dict(latitude=CEDINT_LAT, longitude=CEDINT_LON, start_date="2025-08-01", end_date="2025-10-13",
              hourly="temperature_2m,temperature_2m_previous_day2", timezone="UTC")
TEMP_FILE = DATA / "temperature_cedint_hourly_2025.csv"


def get_temperature() -> pd.DataFrame:
    """Download once, then always reuse the saved file (so results do not change if the provider updates data)."""
    if not TEMP_FILE.exists():
        r = requests.get(URL, params=PARAMS, timeout=60)
        r.raise_for_status()
        j = r.json()
        t = pd.DataFrame(j["hourly"]).rename(columns={
            "time": "hour_utc",
            "temperature_2m": "temp_obs_C",                  # best estimate of the actual temperature
            "temperature_2m_previous_day2": "temp_fc48_C"})  # forecast made 48 h before that hour
        t.to_csv(TEMP_FILE, index=False)
        (DATA / "temperature_download.json").write_text(json.dumps(dict(
            url=URL, params=PARAMS, downloaded_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            grid_latitude=j["latitude"], grid_longitude=j["longitude"], grid_elevation_m=j.get("elevation"),
            units=j["hourly_units"]), indent=2))
    t = pd.read_csv(TEMP_FILE, parse_dates=["hour_utc"])
    t["hour_utc"] = t["hour_utc"].dt.tz_localize("UTC")
    return t.set_index("hour_utc")


# ---------------------------------------------------------------- 2. quality checks
def madrid_station_daily(stations=(24, 58)) -> pd.DataFrame:
    """Daily mean temperature of Madrid city stations (S1-B2 file, magnitude 83). 24 = Casa de Campo, 58 = El Pardo."""
    s = pd.read_csv(REPO / "S1-B2 Data 2025-26.csv", sep=";", dtype=str)
    s = s[(s["MAGNITUD"].astype(int) == 83) & (s["ANO"] == "2025") & s["ESTACION"].astype(int).isin(stations)]
    rows = []
    for _, r in s.iterrows():
        for d in range(1, 32):
            if r[f"V{d:02d}"] == "V":                         # V = validated value
                rows.append((int(r["ESTACION"]), pd.Timestamp(2025, int(r["MES"]), d), float(r[f"D{d:02d}"])))
    return pd.DataFrame(rows, columns=["station", "date", "temp"]).pivot(index="date", columns="station", values="temp")


def split_period(name):
    a, b = C.SPLITS[name]
    return pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")


def quality_checks(T: pd.DataFrame) -> pd.DataFrame:
    meta = json.loads((DATA / "temperature_download.json").read_text())
    rows = []

    def add(check, value, ok=None):
        rows.append(dict(check=check, value=value, ok="" if ok is None else ("yes" if ok else "NO")))

    full = pd.date_range(T.index.min(), T.index.max(), freq="h")
    dist_km = np.hypot((meta["grid_latitude"] - CEDINT_LAT) * 111.0,
                       (meta["grid_longitude"] - CEDINT_LON) * 111.0 * np.cos(np.radians(CEDINT_LAT)))
    add("source", "Open-Meteo Previous Runs API (hourly)")
    add("grid point (lat, lon)", f"{meta['grid_latitude']:.3f}, {meta['grid_longitude']:.3f}")
    add("distance from CeDInt (km)", round(float(dist_km), 1), dist_km < 5)
    add("grid elevation (m)", meta["grid_elevation_m"])
    add("units", meta["units"]["temperature_2m"], meta["units"]["temperature_2m"] == "°C")
    add("time zone of timestamps", "UTC (same as the energy dataset)", True)
    add("first / last hour", f"{T.index.min()} / {T.index.max()}")
    add("expected hours", len(full))
    add("hours present", len(T), len(T) == len(full))
    add("duplicated hours", int(T.index.duplicated().sum()), T.index.duplicated().sum() == 0)
    add("missing temp_obs_C", int(T["temp_obs_C"].isna().sum()), T["temp_obs_C"].isna().sum() == 0)
    add("missing temp_fc48_C", int(T["temp_fc48_C"].isna().sum()), T["temp_fc48_C"].isna().sum() == 0)
    rng_ok = T[["temp_obs_C", "temp_fc48_C"]].stack().between(-15, 45).all()
    add("values inside -15..45 °C", f"{T['temp_obs_C'].min():.1f} .. {T['temp_obs_C'].max():.1f}", rng_ok)
    add("aggregation rule", "none needed: the source is already hourly")
    err = (T["temp_fc48_C"] - T["temp_obs_C"])
    for name in ("train", "validation"):
        a, b = split_period(name)
        e = err[(err.index >= a) & (err.index < b)]
        add(f"48 h forecast error, MAE (°C), {name}", round(float(e.abs().mean()), 2))
    # cross-check with the Madrid city stations already in the repository (daily means, local days)
    st = madrid_station_daily()
    daily = T["temp_obs_C"].tz_convert("Europe/Madrid").resample("D").mean()
    daily.index = daily.index.tz_localize(None)
    both = st.join(daily.rename("open_meteo"), how="inner").loc["2025-08-19":"2025-09-28"]
    for s, label in ((24, "Casa de Campo (24)"), (58, "El Pardo (58)")):
        c = both[[s, "open_meteo"]].dropna()
        d = c["open_meteo"] - c[s]
        add(f"vs station {label}: days / correlation / mean difference / MAE (°C)",
            f"{len(c)} / {c.corr().iloc[0, 1]:.3f} / {d.mean():+.2f} / {d.abs().mean():.2f}", c.corr().iloc[0, 1] > 0.9)
    # temperature range by split (important for interpreting the results)
    for name in ("train", "validation"):
        a, b = split_period(name)
        x = T.loc[(T.index >= a) & (T.index < b), "temp_obs_C"]
        add(f"temperature {name}: min / mean / max (°C)", f"{x.min():.1f} / {x.mean():.1f} / {x.max():.1f}")
    a, b = split_period("validation")
    tr_min = T.loc[(T.index >= split_period("train")[0]) & (T.index < a), "temp_obs_C"].min()
    x = T.loc[(T.index >= a) & (T.index < b), "temp_obs_C"]
    add("validation hours colder than the coldest training hour", f"{(x < tr_min).mean():.0%}")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 3. experiments
TEMP_FEATURES = ["temp_last", "temp_fc_target"]


def add_temperature(F: pd.DataFrame, T: pd.DataFrame) -> pd.DataFrame:
    """The two new inputs. Both are known when the forecast is issued:
    temp_last      = temperature of the last hour before the issue time (same rule as the energy inputs)
    temp_fc_target = temperature FORECAST for the target hour, made 48 h before that hour. Target hours are at most
                     24 h after the issue time, so this forecast always existed at least 24 h before the issue time.
    """
    F = F.copy()
    F["temp_last"] = T["temp_obs_C"].reindex(F["issue_time"] - H).to_numpy()
    F["temp_fc_target"] = T["temp_fc48_C"].reindex(F["target_time"]).to_numpy()
    assert (F["target_time"] - F["issue_time"] < pd.Timedelta(hours=24)).all()
    assert F[TEMP_FEATURES].notna().all().all(), "temperature missing for some forecast rows"
    return F


def run_experiments(T: pd.DataFrame) -> pd.DataFrame:
    h = load_derived(CODE / C.DERIVED_PATH)
    S_all = eligible_series(CODE / C.ELIGIBILITY_FILE, which="all")
    S_train = eligible_series(CODE / C.ELIGIBILITY_FILE, which="training")
    frames = _series_frames(h)
    cache = load_cache(CODE / C.CHRONOS_CACHE_V13)
    cfg = {m: json.loads((CODE / C.FROZEN_V13[m]).read_text()) for m in ("task8", "hybrid", "blend")}
    chronos = pd.read_parquet(CODE / "results" / "chronos_validation_predictions_v1.3.parquet")
    out = []
    for hz in C.HORIZONS:
        cut = fit_cutoff(h, hz, S_all)
        scale = series_scale(h, cut)
        vt = forecast_tasks(h, hz, "validation", S_all)
        # GBM part (same training rows as run_v13_gbm_tune.py)
        F, _ = training_frame(h, hz, S_train, cut, frames=frames)
        V = build_features(h, vt, scale, frames=frames)
        p = cfg["task8"]["horizons"][hz]["params"]
        gbm0 = GBMForecaster("pooled", p, S_train).fit(F).predict(V)
        gbm1 = GBMForecaster("pooled", p, S_train, features=FEATURES + TEMP_FEATURES) \
            .fit(add_temperature(F, T)).predict(add_temperature(V, T))
        # ChronosGBM part (same training rows as run_v13_hybrid_tune.py)
        t = forecast_tasks(h, hz, "train", S_train)
        t = t[t["target_time"] < cut].reset_index(drop=True)
        Fh = build_features_hybrid(h, t, scale, cache, frames=frames)
        Vh = build_features_hybrid(h, vt, scale, cache, frames=frames)
        p = cfg["hybrid"]["horizons"][hz]["params"]
        hyb0 = GBMForecaster("pooled", p, S_train, features=HYBRID_FEATURES).fit(Fh).predict(Vh)
        hyb1 = GBMForecaster("pooled", p, S_train, features=HYBRID_FEATURES + TEMP_FEATURES) \
            .fit(add_temperature(Fh, T)).predict(add_temperature(Vh, T))
        # put everything on the same forecast rows; Chronos = saved frozen v1.3 forecasts
        P = V[KEY + ["y_true"]].assign(gbm_E0=gbm0, gbm_E1=gbm1)
        P = P.merge(Vh[KEY].assign(hyb_E0=hyb0, hyb_E1=hyb1), on=KEY, validate="1:1")
        P = P.merge(chronos[chronos["horizon"] == hz][KEY + ["y_pred"]].rename(columns={"y_pred": "chr"}),
                    on=KEY, validate="1:1")
        w = cfg["blend"]["horizons"][hz]
        for e in ("E0", "E1"):
            P[f"blend_{e}"] = w["w_gbm"] * P[f"gbm_{e}"] + w["w_hybrid"] * P[f"hyb_{e}"] + w["w_chronos"] * P["chr"]
        P["scale_Wh"] = P["series_id"].map(pd.Series(cfg["task8"]["horizons"][hz]["scale_Wh"]))
        out.append(P)
        print(f"{hz}: {len(P)} validation forecast rows")
    return pd.concat(out, ignore_index=True), S_train


def reproduction_check(P: pd.DataFrame, exp: pd.DataFrame) -> pd.DataFrame:
    """Does E0 reproduce the frozen Blend v1.3? Compares forecasts and the validation score of each part.

    Retraining the ChronosGBM part on another computer gives slightly different trees for +1h and day-ahead
    (same data, parameters and seed; the frozen .joblib models reproduce the saved forecasts exactly). The check
    passes if the score difference is below the D10 tie margin, i.e. too small to change any conclusion.
    E0 and E1 are always trained in the same run, so the comparison between them is like for like.
    """
    R = CODE / "results"
    saved = {"gbm": pd.read_parquet(R / "task8_validation_predictions_v1.3.parquet").query("model == 'ML_GBM'"),
             "hyb": pd.read_parquet(R / "hybrid_validation_predictions_v1.3.parquet"),
             "blend": pd.read_parquet(R / "blend_validation_predictions_v1.3.parquet")}
    names = {"gbm": ("task8", "GBM v1.3"), "hyb": ("hybrid", "ChronosGBM v1.3"), "blend": ("blend", "Blend v1.3")}
    rows = []
    for part, s in saved.items():
        cfg = json.loads((CODE / C.FROZEN_V13[names[part][0]]).read_text())
        for hz in C.HORIZONS:
            m = P[P["horizon"] == hz][KEY + [f"{part}_E0"]].merge(s[KEY + ["y_pred"]], on=KEY, validate="1:1")
            frozen = cfg["horizons"][hz]["validation_score"]
            e0 = float(exp.loc[(exp["horizon"] == hz) & (exp["model"] == names[part][1]), "scaled_MAE_E0"].iloc[0])
            rows.append(dict(
                check=f"E0 reproduces frozen {names[part][1]}, {hz}: max forecast difference (Wh) / "
                      f"validation score frozen vs E0",
                value=f"{(m[f'{part}_E0'] - m['y_pred']).abs().max():.2g} / {frozen:.4f} vs {e0:.4f}",
                ok="yes" if abs(e0 - frozen) < TIE_MARGIN else "NO"))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 4. comparison
def mae_rmse(g, col):
    e = g["y_true"] - g[col]
    return e.abs().mean(), float(np.sqrt((e ** 2).mean()))


def compare(P: pd.DataFrame, by: str) -> pd.DataFrame:
    """Blend E0 vs E1, MAE/RMSE in Wh on the same valid hours (actual value available)."""
    rows = []
    for (hz, key), g in P.groupby(["horizon", by], sort=False):
        mae0, rmse0 = mae_rmse(g, "blend_E0")
        mae1, rmse1 = mae_rmse(g, "blend_E1")
        rows.append({"horizon": hz, by: key, "n_valid_hours": len(g), "MAE_E0_Wh": mae0, "MAE_E1_Wh": mae1,
                     "MAE_change_pct": 100 * (mae1 - mae0) / mae0 if mae0 else np.nan,
                     "RMSE_E0_Wh": rmse0, "RMSE_E1_Wh": rmse1,
                     "RMSE_change_pct": 100 * (rmse1 - rmse0) / rmse0 if rmse0 else np.nan})
    return pd.DataFrame(rows).round(3)


def experiment_table(P: pd.DataFrame, S_train) -> pd.DataFrame:
    """Selection metric of the team (mean scaled MAE over the 15 training circuits) for each model part."""
    rows = []
    for hz, g in P.groupby("horizon", sort=False):
        scale = g.groupby("series_id")["scale_Wh"].first()
        for part, label in (("gbm", "GBM v1.3"), ("hyb", "ChronosGBM v1.3"), ("blend", "Blend v1.3")):
            s = {e: scaled_scores(g.assign(y_pred=g[f"{part}_{e}"]), scale, S_train) for e in ("E0", "E1")}
            d = s["E1"]["mean_scaled_MAE"] - s["E0"]["mean_scaled_MAE"]
            rows.append(dict(horizon=hz, model=label,
                             scaled_MAE_E0=s["E0"]["mean_scaled_MAE"], scaled_MAE_E1=s["E1"]["mean_scaled_MAE"],
                             change=d, scaled_RMSE_E0=s["E0"]["mean_scaled_RMSE"],
                             scaled_RMSE_E1=s["E1"]["mean_scaled_RMSE"],
                             result=("better" if d < -TIE_MARGIN else "worse" if d > TIE_MARGIN
                                     else "no clear change (within 0.005)")))
    return pd.DataFrame(rows).round(4)


# ---------------------------------------------------------------- figures
def figures(T: pd.DataFrame, P: pd.DataFrame, by_circuit: pd.DataFrame):
    a, _ = split_period("train")
    va, vb = split_period("validation")
    x = T.loc[(T.index >= a) & (T.index < vb), "temp_obs_C"]
    tr_min = x[x.index < va].min()
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(x.index, x.values, lw=0.8, color="#33658a")
    ax.axvspan(va, vb, color="#f6ae2d", alpha=0.25, label="validation week")
    ax.axhline(tr_min, ls="--", color="#c0392b", lw=1, label=f"coldest training hour ({tr_min:.1f} °C)")
    ax.set_ylabel("Outdoor temperature (°C)")
    ax.set_title("Outdoor temperature at CeDInt: training period vs validation week")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_temperature_train_vs_validation.png", dpi=150)
    plt.close(fig)

    hzs = list(C.HORIZONS)
    fig, axes = plt.subplots(1, len(hzs), figsize=(13, 5.5), sharey=True)
    for ax, hz in zip(axes, hzs):
        d = by_circuit[by_circuit["horizon"] == hz].set_index("series_id")["MAE_change_pct"]
        ax.barh(d.index, d.values, color=np.where(d.values < 0, "#2a9d8f", "#c0392b"))
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(hz)
        ax.set_xlabel("MAE change E1 vs E0 (%)")
    axes[0].invert_yaxis()
    fig.suptitle("Blend v1.3 with temperature: change in validation MAE by circuit (negative = better)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_mae_change_by_circuit.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(len(hzs), 1, figsize=(11, 8), sharex=True)
    for ax, hz in zip(axes, hzs):
        g = P[(P["series_id"] == "NW|HVAC") & (P["horizon"] == hz)].sort_values("target_time")
        ax.plot(g["target_time"], g["y_true"], color="black", lw=1.2, label="actual")
        ax.plot(g["target_time"], g["blend_E0"], color="#33658a", lw=1, label="Blend v1.3 (E0)")
        ax.plot(g["target_time"], g["blend_E1"], color="#e76f51", lw=1, label="Blend + temperature (E1)")
        ax.set_ylabel("Wh")
        ax.set_title(f"NW | HVAC, {hz}")
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_nw_hvac_before_after.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    T = get_temperature()
    P, S_train = run_experiments(T)
    P["zone"] = P["series_id"].str.split("|").str[0]
    P["load_type"] = P["series_id"].str.split("|").str[1]
    P.drop(columns="scale_Wh").to_csv(OUT / "validation_predictions_E0_E1.csv", index=False)
    V = P[P["y_true"].notna()].copy()                   # missing actual values are never filled
    exp = experiment_table(V, S_train)
    exp.to_csv(OUT / "experiment_table.csv", index=False)
    qa = pd.concat([quality_checks(T), reproduction_check(P, exp)], ignore_index=True)
    qa.to_csv(OUT / "temperature_qa.csv", index=False)
    print(qa.to_string(index=False))
    tables = {"horizon": compare(V.assign(all="all circuits"), "all"), "zone": compare(V, "zone"),
              "load_type": compare(V, "load_type"), "circuit": compare(V, "series_id")}
    for name, tab in tables.items():
        tab.to_csv(OUT / f"comparison_by_{name}.csv", index=False)
    figures(T, P, tables["circuit"])
    print("\n" + exp.to_string(index=False))
    print("\n" + tables["horizon"].to_string(index=False))
    print(f"\nwrote outputs to {OUT}")
