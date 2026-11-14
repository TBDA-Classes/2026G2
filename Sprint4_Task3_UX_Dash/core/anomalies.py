"""Consumption anomalies, data quality, tariff costs and base load — built on our own forecast interval.

Method (this app's own):
  forecast      = Blend v1.3 day-ahead (issued 00:00 Madrid)
  interval      = forecast interval at the chosen level (80 / 90 / 95 %): Chronos-Bolt q10-q90 band calibrated per
                  circuit on the validation week (conformalized quantile band, data_layer.apply_intervals);
                  it is in-sample on that week
  anomaly hour  = measured value outside the interval AND |measured − forecast| >= the minimum deviation (Wh)
                  spike = above the interval (extra energy, costs money); drop = below it (possible fault/outage)
  anomaly       = consecutive anomaly hours of one circuit in the same direction
  level         = Critical: >= 1 kWh or >= 6 h · Moderate: >= 0.25 kWh or >= 3 h · Minor: the rest
  cost          = extra kWh x price of the tariff period of each hour (Spanish 2.0TD-style periods, prices are
                  assumptions set in Settings); CO2 = extra kWh x an assumed grid factor
Hours without a valid measurement are never anomalies; they are listed under data quality with their reason.
"""
from __future__ import annotations

import sys
from functools import lru_cache

import numpy as np
import pandas as pd

import data_layer as D
import settings as S

LEVELS = ("Critical", "Moderate", "Minor")
PERIODS = {"eval": "22 Sep – 5 Oct 2025 (evaluation weeks)", "live": "6 – 13 Oct 2025 (latest week)"}
TARIFF = {"P1": "Peak", "P2": "Standard", "P3": "Off-peak"}
DEFAULTS = {"level": 0.90, "min_dev": 25.0, "p1": 0.24, "p2": 0.17, "p3": 0.12, "co2": 0.25, "period": "eval"}
QUALITY = {"energy_catch_up": "Catch-up reading after a gap",
           "energy_pre_outage": "Hour cut short by an outage",
           "energy_inconsistent": "Energy above what the power allows"}
GUIDE = {
    "Plugs & sockets": ["Compare with the same hours on other days: a recurring pattern points to a schedule.",
                        "Ask the zone's users which devices stay connected after hours.",
                        "A smart plug or timer on the largest devices can confirm the cause."],
    "Lighting": ["Check the presence sensors and the lighting schedule for this zone.",
                 "See whether cleaning or events were planned at that time."],
    "Emergency lighting": ["A battery recharge after a monthly test produces this kind of increase.",
                           "If it repeats, ask maintenance to check the luminaires."],
    "HVAC": ["Compare with the HVAC timetable and set-points in the building management system.",
             "Unusual weather that day can explain part of it."],
    "Hand dryers": ["Very high values usually mean a sensor stuck on; worth a quick visual check."],
    "IT rack": ["Ask IT whether equipment was added or a heavy job ran at that time."],
}
DROP_GUIDE = ["A drop below the expected range can mean equipment off, a tripped breaker or a meter problem.",
              "Check whether the zone was closed or the circuit was switched off on purpose."]


def tariff_period(t_local: pd.Series, holiday: pd.Series) -> pd.Series:
    """Spanish 2.0TD-style periods: weekdays P1 10-14 & 18-22, P2 8-10, 14-18 & 22-24, P3 0-8; weekends/holidays P3."""
    h = t_local.dt.hour
    p = np.where(h < 8, "P3", np.where(((h >= 10) & (h < 14)) | ((h >= 18) & (h < 22)), "P1", "P2"))
    off = (t_local.dt.weekday >= 5) | holiday
    return pd.Series(np.where(off, "P3", p), index=t_local.index)


def _read_parquet(path):
    try:
        import pyarrow  # noqa: F401
        return pd.read_parquet(path)
    except ImportError:
        sys.path.insert(0, str(S.TASK6))
        import minipq
        return minipq.read_parquet(str(path))


@lru_cache(maxsize=1)
def derived() -> pd.DataFrame:
    h = _read_parquet(S.current_derived())
    h["hour_utc"] = pd.to_datetime(h["hour_utc"], utc=True)
    return h


