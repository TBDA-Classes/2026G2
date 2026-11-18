"""Add new days of measurements to the dashboard (scalability).

The model stays frozen; only the data grow. This script rebuilds the hourly dataset with the team's own cleaning
pipeline (TBDA_v1.3_ChronosGBM_29-10/task7_pipeline.py: same rules as dataset v1.2) from the newest minute-level
export and saves it next to the app, in data_live/. The frozen dataset of the repository is never touched.
Then press "Compute / update live forecast" in the app (or run live_engine.py): the forecast starts from the new
last measurement automatically.

Accepted inputs (same formats the team already uses):
  - the zip or folder of the cleaned data, with one sub-folder per zone (NE/, NW/, SE/, SW/) holding
    clean_Storey1_<zone>_CLEAN_DATA.csv  (as in "CLEAN DATA all zones.zip")
  - one CSV for all zones with columns zone, sensor, Timestamp (UTC), energy_Wh, energy_source, W, I, ...
    (as Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz)

    python Sprint4_Task3_UX_Dash/engines/update_data.py "CLEAN DATA all zones.zip"
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "core"))   # settings, data_layer, anomalies


import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

import settings as S

ZONES = ("NE", "NW", "SE", "SW")


def _read_zone_files(src: Path) -> pd.DataFrame:
    parts = []
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                base = Path(name).name
                if base.startswith("clean_Storey1_") and base.endswith("_CLEAN_DATA.csv"):
                    zone = base.split("_")[2]
                    with z.open(name) as f:
                        parts.append(pd.read_csv(io.TextIOWrapper(f, "utf-8"), low_memory=False).assign(zone=zone))
    else:
        for p in sorted(src.rglob("clean_Storey1_*_CLEAN_DATA.csv")):
            parts.append(pd.read_csv(p, low_memory=False).assign(zone=p.name.split("_")[2]))
    if not parts:
        raise SystemExit(f"No clean_Storey1_<zone>_CLEAN_DATA.csv files found in {src}")
    return pd.concat(parts, ignore_index=True)


def load_any(src: Path) -> pd.DataFrame:
    df = _read_zone_files(src) if (src.is_dir() or src.suffix.lower() == ".zip") else \
        pd.read_csv(src, low_memory=False)
    missing = {"zone", "sensor", "Timestamp", "energy_Wh", "energy_source"} - set(df.columns)
    if missing:
        raise SystemExit(f"Columns missing in the input: {sorted(missing)}")
    df["utc"] = pd.to_datetime(df["Timestamp"], utc=True, errors="coerce")
    bad = int(df["utc"].isna().sum())
    if bad:
        print(f"warning: {bad} rows with an unreadable timestamp were dropped")
        df = df.dropna(subset=["utc"])
    df["hour_utc"] = df["utc"].dt.floor("h")
    df["series_id"] = df["zone"] + "|" + df["sensor"]
    for c in ("W", "I"):
        if c not in df:
            df[c] = float("nan")
    return df


def main(src: Path) -> None:
    t0 = time.time()
    out_dir = S.LIVE_DATA_DIR
    df = load_any(src.resolve())
    os.chdir(S.MODEL_DIR)
    sys.path.insert(0, str(S.MODEL_DIR))
    import config as C
    from task7_pipeline import (recent_regime, aggregate_energy_hourly, hourly_power_current, consistency_check,
                                add_split_and_calendar, sha256_file)
    rec = recent_regime(df)
    e = aggregate_energy_hourly(rec)
    p = hourly_power_current(rec)
    h = add_split_and_calendar(consistency_check(e.merge(p, on=["series_id", "hour_utc"], how="left")))
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / f"Storey1_hourly_v{C.DERIVED_VERSION}.parquet"
    tmp = pq.with_suffix(".tmp.parquet")
    h.to_parquet(tmp, index=False)
    tmp.replace(pq)
    last = h.loc[h["energy_Wh"].notna(), "hour_utc"].max()
    meta = {"derived_dataset": pq.name, "derived_version": C.DERIVED_VERSION, "derived_sha256": sha256_file(pq),
            "source": src.name, "built_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
            "first_hour_utc": str(h["hour_utc"].min()), "last_measured_hour_utc": str(last),
            "rows_total": len(h), "n_series": int(h["series_id"].nunique()),
            "note": "Built by Sprint4_Task3_UX_Dash/engines/update_data.py with the team's v1.2 pipeline (task7_pipeline.py)."}
    pq.with_name(pq.stem + "_META.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"rows": len(h), "last_measured_hour_utc": str(last), "seconds": round(time.time() - t0, 1),
                      "file": str(pq)}))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
