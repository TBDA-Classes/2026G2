"""Task 7 — from the frozen minute data to an hourly modelling dataset (S05–S11).

    from task7_pipeline import *
    df   = load_frozen("data/Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz")        # S05
    rec  = recent_regime(df)
    e    = aggregate_energy_hourly(rec)                                    # S06
    p    = hourly_power_current(rec)                                       # S07
    h    = add_split_and_calendar(e.merge(p, on=["series_id", "hour_utc"], how="left"))  # S08
    save_derived(h, source_path, out_dir)                                  # S09
    elig = eligibility(h)                                                  # S10
    mae(y_true, y_pred), rmse(y_true, y_pred)                              # S11

All time logic runs in UTC. Madrid local time is only used for calendar features and split boundaries.
"""
from __future__ import annotations

import hashlib
import json
import lzma
import gzip
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as C


# ----------------------------------------------------------------- helpers
def _open_any(path: Path):
    """Open .csv, .csv.gz or .csv.xz read-only as a binary stream."""
    s = path.suffix.lower()
    if s == ".xz":
        return lzma.open(path, "rb")
    if s == ".gz":
        return gzip.open(path, "rb")
    return open(path, "rb")


def sha256_file(path, decompress=False) -> str:
    """SHA-256 of a file. decompress=True hashes the uncompressed CSV content (what the manifest stores)."""
    h = hashlib.sha256()
    opener = _open_any if decompress else (lambda p: open(p, "rb"))
    with opener(Path(path)) as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ----------------------------------------------------------------- S05
