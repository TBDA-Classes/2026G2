"""Backlog PB-28 — Prophet as a time-series alternative, under the team protocol, on the VALIDATION week only.

    python Sprint4_Prophet_PB28/run_prophet_validation.py          (from the repository root)

Why: the backlog (PB-28) asks for a time-series alternative "such as Prophet". Chronos-Bolt fills that role, but
Prophet itself was never tested (06_Backlog_Coverage.md: "Partly"; oral defence audit: "Why not Prophet? Not tested").
This script tests it with the same rules as every other model, so the team can answer with a number.

Same as the v1.3 models (TBDA_v1.3_ChronosGBM_29-10/): dataset v1.2 (checksum verified on load), same splits,
same forecast tasks (task7_baselines.forecast_tasks), same per-circuit training mean as scale (task8_model.series_scale,
checked against the frozen GBM v1.3 config), same score (selection.scaled_scores: mean scaled MAE over the 15 training
circuits, D6) and the same tie rule inside the grid (selection.d10_choose, D10). Grid of 112 configurations (D11: >= 100).

What Prophet can and cannot do here. Prophet is fitted once per circuit on its own TRAINING hours before the earliest
fit cut-off of the three horizons (fit_cutoff of +6h = 21 Sep 19:00 UTC, safe for all three), then it extrapolates
trend + weekly + daily seasonality. The protocol forbids fitting on validation hours, so Prophet is NOT refitted during
the week: unlike the lag-based models it never sees the hours just before the issue time. Its forecast for a target
hour is therefore the same at every horizon; the three scores differ only through each horizon's scale (circuit
training mean before that horizon's cut-off, as for every model). SE|Plugs & Sockets is not a training circuit (D4) and Prophet cannot forecast a circuit it
was not fitted on, so it is left out; the score uses the 15 training circuits, like every model.

Nothing here changes the model choice (models/model_choice_v1.3.json). The test week is never read.
Writes into Sprint4_Prophet_PB28/results/.
"""
import json
import logging
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
V13 = HERE.parent / "TBDA_v1.3_ChronosGBM_29-10"
OUT = HERE / "results"

GRID = [dict(changepoint_prior_scale=cps, seasonality_prior_scale=sps, seasonality_mode=mode, daily=daily)
        for cps in (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 0.5)
        for sps in (0.01, 0.1, 1.0, 10.0)
        for mode in ("additive", "multiplicative")
        for daily in ("single", "weekday_weekend")]                           # 7 x 4 x 2 x 2 = 112
DAILY_FOURIER = 6                                                             # Prophet's default order for daily
ML = "ML_Prophet"


class _FallbackCounter(logging.Handler):
    """Counts Prophet's 'Falling back to Newton' messages (its L-BFGS fit stopped early and Newton finished it)."""
    n = 0

    def emit(self, record):
        if "Falling back to Newton" in record.getMessage():
            _FallbackCounter.n += 1


