"""v1.3 — blend of the three FROZEN v1.3 models: w_gbm x GBM + w_hyb x ChronosGBM + w_chr x Chronos,
weights on a 0.05 grid that sum to 1 (231 combinations, incl. every two-model blend and each model alone).
Chosen on VALIDATION with rule D10, frozen. Then the final model per horizon is chosen with D10 across models.

    python run_v13_blend_tune.py               (after the GBM, Chronos and hybrid v1.3 scripts)
    python run_v13_blend_tune.py --smoke       (reads/writes results/smoke/)

Writes models/blend_frozen_config_v1.3.json, results/blend_tuning_log_v1.3.csv,
results/blend_validation_predictions_v1.3.parquet, results/model_choice_v1.3.csv and
models/model_choice_v1.3.json (= the model choice per horizon that is committed before the test run).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from selection import (scaled_scores, d10_choose, blend_weight_grid, require_d10_agreed, baseline_reference,
                       add_baseline_columns, write_baseline_reference)
from task7_pipeline import sha256_file
from task7_baselines import eligible_series

ap = argparse.ArgumentParser()
ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()
R, M = (Path("results/smoke"), Path("results/smoke")) if args.smoke else (Path("results"), Path("models"))
frozen = M / Path(C.FROZEN_V13["blend"]).name
choice_json = M / f"model_choice_{C.TAG13}.json"
if not args.smoke:
    require_d10_agreed()
for f in (frozen, choice_json):
    if f.exists():
        raise SystemExit(f"{f} exists — frozen. Delete it deliberately to re-tune.")

S_train = eligible_series(C.ELIGIBILITY_FILE, which="training")
cfgs = {m: json.loads((M / Path(C.FROZEN_V13[m]).name).read_text()) for m in ("task8", "chronos", "hybrid")}
KEY = ["series_id", "horizon", "issue_time", "target_time", "lead"]
g = pd.read_parquet(R / f"task8_validation_predictions_{C.TAG13}.parquet")
c = pd.read_parquet(R / f"chronos_validation_predictions_{C.TAG13}.parquet")
y = pd.read_parquet(R / f"hybrid_validation_predictions_{C.TAG13}.parquet")
base = g[g["model"] != "ML_GBM"]
g = g[g["model"] == "ML_GBM"]
W = blend_weight_grid()
assert len(W) == 231 or args.smoke

blog, chosen, bpreds = [], {}, []
for hz in C.HORIZONS:
    scale = pd.Series(cfgs["task8"]["horizons"][hz]["scale_Wh"])
    m = (g[g["horizon"] == hz][KEY + ["split", "y_true", "y_pred"]].rename(columns={"y_pred": "p_gbm"})
         .merge(y[y["horizon"] == hz][KEY + ["y_pred"]].rename(columns={"y_pred": "p_hyb"}), on=KEY, validate="1:1")
         .merge(c[c["horizon"] == hz][KEY + ["y_pred"]].rename(columns={"y_pred": "p_chr"}), on=KEY, validate="1:1"))
    rows = []
    for i, (wg, wh, wc) in enumerate(W):
        P = m.assign(y_pred=wg * m["p_gbm"] + wh * m["p_hyb"] + wc * m["p_chr"])
        s = scaled_scores(P, scale, S_train)
        rows.append(dict(horizon=hz, combo=i, w_gbm=wg, w_hybrid=wh, w_chronos=wc,
                         **{k: v for k, v in s.items() if not k.startswith("per_series")}))
    hl = pd.DataFrame(rows)
    j, hl = d10_choose(hl)
    ref, ref_tab = baseline_reference(base[base["horizon"] == hz], scale, S_train, hz)
    hl = add_baseline_columns(hl, ref)
    blog.append(hl)
    r = hl.loc[j]
    chosen[hz] = dict(w_gbm=float(r["w_gbm"]), w_hybrid=float(r["w_hybrid"]), w_chronos=float(r["w_chronos"]),
                      validation_score=round(float(r["mean_scaled_MAE"]), 6),
                      validation_scaled_RMSE=round(float(r["mean_scaled_RMSE"]), 6),
                      n_tied=int(hl["d10_tied"].sum()), best_score=round(float(hl["mean_scaled_MAE"].min()), 6))
    bpreds.append(m.assign(y_pred=r["w_gbm"] * m["p_gbm"] + r["w_hybrid"] * m["p_hyb"] + r["w_chronos"] * m["p_chr"],
                           model="ML_Blend").drop(columns=["p_gbm", "p_hyb", "p_chr"]))
    print(f"{hz}: D10 chose GBM {r['w_gbm']:.2f} / ChronosGBM {r['w_hybrid']:.2f} / Chronos {r['w_chronos']:.2f}  "
          f"score {r['mean_scaled_MAE']:.4f} ({chosen[hz]['n_tied']} tied)")
pd.concat(blog, ignore_index=True).to_csv(R / f"blend_tuning_log_{C.TAG13}.csv", index=False)
B = pd.concat(bpreds, ignore_index=True)
B.to_parquet(R / f"blend_validation_predictions_{C.TAG13}.parquet", index=False)
frozen.write_text(json.dumps(dict(
    model="ML_Blend", grid_version=C.TAG13, created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    rule="w_gbm x frozen GBM + w_hybrid x frozen ChronosGBM + w_chronos x frozen Chronos point forecast; weights on a "
         f"{C.BLEND_STEP_V13} grid summing to 1, chosen per horizon on validation by rule D10.",
    d10_agreed=C.D10_AGREED, n_combinations=len(W),
    configs={k: sha256_file(M / Path(C.FROZEN_V13[k]).name) for k in ("task8", "chronos", "hybrid")},
    horizons=chosen), indent=2))

# ---- final model per horizon (D10 across models; each model on its own forecasts, training circuits)
ALL = pd.concat([base, g, c[g.columns.intersection(c.columns)], y, B[[col for col in g.columns if col in B.columns]]],
                ignore_index=True)
models = [mm for mm in C.D10_SIMPLICITY if C.D10_INCLUDE_BASELINES or mm.startswith("ML_")]
tracked = [mm for mm in C.D10_SIMPLICITY if mm not in models]          # D10a/D10c: scored, never chosen
final, rows_all, ref_tables = {}, [], []
for hz in C.HORIZONS:
    scale = pd.Series(cfgs["task8"]["horizons"][hz]["scale_Wh"])
    A = ALL[(ALL["horizon"] == hz) & ALL["model"].isin(models)]
    rows = []
    for mm in models:
        s = scaled_scores(A[A["model"] == mm], scale, S_train)
        rows.append(dict(horizon=hz, model=mm, simplicity=C.D10_SIMPLICITY.index(mm),
                         **{k: v for k, v in s.items() if not k.startswith("per_series")}))
    hl = pd.DataFrame(rows).reset_index(drop=True)
    ref, ref_tab = baseline_reference(ALL[ALL["horizon"] == hz], scale, S_train, hz)
    ref_tables.append(ref_tab)
    piv = A.pivot_table(index=KEY, columns="model", values="y_pred", aggfunc="first")
    ident = {}
    for i, mi in enumerate(hl["model"]):                      # identical forecasts -> simplest one
        for k, mk in enumerate(hl["model"][:i]):
            if mk in piv and mi in piv and np.nanmax(np.abs(piv[mi] - piv[mk])) < C.D10_IDENTICAL_EPS \
                    and (piv[mi].isna() == piv[mk].isna()).all():
                ident[i] = k
                break
    j, hl = d10_choose(hl, simplicity_col="simplicity", identical_to=ident)
    hl["candidate"] = True
    tr = ref_tab[ref_tab["model"].isin(tracked)][["horizon", "model", "mean_scaled_MAE", "mean_scaled_RMSE",
                                                  "score_all16", "score_core8"]]
    tr = tr.assign(simplicity=tr["model"].map(C.D10_SIMPLICITY.index), candidate=False, d10_tied=False,
                   d10_chosen=False)
    hl = add_baseline_columns(pd.concat([hl, tr], ignore_index=True), ref)
    rows_all.append(hl)
    final[hz] = dict(model=hl.loc[j, "model"], validation_score=round(float(hl.loc[j, "mean_scaled_MAE"]), 6),
                     validation_scaled_RMSE=round(float(hl.loc[j, "mean_scaled_RMSE"]), 6),
                     tied=hl.loc[hl["d10_tied"].astype(bool), "model"].tolist(),
                     best_baseline=ref["best_baseline"], best_baseline_score=round(ref["best_baseline_MAE"], 6),
                     gap_to_best_baseline=round(float(hl.loc[hl["d10_chosen"].astype(bool), "gap_to_best_baseline"].iloc[0]), 6),
                     baselines_within_tie_margin=[b for b in tracked if ref.get(f"ref_{b}_MAE", 9) <=
                                                  float(hl.loc[hl["d10_chosen"].astype(bool), "mean_scaled_MAE"].iloc[0])
                                                  + C.D10_TIE_MARGIN])
    print(f"{hz}: final model = {final[hz]['model']}  (tied: {final[hz]['tied']}); best baseline "
          f"{ref['best_baseline']} {ref['best_baseline_MAE']:.4f}, gap {final[hz]['gap_to_best_baseline']:+.4f}"
          + (f"; WITHIN TIE MARGIN: {final[hz]['baselines_within_tie_margin']} -> state in the report"
             if final[hz]['baselines_within_tie_margin'] else ""))
pd.concat(rows_all, ignore_index=True).to_csv(R / f"model_choice_{C.TAG13}.csv", index=False)
write_baseline_reference(ref_tables, R / f"baseline_reference_{C.TAG13}.csv")
choice_json.write_text(json.dumps(dict(
    created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), d10_agreed=C.D10_AGREED,
    d10=dict(tie_margin=C.D10_TIE_MARGIN, tie_break="mean scaled RMSE over the training circuits",
             include_baselines=C.D10_INCLUDE_BASELINES, simplicity=C.D10_SIMPLICITY,
             baselines="tracked as reference in every tuning log and here (D10c), not candidates (D10a)"),
    note="Chosen on validation only. Commit this file BEFORE any test forecast is made (point 8).",
    horizons=final), indent=2))
print(f"wrote {frozen}, {choice_json}")
