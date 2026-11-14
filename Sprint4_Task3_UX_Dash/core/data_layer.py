"""Data access for the dashboard: forecasts of the final model, official scores, prediction intervals.

Only the final model (Blend v1.3) is read. Two sources of forecasts:
  - "stored":     the frozen forecasts saved in Task 6 (Task6_rev0_03-11/results/predictions)
  - "recomputed": forecasts produced by this app from the frozen model (model_engine.py, "Model" page)
"""
from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

import settings as S


# ----------------------------------------------------------------------------------------------------------
# Forecasts
# ----------------------------------------------------------------------------------------------------------
def recomputed_path(split: str):
    return S.CACHE_DIR / f"{S.MODEL_FILE_TAG}_{split}_recomputed.csv"


def stored_path(split: str):
    return S.PRED_DIR / f"{S.MODEL_FILE_TAG}_{split}_predictions.csv"


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    """Task 6 columns -> dashboard columns. 'zone' in the Task 6 files is the circuit id (e.g. 'NW|Lighting')."""
    df = df.rename(columns={"zone": "circuit", "circuit_zone": "zone", "actual_Wh": "actual", "predicted_Wh": "pred"})
    df["target_utc"] = pd.to_datetime(df["target_hour"], utc=True)
    df["issue_utc"] = pd.to_datetime(df["issue_time"], utc=True)
    df["target_local"] = df["target_utc"].dt.tz_convert(S.TZ_LOCAL)
    df["load_raw"] = df["circuit"].str.split("|").str[1]
    df["load_type"] = df["load_raw"].map(S.LOAD_TYPES).fillna(df["load_raw"])
    df["day_local"] = df["target_local"].dt.strftime("%Y-%m-%d")
    df["hour_local"] = df["target_local"].dt.hour
    df["pred"] = df["pred"].clip(lower=0)
    if "is_future" not in df:
        df["is_future"] = False
    df["is_future"] = df["is_future"].astype(str).str.lower().isin(["true", "1"])
    cols = ["circuit", "zone", "load_type", "horizon_h", "target_utc", "target_local", "day_local", "hour_local",
            "issue_utc", "lead_h", "actual", "pred", "is_future"]
    cols += [c for c in ("q10", "q90") if c in df]                   # Chronos-Bolt band (live file)
    return df[cols].sort_values(["horizon_h", "circuit", "target_utc"])


_HZ = {"+1h": 1, "+6h": 6, "day-ahead": 24}


@lru_cache(maxsize=4)
def chronos_band(split: str) -> pd.DataFrame | None:
    """Chronos-Bolt v1.3 q10 / q90 of the frozen configuration (one of the three Blend parts), per horizon."""
    path = S.MODEL_DIR / "results" / f"chronos_{split}_predictions_v1.3.parquet"
    if not path.exists():
        return None
    try:
        import pyarrow  # noqa: F401
        c = pd.read_parquet(path)
    except ImportError:
        sys.path.insert(0, str(S.TASK6))
        import minipq
        c = minipq.read_parquet(str(path))
    c = c.assign(horizon_h=c["horizon"].map(_HZ), target_utc=pd.to_datetime(c["target_time"], utc=True),
                 circuit=c["series_id"])
    return c[["circuit", "horizon_h", "target_utc", "q10", "q90"]]


@lru_cache(maxsize=8)
def _load(split: str, source: str, stamp: float) -> pd.DataFrame:   # stamp = file mtime, so a recomputation reloads
    path = recomputed_path(split) if source == "recomputed" else stored_path(split)
    df = _tidy(pd.read_csv(path))
    band = chronos_band(split)
    if band is not None:
        df = df.merge(band, on=["circuit", "horizon_h", "target_utc"], how="left")
    return df


def has_recomputed(split: str) -> bool:
    return recomputed_path(split).exists()


def predictions(split: str = "test", source: str = "stored") -> pd.DataFrame:
    if source == "recomputed" and not has_recomputed(split):
        source = "stored"
    path = recomputed_path(split) if source == "recomputed" else stored_path(split)
    return _load(split, source, path.stat().st_mtime).copy()


def select(df: pd.DataFrame, horizon: int, zones=None, load_types=None, day=None) -> pd.DataFrame:
    m = df["horizon_h"] == horizon
    if zones:
        m &= df["zone"].isin(zones)
    if load_types:
        m &= df["load_type"].isin(load_types)
    if day and day != "all":
        m &= df["day_local"] == day
    return df[m]


