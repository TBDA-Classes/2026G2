"""LIVE forecast with the frozen final model (Blend v1.3): the latest measured data and the forecast ahead.

The latest data in the repository (dataset v1.2) end on 13 Oct 2025, 14:00 UTC (16:00 Madrid). The week after the
test week (6 – 13 Oct 2025, split "outside") was never used to build, choose or score any model, so it is new data.

For that week and the hours after the last measurement this script makes the forecasts exactly as the frozen
model would have made them in real time:
  +1 h       every hour up to the first hour after the last measurement (= "next hour")
  +6 h       every hour up to six hours after the last measurement (= "the next six hours", each issued 6 h earlier)
  day-ahead  every day issued at 00:00 Madrid time, including today's (the rest of today is a forecast)

Nothing is fitted or tuned. Steps per horizon (same as Task6 .../run_task6_v13_predictions.py):
  1. Chronos-Bolt (frozen size / context / point per horizon) is RUN on the latest data   -> needs torch + chronos
  2. the frozen GBM v1.3 and ChronosGBM v1.3 (.joblib) predict from the same inputs
  3. blend with the frozen weights (models/blend_frozen_config_v1.3.json)

Usage (from anywhere; the dashboard calls it with the "Update live forecast" button):
    python live_engine.py OUTPUT.csv            live forecast (downloads Chronos-Bolt tiny + base on first use)
    python live_engine.py --check               self-test without torch: rebuilds the TEST week with the frozen
                                                Chronos cache and compares it with the stored Task 6 forecasts
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "core"))   # settings, data_layer, anomalies


import json
import os
import sys
import time
from pathlib import Path

import settings as S

H_MIN = 60
LIVE_START_UTC = "2025-10-06 00:00"          # first hour after the test week


def _setup():
    import pandas as pd
    os.chdir(S.MODEL_DIR)                    # the model code uses paths relative to its own folder
    sys.path.insert(0, str(S.MODEL_DIR))
    try:
        import pyarrow  # noqa: F401
    except ImportError:                      # the team's pure-Python parquet reader
        sys.path.insert(0, str(S.TASK6))
        import minipq
        pd.read_parquet = lambda p, **k: minipq.read_parquet(p)


def live_tasks(h, hz: str, start, now_issue, series):
    """All (series, issue_time, target_time, lead) of one horizon with target >= start and issue <= now_issue.

    issue_time follows the project convention: the forecast for `target` with lead L is issued at
    target - (L-1) h and uses only hours that START before the issue time.
    """
    import pandas as pd
    import config as C
    H = pd.Timedelta(hours=1)
    if hz == "day-ahead":
        loc0 = start.tz_convert(C.ISSUE_TZ_DAY_AHEAD).normalize().tz_localize(None)
        loc1 = now_issue.tz_convert(C.ISSUE_TZ_DAY_AHEAD).normalize().tz_localize(None)
        days = pd.date_range(loc0, loc1, freq="D")
        issues = days.tz_localize(C.ISSUE_TZ_DAY_AHEAD).tz_convert("UTC")
        t = pd.DataFrame([(i, i + (L - 1) * H, L) for i in issues for L in range(1, 25)],
                         columns=["issue_time", "target_time", "lead"])
        same_day = (t["target_time"].dt.tz_convert(C.ISSUE_TZ_DAY_AHEAD).dt.normalize()
                    == t["issue_time"].dt.tz_convert(C.ISSUE_TZ_DAY_AHEAD).dt.normalize())
        t = t[same_day & (t["issue_time"] <= now_issue)]
    else:
        L = 1 if hz == "+1h" else 6
        targets = pd.date_range(start, now_issue + (L - 1) * H, freq="h")
        t = pd.DataFrame({"target_time": targets, "lead": L})
        t["issue_time"] = t["target_time"] - (L - 1) * H
    t = t[t["target_time"] >= start]
    t = t.merge(pd.DataFrame({"series_id": list(series)}), how="cross")
    t["horizon"], t["split"] = hz, "live"
    return t[["series_id", "issue_time", "target_time", "lead", "horizon", "split"]].reset_index(drop=True)


def load_chronos(size: str, cfg: dict):
    """Frozen Chronos-Bolt weights: the team's local copy if present, else the official Hugging Face release.
    The file checksum is compared with the one recorded when the model was frozen."""
    import chronos_model as CM
    local = Path(f"weights/chronos-bolt-{size}")
    if (local / "model.safetensors").exists():
        path = local
    else:
        from huggingface_hub import snapshot_download
        path = Path(snapshot_download(f"amazon/chronos-bolt-{size}"))
    same = CM.sha256(path / "model.safetensors") == cfg["weights"][size]["model_sha256"]
    return CM.load_pipeline(path), same


def blend(h, fr, tasks_by_hz: dict, chronos_by_hz: dict):
    """Frozen GBM + ChronosGBM + Chronos point forecast -> Blend v1.3, Task 6 file format."""
    import joblib
    import numpy as np
    import pandas as pd
    import config as C
    from task8_model import build_features, predictions_frame
    from hybrid_model import build_features_hybrid
    gc = json.load(open(C.FROZEN_V13["task8"]))
    hc = json.load(open(C.FROZEN_V13["hybrid"]))
    cc = json.load(open(C.FROZEN_V13["chronos"]))
    bc = json.load(open(C.FROZEN_V13["blend"]))
    out = []
    for hz, tasks in tasks_by_hz.items():
        ch, cz = cc["horizons"][hz], chronos_by_hz[hz]
        G = build_features(h, tasks, pd.Series(gc["horizons"][hz]["scale_Wh"]), frames=fr)
        p_gbm = joblib.load("models/" + gc["horizons"][hz]["model_file"]).predict(G)
        F = build_features_hybrid(h, tasks, pd.Series(hc["horizons"][hz].get("scale_Wh") or gc["horizons"][hz]["scale_Wh"]),
                                  cz, frames=fr)
        assert (F[["series_id", "target_time"]].values == G[["series_id", "target_time"]].values).all()
        p_hyb = joblib.load("models/" + hc["horizons"][hz]["model_file"]).predict(F)
        col = "pred_median" if ch["point"] == "median" else "pred_mean_q"
        p_chr = np.clip(F.merge(cz[["series_id", "horizon", "issue_time", "lead", col]],
                                on=["series_id", "horizon", "issue_time", "lead"], how="left")[col].to_numpy(), 0, None)
        w = bc["horizons"][hz]
        p = w["w_gbm"] * p_gbm + w["w_hybrid"] * p_hyb + w["w_chronos"] * p_chr
        out.append(predictions_frame(G, p, "Blend_v1.3"))
    P = pd.concat(out, ignore_index=True)
    P["horizon_h"] = P.horizon.map({"+1h": 1, "+6h": 6, "day-ahead": 24})
    P["zone"] = P.series_id
    P["circuit_zone"] = P.series_id.str.split("|").str[0]
    P = P.rename(columns={"target_time": "target_hour", "y_true": "actual_Wh", "y_pred": "predicted_Wh", "lead": "lead_h"})
    P["model"] = "ML_Blend_v1.3"
    return P[["model", "zone", "circuit_zone", "horizon_h", "target_hour", "actual_Wh", "predicted_Wh", "lead_h",
              "issue_time"]]


def run_live(out_csv: str) -> None:
    _setup()
    import pandas as pd
    import config as C
    import chronos_v13 as CV
    import chronos_model as CM
    from task7_baselines import load_derived
    from task8_model import _series_frames

    t0 = time.time()
    h = load_derived(str(S.current_derived()))                          # newest data (update_data.py) if present
    fr = _series_frames(h)
    cc = json.load(open(C.FROZEN_V13["chronos"]))
    hc = json.load(open(C.FROZEN_V13["hybrid"]))
    series = hc["series"]
    last = h.loc[h["energy_Wh"].notna(), "hour_utc"].max()               # last measured hour (start of the hour)
    now_issue = last + pd.Timedelta(hours=1)                             # forecasts are issued "now"
    # the latest 8 days, never earlier than the first hour after the test week
    start = max(pd.Timestamp(LIVE_START_UTC, tz="UTC"), last.floor("D") - pd.Timedelta(days=7))
    grids = CM.series_grid(h)

    tasks, chron, weights_ok = {}, {}, {}
    pipes = {}
    for hz in C.HORIZONS:
        c = cc["horizons"][hz]
        size, L = c["size"], int(c["ctx_len"])
        if size not in pipes:
            pipes[size] = load_chronos(size, cc)
        pipe, weights_ok[size] = pipes[size]
        tasks[hz] = live_tasks(h, hz, start, now_issue, series)
        P9 = CV.forecasts9(pipe, h, tasks[hz], L, grids=grids)
        chron[hz] = P9.assign(size=size)
        print(f"{hz}: Chronos-Bolt {size}, context {L} h, {len(P9):,} forecasts", flush=True)

    P = blend(h, fr, tasks, chron)
    # Chronos-Bolt 10-90 % band of every horizon: the dashboard calibrates it per circuit into the forecast interval
    hzn = {"+1h": 1, "+6h": 6, "day-ahead": 24}
    band = pd.concat([chron[hz][["series_id", "issue_time", "lead", "q10", "q90"]].assign(horizon_h=hzn[hz])
                      for hz in chron if hz in hzn]).rename(columns={"series_id": "zone", "lead": "lead_h"})
    P = P.merge(band, on=["zone", "issue_time", "lead_h", "horizon_h"], how="left")
    P["is_future"] = pd.to_datetime(P["target_hour"], utc=True) > last
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    P.to_csv(out_csv, index=False)
    meta = {
        "created_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "last_measured_hour_utc": last.isoformat(),
        "issued_at_utc": now_issue.isoformat(),
        "live_start_utc": start.isoformat(),
        "dataset": str(S.current_derived().name) + (" (updated)" if "data_live" in str(S.current_derived()) else ""),
        "rows": int(len(P)),
        "future_rows": int(P["is_future"].sum()),
        "chronos_weights_match_frozen": weights_ok,
        "seconds": round(time.time() - t0, 1),
    }
    Path(out_csv).with_suffix(".json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta))


def run_check() -> None:
    """Rebuild the TEST week with this script's task builder + the frozen Chronos cache; must equal Task 6."""
    _setup()
    import numpy as np
    import pandas as pd
    import config as C
    from task7_baselines import load_derived, forecast_tasks
    from task8_model import _series_frames
    from hybrid_model import load_cache

    h = load_derived()
    fr = _series_frames(h)
    cc = json.load(open(C.FROZEN_V13["chronos"]))
    series = json.load(open(C.FROZEN_V13["hybrid"]))["series"]
    cache = load_cache("results/chronos_cache_v1.3_test.parquet", allow_test=True)
    start, end_issue = pd.Timestamp("2025-09-29 00:00", tz="UTC"), pd.Timestamp("2025-10-05 23:00", tz="UTC")
    tasks, chron = {}, {}
    for hz in C.HORIZONS:
        t = live_tasks(h, hz, start, end_issue, series)
        t = t[t["target_time"] <= end_issue].reset_index(drop=True)
        ref = forecast_tasks(h, hz, "test", series)
        key = ["series_id", "issue_time", "target_time", "lead"]
        same = t[key].sort_values(key).reset_index(drop=True).equals(ref[key].sort_values(key).reset_index(drop=True))
        print(f"{hz}: live task builder == forecast_tasks(test): {same}")
        assert same
        tasks[hz] = ref
        c = cc["horizons"][hz]
        chron[hz] = cache[(cache.horizon == hz) & (cache["size"] == c["size"]) & (cache.ctx_len == c["ctx_len"])]
    P = blend(h, fr, tasks, chron)
    S_ = pd.read_csv(S.PRED_DIR / "ML_Blend_v1.3_test_predictions.csv")
    k = ["zone", "horizon_h", "target_hour", "issue_time"]
    for d in (P, S_):
        d["target_hour"] = pd.to_datetime(d["target_hour"], utc=True)
        d["issue_time"] = pd.to_datetime(d["issue_time"], utc=True)
    j = S_.merge(P, on=k, suffixes=("_stored", "_live"))
    diff = float(np.abs(j["predicted_Wh_stored"] - j["predicted_Wh_live"]).max())
    print(json.dumps({"matched": int(len(j)), "stored": int(len(S_)), "max_abs_diff_Wh": diff}))
    assert len(j) == len(S_) and diff < 1e-6


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check":
        run_check()
    elif len(sys.argv) == 2:
        run_live(str(Path(sys.argv[1]).resolve()))
    else:
        sys.exit("usage: python live_engine.py OUTPUT.csv  |  python live_engine.py --check")