def load_frozen(path, manifest=None, verify=True) -> pd.DataFrame:
    """S05 — load the frozen dataset (.csv.xz/.gz/.csv) without modifying it.

    Adds: utc (tz-aware), hour_utc, hour_local (Europe/Madrid), series_id = "zone|sensor".
    Verifies the uncompressed SHA-256 against FROZEN_v*_MANIFEST.json if one is found next to the file.
    """
    path = Path(path)
    if manifest is None:
        manifest = next(path.parent.glob("FROZEN_v*_MANIFEST.json"), None)
    if verify and manifest is not None and Path(manifest).is_file():
        expected = json.loads(Path(manifest).read_text())["csv_sha256_uncompressed"]
        got = sha256_file(path, decompress=True)
        if got != expected:
            raise ValueError(f"Frozen dataset checksum mismatch: {got} != {expected}")

    with _open_any(path) as f:                       # read-only handle, source is never written
        df = pd.read_csv(f, low_memory=False)

    df["utc"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    n_bad = int(df["utc"].isna().sum())
    assert n_bad == 0, f"{n_bad} unparseable timestamps"
    df["hour_utc"] = df["utc"].dt.floor("h")
    df["hour_local"] = df["hour_utc"].dt.tz_convert(C.TZ_LOCAL)
    df["series_id"] = df["zone"] + "|" + df["sensor"]

    # consistency with the stored Madrid wall clock (QA'd in Task 4, re-checked cheaply here)
    local_naive = df["utc"].dt.tz_convert(C.TZ_LOCAL).dt.tz_localize(None)
    assert (local_naive == pd.to_datetime(df["timestamp_madrid"])).all(), "UTC/Madrid mismatch"
    return df


def recent_regime(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the minute-level 2025 regime only (2020–2023 is already hourly)."""
    return df[df["utc"] >= C.REGIME_CUT_UTC].sort_values(["series_id", "utc"]).reset_index(drop=True)


# ----------------------------------------------------------------- S06
def aggregate_energy_hourly(df: pd.DataFrame, threshold: int = C.THRESHOLD,
                            max_gap: float | None = C.ENERGY_MAX_GAP,
                            tail_max: float = C.ENERGY_TAIL_MAX) -> pd.DataFrame:
    """S06 — minute energy_Wh -> hourly sums per series.

    Returns one row per (series_id, hour_utc) on a COMPLETE hourly grid (hours without any row are included),
    with energy_Wh, energy_n_obs, energy_valid, energy_source (most frequent source in the hour).
    energy_Wh is NaN whenever the hour is not valid. Missing values are never filled with zero.

    Note: after a gap, energy_Wh of the next row covers the whole gap (checked in the data), so the hourly sum
    stays complete even when rows are missing. That is why THRESHOLD can sit well below 60.
    The flip side: after a long outage one row carries hours of energy. energy_max_gap_min records the longest
    preceding gap in the hour, and hours with a gap > max_gap are invalid (energy_catch_up = True).
    """
    d = df[["series_id", "utc", "hour_utc", "energy_Wh", "energy_source"]].sort_values(["series_id", "utc"])
    prev_gap = d.groupby("series_id")["utc"].diff().dt.total_seconds() / 60
    d = d.assign(prev_gap=prev_gap.where(d["energy_Wh"].notna()))
    has_e = d["energy_Wh"].notna()
    g = d.groupby(["series_id", "hour_utc"])
    out = pd.DataFrame({
        "energy_Wh": g["energy_Wh"].sum(min_count=1),
        "energy_n_obs": has_e.groupby([d["series_id"], d["hour_utc"]]).sum().astype(int),
        "energy_max_gap_min": g["prev_gap"].max(),
    })
    src = (d.groupby(["series_id", "hour_utc", "energy_source"]).size()
             .reset_index(name="n").sort_values(["series_id", "hour_utc", "n", "energy_source"],
                                                ascending=[True, True, False, True])
             .drop_duplicates(["series_id", "hour_utc"]).set_index(["series_id", "hour_utc"])["energy_source"])
    out["energy_source"] = src
    # v1.2 — share of the hour's energy readings whose energy_Wh was derived by `spread` in the frozen dataset
    is_spread = (d["energy_source"] == "spread") & has_e
    out["energy_spread_share"] = (is_spread.groupby([d["series_id"], d["hour_utc"]]).sum()
                                  / out["energy_n_obs"].where(out["energy_n_obs"] > 0))

    # v1.1 — pre-outage hours. A long gap that STARTS in an earlier hour moves the end of that hour's energy into
    # the catch-up row of a later hour, so the earlier hour's sum is too low. energy_tail_gap_min = minutes at the
    # end of the hour that lie inside such a gap; above tail_max the hour is invalid (energy_pre_outage).
    if max_gap is not None:
        prev_t = d["utc"] - pd.to_timedelta(d["prev_gap"], unit="min")
        start_h = prev_t.dt.floor("h")
        tail = (np.minimum(d["utc"], start_h + pd.Timedelta(hours=1)) - prev_t).dt.total_seconds() / 60
        m = (d["prev_gap"] > max_gap) & (start_h < d["hour_utc"])
        out["energy_tail_gap_min"] = (pd.DataFrame({"series_id": d.loc[m, "series_id"], "hour_utc": start_h[m],
                                                    "t": tail[m]}).groupby(["series_id", "hour_utc"])["t"].max())
    else:
        out["energy_tail_gap_min"] = np.nan

    # complete grid: every series x every hour of the regime
    if len(d):
        hours = pd.date_range(d["hour_utc"].min(), d["hour_utc"].max(), freq="h")
        grid = pd.MultiIndex.from_product([sorted(d["series_id"].unique()), hours], names=["series_id", "hour_utc"])
        out = out.reindex(grid)
    out["energy_n_obs"] = out["energy_n_obs"].fillna(0).astype(int)
    out["energy_catch_up"] = (out["energy_max_gap_min"] > max_gap) if max_gap is not None else False
    out["energy_pre_outage"] = out["energy_tail_gap_min"] > tail_max
    out["energy_valid"] = (out["energy_n_obs"] >= threshold) & ~out["energy_catch_up"] & ~out["energy_pre_outage"]
    out.loc[~out["energy_valid"], "energy_Wh"] = np.nan
    return out.reset_index()


# ----------------------------------------------------------------- S06b (v1.2)
def consistency_check(h: pd.DataFrame, ratio: float = C.CONSISTENCY_RATIO, tol: float = C.CONSISTENCY_TOL_WH,
                      zero_w: float = C.ZERO_WITH_POWER_W) -> pd.DataFrame:
    """S06b — energy vs power per hour (DECISIONS_v1.2.md D2, D3). Needs the S06 and S07 columns.

    energy_checked       the hour had valid energy AND a valid power mean (W_valid), so it could be checked
    energy_inconsistent  checked and energy_Wh > ratio * W_mean + tol: more energy than the measured power can
                         deliver in one hour -> the hour becomes invalid (energy_Wh = NaN)
    energy_zero_with_power  valid energy == 0 while W_mean > zero_w: counted only, never flagged (D3)
    One-sided on purpose: hand dryers have energy far BELOW the sampled power and are not an error.
    """
    h = h.copy()
    ok = h["energy_valid"] & h["W_valid"].fillna(False).astype(bool)
    h["energy_checked"] = ok
    h["energy_inconsistent"] = ok & (h["energy_Wh"] > ratio * h["W_mean"] + tol)
    h["energy_zero_with_power"] = h["energy_valid"] & (h["energy_Wh"] == 0) & (h["W_mean"] > zero_w)
    h.loc[h["energy_inconsistent"], "energy_valid"] = False
    h.loc[~h["energy_valid"], "energy_Wh"] = np.nan
    return h


# ----------------------------------------------------------------- S07
def _weighted_hourly(df: pd.DataFrame, col: str, max_gap: float, min_cov: float) -> pd.DataFrame:
    d = df.loc[df[col].notna(), ["series_id", "utc", col]].sort_values(["series_id", "utc"])
    nxt = d.groupby("series_id")["utc"].shift(-1)
    gap = (nxt - d["utc"]).dt.total_seconds() / 60
    w = gap.clip(upper=max_gap).fillna(1.0)            # last reading of a series: assume one minute
    start = d["utc"]
    end = start + pd.to_timedelta(w, unit="min")
    h0 = start.dt.floor("h")
    boundary = h0 + pd.Timedelta(hours=1)
    # split segments that cross the hour boundary (max_gap <= 60 -> at most one crossing)
    w_first = np.minimum(end, boundary).sub(start).dt.total_seconds() / 60
    w_second = (end - boundary).dt.total_seconds().clip(lower=0) / 60
    parts = pd.concat([
        pd.DataFrame({"series_id": d["series_id"], "hour_utc": h0, "w": w_first, "x": d[col], "obs": 1}),
        pd.DataFrame({"series_id": d["series_id"], "hour_utc": boundary, "w": w_second, "x": d[col], "obs": 0}),
    ])
    parts = parts[parts["w"] > 0]
    parts["wx"] = parts["w"] * parts["x"]
    g = parts.groupby(["series_id", "hour_utc"])
    res = pd.DataFrame({f"{col}_cov_min": g["w"].sum(), f"{col}_n_obs": g["obs"].sum().astype(int)})
    res[f"{col}_mean"] = g["wx"].sum() / res[f"{col}_cov_min"]
    res[f"{col}_valid"] = res[f"{col}_cov_min"] >= min_cov
    res.loc[~res[f"{col}_valid"], f"{col}_mean"] = np.nan
    return res


def hourly_power_current(df: pd.DataFrame, max_gap: float = C.MAX_GAP, min_cov: float = C.MIN_COVERAGE_MIN) -> pd.DataFrame:
    """S07 — coverage-aware, time-weighted hourly means of W and I.

    W and I are instantaneous readings, so they are averaged, not summed. Each reading is assumed to hold until
    the next one, capped at max_gap minutes, and is split across the hour boundary if needed.

    Why not a simple arithmetic mean: readings are irregular (1–8 min gaps). A plain mean gives every reading the
    same weight, so stretches with dense sampling dominate the hour and a reading followed by a long gap counts
    as little as one followed by one minute. If gaps correlate with the load state, the hourly mean is biased.
    The cap prevents a single reading from being stretched over a long outage.
    """
    a = _weighted_hourly(df, "W", max_gap, min_cov)
    b = _weighted_hourly(df, "I", max_gap, min_cov)
    return a.join(b, how="outer").reset_index()


# ----------------------------------------------------------------- S08
def add_split_and_calendar(h: pd.DataFrame, splits=C.SPLITS) -> pd.DataFrame:
    """S08 — split column (train/validation/test/outside) and calendar features from Madrid local time."""
    import holidays

    h = h.copy()
    h["hour_local"] = h["hour_utc"].dt.tz_convert(C.TZ_LOCAL)
    h["split"] = "outside"
    bounds = {k: (pd.Timestamp(s, tz=C.SPLIT_TZ), pd.Timestamp(e, tz=C.SPLIT_TZ)) for k, (s, e) in splits.items()}
    for name, (s, e) in bounds.items():
        h.loc[(h["hour_utc"] >= s) & (h["hour_utc"] < e), "split"] = name

    # splits must not overlap
    ordered = sorted(bounds.values())
    for (s1, e1), (s2, e2) in zip(ordered, ordered[1:]):
        assert e1 <= s2, f"splits overlap: {s1}-{e1} and {s2}-{e2}"

    loc = h["hour_local"]
    h["hour"] = loc.dt.hour
    h["weekday"] = loc.dt.weekday            # 0 = Monday
    h["month"] = loc.dt.month
    h["is_weekend"] = h["weekday"] >= 5
    years = sorted(loc.dt.year.unique())
    hol = holidays.country_holidays(C.HOLIDAY_COUNTRY, subdiv=C.HOLIDAY_SUBDIV, years=years)
    h["is_holiday"] = loc.dt.date.map(lambda d: d in hol)
    return h


# ----------------------------------------------------------------- S09
def save_derived(h: pd.DataFrame, source_path, out_dir="derived", version=C.DERIVED_VERSION) -> tuple[Path, Path]:
    """S09 — versioned parquet + JSON metadata (source checksum, parameters, row counts)."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / f"Storey1_hourly_v{version}.parquet"
    meta_p = out_dir / f"Storey1_hourly_v{version}_META.json"
    if pq.exists():
        raise FileExistsError(f"{pq} exists — bump DERIVED_VERSION instead of overwriting")
    h.to_parquet(pq, index=False)
    counts = h.groupby(["series_id", "split"]).size().unstack(fill_value=0)
    meta = dict(
        derived_dataset=pq.name, derived_version=version,
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_file=Path(source_path).name, source_dataset_version=C.DATASET_VERSION,
        source_sha256_file=sha256_file(source_path),
        source_sha256_uncompressed_csv=sha256_file(source_path, decompress=True),
        derived_sha256=sha256_file(pq),
        parameters=dict(THRESHOLD=C.THRESHOLD, ENERGY_MAX_GAP=C.ENERGY_MAX_GAP, ENERGY_TAIL_MAX=C.ENERGY_TAIL_MAX, MAX_GAP=C.MAX_GAP, MIN_COVERAGE_MIN=C.MIN_COVERAGE_MIN,
                        CONSISTENCY_RATIO=C.CONSISTENCY_RATIO, CONSISTENCY_TOL_WH=C.CONSISTENCY_TOL_WH, ZERO_WITH_POWER_W=C.ZERO_WITH_POWER_W,
                        decisions="DECISIONS_v1.2.md",
                        SPLITS=C.SPLITS, SPLIT_TZ=C.SPLIT_TZ, SPLIT_SOURCE="Task 6 (task6.pdf §4)", TZ_LOCAL=C.TZ_LOCAL, REGIME="recent_2025 (utc >= 2024-01-01)",
                        holidays=f"{C.HOLIDAY_COUNTRY}/{C.HOLIDAY_SUBDIV}"),
        rows_total=len(h), n_series=int(h["series_id"].nunique()),
        rows_by_series_split={s: {k: int(v) for k, v in r.items()} for s, r in counts.iterrows()},
    )
    meta_p.write_text(json.dumps(meta, indent=2))
    return pq, meta_p


# ----------------------------------------------------------------- S10
def eligibility(h: pd.DataFrame, share=C.ELIGIBILITY_SHARE, expected=C.EXPECTED_HOURS,
                min_train=C.MIN_TRAIN_HOURS, max_flag=C.MAX_FLAGGED_TRAIN_SHARE, min_scale=C.MIN_SCALE_HOURS) -> pd.DataFrame:
    """S10 — share of valid energy hours in validation and test (denominator = expected hours, not observed).

    v1.2: `eligible`/`core` (>= share in validation AND test) only marks circuits for the core table (D5).
    `in_training` (D4) decides which circuits are used to FIT models. Every circuit is forecast and scored."""
    rows = []
    for sid, g in h.groupby("series_id"):
        r = {"series_id": sid}
        reasons = []
        for split, n_exp in expected.items():
            n_valid = int(g.loc[g["split"] == split, "energy_valid"].sum())
            r[f"{split}_valid_hours"] = n_valid
            r[f"{split}_share"] = round(n_valid / n_exp, 4)
            if n_valid / n_exp < share:
                reasons.append(f"{split}: {n_valid}/{n_exp} valid hours ({n_valid / n_exp:.1%} < {share:.0%})")
        r["eligible"] = not reasons                  # v1.2: = "high_coverage" (reporting only, D5)
        r["reason"] = "; ".join(reasons) if reasons else ""
        # v1.2 (D4) — training set rule, identical for every circuit. Needs S06b columns; skipped on older data.
        if "energy_inconsistent" in g:
            tr = g[g["split"] == "train"]
            n_valid, n_chk = int(tr["energy_valid"].sum()), int(tr["energy_checked"].sum())
            n_flag = int(tr["energy_inconsistent"].sum())
            fshare = n_flag / n_chk if n_chk else 0.0     # energy_checked includes the flagged hours (set before flagging)
            why = []
            if n_valid < min_train:
                why.append(f"{n_valid} valid training hours < {min_train}")
            if fshare > max_flag:
                why.append(f"{fshare:.0%} of checked training hours inconsistent > {max_flag:.0%}")
            r.update(train_valid_hours=n_valid, train_checked_hours=n_chk, train_flagged_hours=n_flag,
                     train_flagged_share=round(fshare, 4), in_training=not why, training_reason="; ".join(why),
                     has_scale=n_valid >= min_scale)
        rows.append(r)
    out = pd.DataFrame(rows)
    out.insert(1, "high_coverage", out["eligible"])
    return out


def eligibility_to_excel(elig: pd.DataFrame, path, sensitivity: pd.DataFrame | None = None):
    path = Path(path)
    with pd.ExcelWriter(path) as xw:
        elig.to_excel(xw, sheet_name="all_series", index=False)
        if "in_training" in elig:
            elig[elig["in_training"]].to_excel(xw, sheet_name="training", index=False)
            elig[~elig["in_training"]].to_excel(xw, sheet_name="not_in_training", index=False)
        elig[elig["eligible"]].to_excel(xw, sheet_name="high_coverage", index=False)
        elig[~elig["eligible"]].to_excel(xw, sheet_name="low_coverage", index=False)
        if sensitivity is not None:
            sensitivity.to_excel(xw, sheet_name="gap_sensitivity", index=False)
    return path


# ----------------------------------------------------------------- S11
def _pairs(y_true, y_pred):
    t = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    if t.shape != p.shape:
        raise ValueError(f"shape mismatch: {t.shape} vs {p.shape}")
    m = ~(np.isnan(t) | np.isnan(p))
    if not m.any():
        raise ValueError("no valid (non-NaN) pairs")
    return t[m], p[m], int(m.sum())


def mae(y_true, y_pred) -> tuple[float, int]:
    """S11 — mean absolute error over pairs where neither value is NaN. Returns (mae, n_valid_pairs)."""
    t, p, n = _pairs(y_true, y_pred)
    return float(np.mean(np.abs(t - p))), n


def rmse(y_true, y_pred) -> tuple[float, int]:
    """S11 — root mean squared error over pairs where neither value is NaN. Returns (rmse, n_valid_pairs)."""
    t, p, n = _pairs(y_true, y_pred)
    return float(np.sqrt(np.mean((t - p) ** 2))), n