def circuits() -> pd.DataFrame:
    d = predictions("test")[["circuit", "zone", "load_type"]].drop_duplicates()
    return d.sort_values(["zone", "circuit"]).reset_index(drop=True)


# ----------------------------------------------------------------------------------------------------------
# Live forecast (latest data + forecast ahead; made on this computer by live_engine.py)
# ----------------------------------------------------------------------------------------------------------
LIVE_CSV = S.CACHE_DIR / "live_forecast.csv"


def has_live() -> bool:
    return LIVE_CSV.exists() and LIVE_CSV.with_suffix(".json").exists()


@lru_cache(maxsize=2)
def _load_live(stamp: float) -> pd.DataFrame:
    return _tidy(pd.read_csv(LIVE_CSV))


def live_predictions() -> pd.DataFrame:
    return _load_live(LIVE_CSV.stat().st_mtime).copy()


def live_meta() -> dict:
    m = json.loads(LIVE_CSV.with_suffix(".json").read_text())
    for k in ("last_measured_hour_utc", "issued_at_utc", "created_utc", "live_start_utc"):
        m[k.replace("_utc", "_local")] = pd.Timestamp(m[k]).tz_convert(S.TZ_LOCAL)
    return m


def run_live(timeout_s: int = 3600) -> dict:
    """Run live_engine.py (Chronos-Bolt + frozen GBMs + blend) in a separate process."""
    proc = subprocess.run([sys.executable, str(S.ENGINES_DIR / "live_engine.py"), str(LIVE_CSV)],
                          capture_output=True, text=True, timeout=timeout_s, cwd=str(S.APP_DIR))
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-15:]
        return {"ok": False, "error": "\n".join(tail)}
    _load_live.cache_clear()
    return {"ok": True, **json.loads(proc.stdout.strip().splitlines()[-1])}


def update_data(source: str, timeout_s: int = 3600) -> dict:
    """Rebuild the hourly dataset from a newer export (update_data.py), then refresh the live forecast."""
    proc = subprocess.run([sys.executable, str(S.ENGINES_DIR / "update_data.py"), source], capture_output=True, text=True,
                          timeout=timeout_s, cwd=str(S.REPO))
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-15:]
        return {"ok": False, "error": "\n".join(tail)}
    info = json.loads(proc.stdout.strip().splitlines()[-1])
    live = run_live(timeout_s)
    return {"ok": live["ok"], "data": info, "live": live, "error": live.get("error")}


def check_repository() -> list[str]:
    """Files the dashboard needs from the repository; returns the missing ones (empty = all good)."""
    need = [stored_path("test"), stored_path("validation"), S.METRICS["test"] / "metrics_with_CI.csv",
            S.METRICS["validation"] / "metrics_with_CI.csv", S.SCALE_FILE, S.BLEND_CONFIG,
            S.MODEL_DIR / "derived" / "Storey1_hourly_v1.2.parquet"]
    return [str(p) for p in need if not p.exists()]


