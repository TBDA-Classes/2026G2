"""v1.2 — what the frozen ChronosGBM hybrid uses (VALIDATION only; explains the result, chooses nothing).

    python run_v12_hybrid_importance.py

Permutation importance, shuffled WITHIN each circuit (shuffling across circuits would mix circuits with
different levels and exaggerate every effect):
- chronos_inputs_by_circuit: validation scaled MAE of the frozen hybrid, and after shuffling all Chronos inputs
  together; increase > 0 = the Chronos inputs help that circuit
- single_feature: increase of the selection metric (training circuits) when one input is shuffled
5 repeats, seed 0. Writes results/hybrid_importance_v1.2.xlsx.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

import config as C
from task7_baselines import load_derived, eligible_series, forecast_tasks
from task8_model import _series_frames, predictions_frame, scaled_mae_by_series
from hybrid_model import CHR_SCALED, HYBRID_FEATURES, load_cache, build_features_hybrid

cfg = json.loads(Path(C.HYBRID_FROZEN_CONFIG).read_text())
h = load_derived(C.DERIVED_PATH)
S_all, S_train = cfg["series"], cfg["training_series"]
frames, cache = _series_frames(h), load_cache()
CHR = CHR_SCALED + ["chr_ctx_h"]
rng = np.random.default_rng(C.SEED)


def shuffle_within(K, cols, rng):
    Kp = K.copy()
    for _, idx in K.groupby("series_id").groups.items():
        idx = np.asarray(idx)
        Kp.loc[idx, cols] = K.loc[rng.permutation(idx), cols].to_numpy()
    return Kp


group_rows, single_rows = [], []
for hz, hc in cfg["horizons"].items():
    m = joblib.load(Path("models") / hc["model_file"])
    scale = pd.Series(hc["scale_Wh"])
    K = build_features_hybrid(h, forecast_tasks(h, hz, "validation", S_all), scale, cache, frames=frames)
    K = K[K["y_true"].notna()].reset_index(drop=True)
    base = scaled_mae_by_series(predictions_frame(K, m.predict(K), "x"), scale)
    for rep in range(5):
        per = scaled_mae_by_series(predictions_frame(Kp := shuffle_within(K, CHR, rng), m.predict(Kp), "x"), scale)
        group_rows += [dict(horizon=hz, series_id=s, repeat=rep, sMAE=base[s], sMAE_chronos_shuffled=per[s])
                       for s in per.index]
        for f in HYBRID_FEATURES:
            Kf = shuffle_within(K, [f], rng)
            pf = scaled_mae_by_series(predictions_frame(Kf, m.predict(Kf), "x"), scale)
            single_rows.append(dict(horizon=hz, feature=f, repeat=rep,
                                    increase=float(pf.reindex(S_train).mean() - base.reindex(S_train).mean())))
    print(hz, "done")

g = pd.DataFrame(group_rows).groupby(["horizon", "series_id"])[["sMAE", "sMAE_chronos_shuffled"]].mean()
g["increase"] = g["sMAE_chronos_shuffled"] - g["sMAE"]
g["increase_pct"] = (100 * g["increase"] / g["sMAE"]).round(1)
sgl = (pd.DataFrame(single_rows).groupby(["horizon", "feature"])["increase"].mean().unstack("horizon")
       .sort_values("day-ahead", ascending=False).round(4))
with pd.ExcelWriter(f"results/hybrid_importance_{C.TAG}.xlsx") as xw:
    pd.DataFrame({"sheet": ["chronos_inputs_by_circuit", "single_feature"],
                  "content": ["Validation scaled MAE of the frozen hybrid, and after shuffling all Chronos inputs "
                              "together within each circuit (5 repeats). increase > 0 = Chronos inputs help.",
                              "Increase of the selection metric when one input is shuffled within each circuit "
                              "(5 repeats)."]}).to_excel(xw, sheet_name="README", index=False)
    g.round(4).reset_index().to_excel(xw, sheet_name="chronos_inputs_by_circuit", index=False)
    sgl.reset_index().to_excel(xw, sheet_name="single_feature", index=False)
pd.set_option("display.width", 200)
print(g["increase_pct"].unstack("horizon").to_string())
print(sgl.head(8).to_string())