def _quality(frame: pd.DataFrame) -> pd.Series:
    h = derived().set_index(["series_id", "hour_utc"])
    sub = h.reindex(pd.MultiIndex.from_arrays([frame["circuit"], frame["target_utc"]]))
    r = pd.Series("Failed another validity rule", index=frame.index, dtype=object)
    for col, txt in QUALITY.items():
        r[sub[col].fillna(False).to_numpy().astype(bool)] = txt
    r[sub["energy_n_obs"].isna().to_numpy()] = "No reading"
    return r.where(frame["actual"].isna(), None)


@lru_cache(maxsize=8)
def _frame(period: str, level: float, stamp: float) -> pd.DataFrame | None:
    if period == "eval":
        p = pd.concat([D.predictions("validation", "stored"), D.predictions("test", "stored")])
    else:
        if not D.has_live():
            return None
        p = D.live_predictions()
        p = p[~p["is_future"]]
    p = p[p["horizon_h"] == 24].rename(columns={"pred": "forecast"}).copy()
    p = D.apply_intervals(p.rename(columns={"forecast": "pred"}), level).rename(columns={"pred": "forecast"})
    hol = derived().drop_duplicates("hour_utc").set_index("hour_utc")["is_holiday"]
    p["holiday"] = p["target_utc"].map(hol).fillna(False).astype(bool)
    p["tariff"] = tariff_period(p["target_local"], p["holiday"])
    p["night_weekend"] = (p["target_local"].dt.weekday >= 5) | p["holiday"] | (p["hour_local"] < 7) | \
                         (p["hour_local"] >= 20)
    p["quality"] = _quality(p)
    p["time"] = p["target_local"].dt.tz_localize(None)
    return p.sort_values(["circuit", "target_utc"]).reset_index(drop=True)


def frame(period: str = "eval", level: float = 0.90) -> pd.DataFrame | None:
    stamp = D.LIVE_CSV.stat().st_mtime if period == "live" and D.LIVE_CSV.exists() else 0.0
    return _frame(period, round(float(level), 2), stamp)


def price_of(tariff: pd.Series, cfg: dict) -> pd.Series:
    return tariff.map({"P1": cfg["p1"], "P2": cfg["p2"], "P3": cfg["p3"]}).astype(float)