# ----------------------------------------------------------------------------------------------------------
# Prediction intervals (experimental until validated by Pole 1)
# ----------------------------------------------------------------------------------------------------------
def _base_band(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Chronos q10-q90 band widened to contain the Blend forecast; rows without Chronos quantiles -> NaN."""
    f = df["pred"].clip(lower=0).to_numpy(dtype=float)
    if "q10" not in df:
        n = np.full(len(df), np.nan)
        return f, n, n
    blo = np.clip(np.minimum(df["q10"].to_numpy(dtype=float), f), 0, None)
    bhi = np.maximum(df["q90"].to_numpy(dtype=float), f)
    return f, blo, bhi


def _conformal(x, level: float) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    k = int(np.ceil((len(x) + 1) * level))
    return float(x[min(k, len(x)) - 1])


@lru_cache(maxsize=4)
def interval_halfwidths(level: float = S.INTERVAL_LEVEL) -> pd.DataFrame:
    """Calibration of the forecast interval per horizon x circuit, on the VALIDATION week only.

    Main method, conformalized quantile band (CQR): the Chronos-Bolt q10-q90 band of the frozen configuration (one
    of the three parts of Blend v1.3), widened to contain the Blend forecast, is shifted outwards (or inwards) by
    Q = the ceil((n+1)*level)-th smallest score max(lo - actual, actual - hi) of the circuit's validation hours.
    The band follows the daily shape (narrow at night, wide in the day) and Q fixes its coverage circuit by circuit.
    Fallback (rows without Chronos quantiles): symmetric split-conformal half-width q of |actual - forecast|.
    Circuits with fewer than INTERVAL_MIN_N validation hours take the horizon-wide value scaled by the circuit mean.
    """
    v = predictions("validation", "stored").dropna(subset=["actual"]).copy()
    f, blo, bhi = _base_band(v)
    a = v["actual"].to_numpy(dtype=float)
    v["abs_res"] = np.abs(a - f)
    v["cqr"] = np.maximum(blo - a, a - bhi)
    scale = pd.read_csv(S.SCALE_FILE).set_index("circuit")["scale_Wh"]
    rows = []
    for hz, g in v.groupby("horizon_h"):
        sc = g["circuit"].map(scale).clip(lower=1.0)
        g_abs = _conformal(g["abs_res"] / sc, level)
        gc_ = g.dropna(subset=["cqr"])
        g_cqr = _conformal(gc_["cqr"] / gc_["circuit"].map(scale).clip(lower=1.0), level) if len(gc_) else np.nan
        for c in sorted(predictions("test")["circuit"].unique()):
            gc = g[g["circuit"] == c]
            cq = gc["cqr"].dropna()
            s_c = max(float(scale.get(c, 1.0)), 1.0)
            if len(gc) >= S.INTERVAL_MIN_N:
                rows.append((hz, c, _conformal(gc["abs_res"], level),
                             _conformal(cq, level) if len(cq) >= S.INTERVAL_MIN_N else g_cqr * s_c, len(gc), "circuit"))
            else:
                rows.append((hz, c, g_abs * s_c, g_cqr * s_c, len(gc), "pooled"))
    return pd.DataFrame(rows, columns=["horizon_h", "circuit", "q_Wh", "q_cqr_Wh", "n_calibration", "method"])


def apply_intervals(df: pd.DataFrame, level: float = S.INTERVAL_LEVEL) -> pd.DataFrame:
    """Add lo / hi (Wh) of the forecast interval at `level`, plus q_Wh = half its width (used as a scale)."""
    q = interval_halfwidths(round(float(level), 2))
    out = df.merge(q[["horizon_h", "circuit", "q_Wh", "q_cqr_Wh"]], on=["horizon_h", "circuit"], how="left")
    f, blo, bhi = _base_band(out)
    qc = out["q_cqr_Wh"].to_numpy(dtype=float)
    qa = out["q_Wh"].to_numpy(dtype=float)
    use = ~np.isnan(blo) & ~np.isnan(qc) if S.INTERVAL_METHOD == "cqr" else np.zeros(len(out), bool)
    lo = np.where(use, np.minimum(blo - qc, f), f - qa)
    hi = np.where(use, np.maximum(bhi + qc, f), f + qa)
    out["lo"] = np.clip(lo, 0, None)
    out["hi"] = hi
    out["q_Wh"] = (out["hi"] - out["lo"]) / 2
    out["interval_method"] = np.where(use, "cqr", "abs")
    return out.drop(columns=["q_cqr_Wh"])


def add_intervals(df: pd.DataFrame) -> pd.DataFrame:
    return apply_intervals(df, S.INTERVAL_LEVEL)


def interval_coverage(split: str = "test") -> pd.DataFrame:
    """Share of measured hours inside the interval, per horizon (only meaningful on the test week)."""
    d = add_intervals(predictions(split)).dropna(subset=["actual"])
    d["inside"] = (d["actual"] >= d["lo"]) & (d["actual"] <= d["hi"])
    d["width"] = d["hi"] - d["lo"]
    return d.groupby("horizon_h").agg(coverage=("inside", "mean"), mean_width_Wh=("width", "mean"),
                                      n=("inside", "size")).reset_index()


# ----------------------------------------------------------------------------------------------------------
# Aggregation for the forecast chart
# ----------------------------------------------------------------------------------------------------------
def hourly_total(sel: pd.DataFrame, with_interval: bool) -> pd.DataFrame:
    """Sum the selected circuits per hour. The measured total is shown only for hours where EVERY selected
    circuit has a valid measurement (otherwise it would look like a drop in consumption)."""
    if with_interval:
        sel = add_intervals(sel)
    agg = {"pred": ("pred", "sum"), "actual": ("actual", lambda s: s.sum() if s.notna().all() else np.nan),
           "n_circuits": ("circuit", "nunique")}
    if with_interval:
        # sum of per-circuit distances to the limits = conservative (assumes the circuits' errors move together)
        sel = sel.assign(d_lo=sel["pred"] - sel["lo"], d_hi=sel["hi"] - sel["pred"])
        agg["d_lo"] = ("d_lo", "sum")
        agg["d_hi"] = ("d_hi", "sum")
    t = sel.groupby("target_local").agg(**agg).reset_index()
    t["time"] = t["target_local"].dt.tz_localize(None)          # Madrid wall-clock time for the charts
    if with_interval:
        t["lo"] = (t["pred"] - t["d_lo"]).clip(lower=0)
        t["hi"] = t["pred"] + t["d_hi"]
        t["q_Wh"] = (t["hi"] - t["lo"]) / 2
    return t


def selection_kpis(sel: pd.DataFrame) -> dict:
    ok = sel.dropna(subset=["actual"])
    err = ok["pred"] - ok["actual"]
    tot = hourly_total(sel, False)
    peak = tot.loc[tot["pred"].idxmax()] if len(tot) else None
    return {
        "energy_kwh": sel["pred"].sum() / 1000.0,
        "peak_wh": float(peak["pred"]) if peak is not None else np.nan,
        "peak_time": peak["target_local"] if peak is not None else None,
        "mae": float(err.abs().mean()) if len(ok) else np.nan,
        "bias": float(err.mean()) if len(ok) else np.nan,
        "n_valid": int(len(ok)),
        "n_rows": int(len(sel)),
    }


# ----------------------------------------------------------------------------------------------------------
# Official scores of the final model (Task 6 files, common hours of the model comparison, 95% bootstrap CIs)
# ----------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=4)
def official_metrics(split: str = "test") -> pd.DataFrame:
    m = pd.read_csv(S.METRICS[split] / "metrics_with_CI.csv")
    return m[m["model"] == S.MODEL_FILE_TAG].reset_index(drop=True)


@lru_cache(maxsize=4)
def official_per_circuit(split: str = "test") -> pd.DataFrame:
    m = pd.read_csv(S.METRICS[split] / "metrics_per_circuit.csv")
    m = m[m["model"] == S.MODEL_FILE_TAG].copy()
    m["load_type"] = m["circuit"].str.split("|").str[1].map(S.LOAD_TYPES)
    return m.reset_index(drop=True)


@lru_cache(maxsize=4)
def official_by_hour(split: str = "test") -> pd.DataFrame:
    m = pd.read_csv(S.METRICS[split] / "error_by_hour_of_day.csv")
    return m[m["model"] == S.MODEL_FILE_TAG].reset_index(drop=True)


def data_coverage(split: str = "test") -> pd.DataFrame:
    """Measured hours per circuit (out of 168) in the chosen week: low coverage = less reliable scores."""
    d = predictions(split)
    d = d[d["horizon_h"] == 1]
    g = d.groupby(["circuit", "zone", "load_type"])["actual"].apply(lambda s: s.notna().sum()).reset_index(name="valid_h")
    g["coverage"] = g["valid_h"] / 168.0
    return g.sort_values("coverage")


def blend_config() -> dict:
    return json.loads(S.BLEND_CONFIG.read_text())


# ----------------------------------------------------------------------------------------------------------
# Running the frozen model
# ----------------------------------------------------------------------------------------------------------
def run_model(split: str, timeout_s: int = 900) -> dict:
    """Recompute the forecasts with model_engine.py in a separate process and compare with the stored file."""
    out = recomputed_path(split)
    proc = subprocess.run([sys.executable, str(S.ENGINES_DIR / "model_engine.py"), split, str(out)],
                          capture_output=True, text=True, timeout=timeout_s, cwd=str(S.APP_DIR))
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-12:]
        return {"ok": False, "error": "\n".join(tail)}
    info = json.loads(proc.stdout.strip().splitlines()[-1])
    _load.cache_clear()
    new = predictions(split, "recomputed")
    old = predictions(split, "stored")
    keys = ["circuit", "horizon_h", "target_utc", "issue_utc"]
    j = old.merge(new, on=keys, suffixes=("_stored", "_new"))
    diff = (j["pred_stored"] - j["pred_new"]).abs()
    info.update({"ok": True, "matched": int(len(j)), "max_abs_diff_Wh": float(diff.max()) if len(j) else np.nan})
    return info


def days(split: str) -> list[str]:
    """Madrid-time days of the week with (almost) all 24 hours; the first/last UTC hours spill into extra days."""
    d = predictions(split)
    n = d[d["horizon_h"] == 1].groupby("day_local")["target_utc"].nunique()
    return sorted(n[n >= 20].index)