def _quiet():
    import cmdstanpy
    if hasattr(cmdstanpy, "disable_logging"):
        cmdstanpy.disable_logging()                     # its own handler prints every Stan run otherwise
    for name in ("prophet", "prophet.models"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        lg.handlers = [_FallbackCounter()]
        lg.propagate = False


def local_naive(ts: pd.Series) -> pd.Series:
    """UTC timestamps -> Madrid wall-clock time without tz (Prophet needs naive ds; no DST change in the window)."""
    return ts.dt.tz_convert("Europe/Madrid").dt.tz_localize(None)


def with_conditions(df: pd.DataFrame) -> pd.DataFrame:
    wd = df["ds"].dt.weekday < 5
    return df.assign(is_weekday=wd, is_weekend=~wd)


def train_frame(h: pd.DataFrame, series_id: str, cutoff) -> pd.DataFrame:
    """Valid TRAINING hours of one circuit that start before `cutoff` (energy_Wh is NaN for invalid hours)."""
    d = h[(h["series_id"] == series_id) & (h["split"] == "train") & (h["hour_utc"] < cutoff) & h["energy_Wh"].notna()]
    assert (d["hour_utc"] < cutoff).all() and (d["split"] == "train").all()
    return with_conditions(pd.DataFrame({"ds": local_naive(d["hour_utc"]).to_numpy(), "y": d["energy_Wh"].to_numpy()}))


def make_model(p: dict):
    from prophet import Prophet
    m = Prophet(changepoint_prior_scale=p["changepoint_prior_scale"],
                seasonality_prior_scale=p["seasonality_prior_scale"], seasonality_mode=p["seasonality_mode"],
                yearly_seasonality=False, weekly_seasonality=True,
                daily_seasonality=(p["daily"] == "single"), uncertainty_samples=0)
    if p["daily"] == "weekday_weekend":           # a building's day looks different on weekdays and weekends
        m.add_seasonality("daily_weekday", period=1, fourier_order=DAILY_FOURIER, condition_name="is_weekday")
        m.add_seasonality("daily_weekend", period=1, fourier_order=DAILY_FOURIER, condition_name="is_weekend")
    return m


def prophet_forecast(train: pd.DataFrame, targets_utc: pd.Series, p: dict) -> np.ndarray:
    """Fit on `train`, forecast the given target hours; negative forecasts are clipped to 0 (team rule)."""
    m = make_model(p).fit(train)
    fut = with_conditions(pd.DataFrame({"ds": local_naive(targets_utc).to_numpy()}))
    return np.clip(m.predict(fut)["yhat"].to_numpy(), 0.0, None)


def main():
    _quiet()
    sys.path.insert(0, str(V13))
    os.chdir(V13)                                                      # team code uses paths relative to its folder
    import config as C
    from selection import scaled_scores, d10_choose
    from task7_baselines import load_derived, eligible_series, forecast_tasks, _attach_truth
    from task8_model import fit_cutoff, series_scale
    import prophet, cmdstanpy

    assert len(GRID) == 112 and len({tuple(sorted(p.items())) for p in GRID}) == 112
    OUT.mkdir(parents=True, exist_ok=True)
    h = load_derived(C.DERIVED_PATH)                                   # verifies the v1.2 checksum
    S_all = eligible_series(C.ELIGIBILITY_FILE, which="all")
    S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
    gbm = json.loads(Path(C.FROZEN_V13["task8"]).read_text())
    choice = json.loads(Path("models/model_choice_v1.3.json").read_text())
    blend = pd.read_parquet("results/blend_validation_predictions_v1.3.parquet")
    base_ref = pd.read_csv("results/baseline_reference_v1.3.csv")

    # One fit per circuit and configuration, on training hours before the EARLIEST fit cut-off of the three horizons
    # (+6h: 21 Sep 19:00 UTC). That cut-off is safe for every horizon, and one fit serves all three (3x faster).
    cuts = {hz: fit_cutoff(h, hz, S_all) for hz in C.HORIZONS}
    cut0 = min(cuts.values())
    trains = {s: train_frame(h, s, cut0) for s in S_train}
    val_hours = pd.Series(sorted(h.loc[h["split"] == "validation", "hour_utc"].unique()))
    tasks, scales = {}, {}
    for hz in C.HORIZONS:
        scales[hz] = series_scale(h, cuts[hz])
        ref = pd.Series(gbm["horizons"][hz]["scale_Wh"])
        assert np.allclose(scales[hz].reindex(ref.index), ref, rtol=0, atol=1e-5), "scale differs from frozen GBM"
        tasks[hz] = _attach_truth(h, forecast_tasks(h, hz, "validation", S_train), "energy_Wh")
        assert (tasks[hz]["split"] == "validation").all()              # no test row is ever built here
        assert tasks[hz]["target_time"].isin(val_hours).all()

    def frame(hz, fc):
        P = tasks[hz].copy()
        idx = pd.MultiIndex.from_arrays([P["series_id"], P["target_time"]])
        P["y_pred"], P["model"] = fc.reindex(idx).to_numpy(), ML
        return P

    rows, fcs = {hz: [] for hz in C.HORIZONS}, []
    for i, p in enumerate(GRID):
        fb0 = _FallbackCounter.n
        fc = pd.concat({s: pd.Series(prophet_forecast(trains[s], val_hours, p), index=val_hours.to_numpy())
                        for s in S_train})                              # index (series_id, hour_utc)
        fcs.append(fc)
        msg = []
        for hz in C.HORIZONS:
            s_ = scaled_scores(frame(hz, fc), scales[hz], S_train)
            rows[hz].append(dict(horizon=hz, config=i, **p, newton_fallbacks=_FallbackCounter.n - fb0,
                                 **{k: v for k, v in s_.items() if not k.startswith("per_series")},
                                 **{f"sMAE_{k}": v for k, v in s_["per_series_MAE"].items()}))
            msg.append(f"{s_['mean_scaled_MAE']:.4f}")
        print(f"  {i:3d} cps={p['changepoint_prior_scale']:<5g} sps={p['seasonality_prior_scale']:<5g} "
              f"{p['seasonality_mode']:14s} {p['daily']:15s} score {' / '.join(msg)}", flush=True)

    log, preds, chosen, compare, per_circuit = [], [], {}, [], []
    for hz in C.HORIZONS:
        cut, scale = cuts[hz], scales[hz]
        cand = [frame(hz, fc) for fc in fcs]
        hl = pd.DataFrame(rows[hz])
        j, hl = d10_choose(hl)
        r = hl.loc[j]
        log.append(hl)
        preds.append(cand[j])
        chosen[hz] = dict(config_index=int(j), **GRID[j], validation_score=round(float(r["mean_scaled_MAE"]), 6),
                          validation_scaled_RMSE=round(float(r["mean_scaled_RMSE"]), 6),
                          n_tied=int(hl["d10_tied"].sum()), best_score=round(float(hl["mean_scaled_MAE"].min()), 6),
                          prophet_fit_cutoff_utc=str(cut0), scale_cutoff_utc=str(cut),
                          training_hours={s: len(trains[s]) for s in S_train})

        # sanity check: the same scoring code gives the Blend score recorded in model_choice_v1.3.json
        b = blend[blend["horizon"] == hz]
        sb = scaled_scores(b, scale, S_train)
        assert abs(sb["mean_scaled_MAE"] - choice["horizons"][hz]["validation_score"]) < 1e-5, "Blend not reproduced"
        sp = scaled_scores(cand[j], scale, S_train)
        compare.append(dict(horizon=hz, model="ML_Blend_v1.3 (final model)", mean_scaled_MAE=sb["mean_scaled_MAE"],
                            mean_scaled_RMSE=sb["mean_scaled_RMSE"]))
        compare.append(dict(horizon=hz, model="ML_Prophet (best of 112)", mean_scaled_MAE=sp["mean_scaled_MAE"],
                            mean_scaled_RMSE=sp["mean_scaled_RMSE"]))
        for _, q in base_ref[base_ref["horizon"] == hz].iterrows():
            compare.append(dict(horizon=hz, model=q["model"], mean_scaled_MAE=q["mean_scaled_MAE"],
                                mean_scaled_RMSE=q["mean_scaled_RMSE"]))
        bl2 = base_ref[(base_ref["horizon"] == hz) & (base_ref["model"] == "B2_weekday_hour_median")].iloc[0]
        for s in S_train:
            per_circuit.append(dict(horizon=hz, series_id=s, prophet=sp["per_series_MAE"].get(s, np.nan),
                                    blend_v13=sb["per_series_MAE"].get(s, np.nan), B2_weekday_hour=bl2[f"sMAE_{s}"]))
        print(f"{hz}: D10 chose config {j} score {r['mean_scaled_MAE']:.4f} ({chosen[hz]['n_tied']} tied); "
              f"Blend v1.3 {sb['mean_scaled_MAE']:.4f}", flush=True)

    pd.concat(log, ignore_index=True).to_csv(OUT / "prophet_tuning_log.csv", index=False, float_format="%.6f")
    pd.concat(preds, ignore_index=True)[["series_id", "horizon", "issue_time", "target_time", "lead", "split", "y_true",
                                         "y_pred", "model"]].to_csv(OUT / "prophet_validation_predictions.csv",
                                                                    index=False, float_format="%.4f")
    pd.DataFrame(compare).to_csv(OUT / "comparison_validation.csv", index=False, float_format="%.4f")
    pd.DataFrame(per_circuit).to_csv(OUT / "per_circuit_validation.csv", index=False, float_format="%.4f")
    (OUT / "prophet_chosen_config.json").write_text(json.dumps(dict(
        model=ML, purpose="Backlog PB-28: Prophet tested under the v1.3 protocol. Not a candidate: the model choice "
                          "(model_choice_v1.3.json) is unchanged. Test week not used.",
        rule="Fitted per training circuit on its own training hours before the horizon's fit cut-off, no refit; "
             "chosen on validation by mean scaled MAE over the 15 training circuits (D6), ties by D10.",
        dataset=dict(file=Path(C.DERIVED_PATH).name, version=C.DERIVED_VERSION), training_series=S_train,
        n_configurations=len(GRID), grid=GRID, daily_fourier_order=DAILY_FOURIER, horizons=chosen,
        versions=dict(python=platform.python_version(), prophet=prophet.__version__, cmdstanpy=cmdstanpy.__version__,
                      pandas=pd.__version__, numpy=np.__version__),
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds")), indent=2))
    print(pd.DataFrame(compare).round(4).to_string(index=False))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