def detect(f: pd.DataFrame, min_dev: float, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Anomaly hours and anomalies (spikes and drops)."""
    m = f.dropna(subset=["actual"]).copy()
    m["dev"] = m["actual"] - m["forecast"]
    up = (m["actual"] > m["hi"]) & (m["dev"] >= min_dev)
    dn = (m["actual"] < m["lo"]) & (-m["dev"] >= min_dev)
    m["kind"] = np.where(up, "Spike", np.where(dn, "Drop", None))
    hrs = m[m["kind"].notna()].copy()
    cols = ["id", "circuit", "zone", "load_type", "kind", "start", "end", "n", "measured_kwh", "forecast_kwh",
            "dev_kwh", "peak_dev_wh", "cost_eur", "night_share", "level", "story"]
    if hrs.empty:
        return hrs.assign(aid=pd.Series(dtype=str)), pd.DataFrame(columns=cols)
    hrs["cost"] = np.where(hrs["kind"] == "Spike", hrs["dev"] / 1000 * price_of(hrs["tariff"], cfg), 0.0)
    brk = (hrs["circuit"] != hrs["circuit"].shift()) | (hrs["kind"] != hrs["kind"].shift()) | \
          (hrs["target_utc"].diff() != pd.Timedelta(hours=1))
    hrs["g"] = brk.cumsum()
    a = hrs.groupby("g").agg(circuit=("circuit", "first"), zone=("zone", "first"), load_type=("load_type", "first"),
                             kind=("kind", "first"), start=("time", "min"), end=("time", "max"), n=("time", "size"),
                             measured_kwh=("actual", "sum"), forecast_kwh=("forecast", "sum"), dev_kwh=("dev", "sum"),
                             peak_dev_wh=("dev", lambda s: s.abs().max()), cost_eur=("cost", "sum"),
                             night_share=("night_weekend", "mean")).reset_index()
    for c in ("measured_kwh", "forecast_kwh", "dev_kwh"):
        a[c] = a[c] / 1000
    a["end"] = a["end"] + pd.Timedelta(hours=1)
    size = a["dev_kwh"].abs()
    a["level"] = np.where((size >= 1) | (a["n"] >= 6), "Critical",
                          np.where((size >= 0.25) | (a["n"] >= 3), "Moderate", "Minor"))
    a = a.sort_values("start").reset_index(drop=True)
    a["id"] = [f"{'S' if k == 'Spike' else 'D'}-{i + 1:03d}" for i, k in enumerate(a["kind"])]
    hrs["aid"] = hrs["g"].map(dict(zip(a["g"], a["id"])))
    a["story"] = [
        (f"From {r.start:%a %d %b %H:%M} to {r.end:%H:%M} the {r.load_type.lower()} circuit of zone {r.zone} "
         + (f"used {r.dev_kwh:.2f} kWh more than the model expected ({r.measured_kwh:.2f} measured vs "
            f"{r.forecast_kwh:.2f} forecast)" if r.kind == "Spike" else
            f"used {-r.dev_kwh:.2f} kWh less than the model expected ({r.measured_kwh:.2f} measured vs "
            f"{r.forecast_kwh:.2f} forecast)")
         + f", {'mostly at night or at the weekend' if r.night_share >= 0.5 else 'mostly in working hours'}.")
        for r in a.itertuples()]
    return hrs, a[cols]


def quality_table(f: pd.DataFrame) -> pd.DataFrame:
    q = f[f["quality"].notna()].copy()
    if q.empty:
        return pd.DataFrame(columns=["circuit", "zone", "load_type", "start", "end", "hours", "reason"])
    brk = (q["circuit"] != q["circuit"].shift()) | (q["quality"] != q["quality"].shift()) | \
          (q["target_utc"].diff() != pd.Timedelta(hours=1))
    q["g"] = brk.cumsum()
    t = q.groupby("g").agg(circuit=("circuit", "first"), zone=("zone", "first"), load_type=("load_type", "first"),
                           start=("time", "min"), end=("time", "max"), hours=("time", "size"),
                           reason=("quality", "first")).reset_index(drop=True)
    t["end"] = t["end"] + pd.Timedelta(hours=1)
    return t.sort_values("start")


@lru_cache(maxsize=1)
def base_load() -> pd.DataFrame:
    """Base load = 10th percentile of hourly use (the floor the circuit never goes below), 19 Aug – 13 Oct 2025."""
    h = derived()
    h = h[(h["hour_utc"] >= pd.Timestamp("2025-08-19", tz="UTC")) & h["energy_Wh"].notna()].copy()
    loc = h["hour_utc"].dt.tz_convert(S.TZ_LOCAL)
    nw = (loc.dt.weekday >= 5) | h["is_holiday"].astype(bool) | (loc.dt.hour < 7) | (loc.dt.hour >= 20)
    rows = []
    for c, g in h.groupby("series_id"):
        k = nw[g.index]
        rows.append({"circuit": c, "zone": c.split("|")[0], "load_type": S.LOAD_TYPES.get(c.split("|")[1], c),
                     "base_wh": float(g["energy_Wh"].quantile(0.10)), "mean_wh": float(g["energy_Wh"].mean()),
                     "night_weekend_share": float(g.loc[k, "energy_Wh"].sum() / max(g["energy_Wh"].sum(), 1e-9))})
    t = pd.DataFrame(rows)
    t["base_share"] = t["base_wh"] / t["mean_wh"].clip(lower=1e-9)
    return t.sort_values("base_wh", ascending=False).reset_index(drop=True)


def coverage(f: pd.DataFrame) -> float:
    v = f.dropna(subset=["actual"])
    return float(((v["actual"] >= v["lo"]) & (v["actual"] <= v["hi"])).mean()) if len(v) else float("nan")
