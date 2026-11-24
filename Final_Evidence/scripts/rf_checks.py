"""Random Forest checks for 15_Random_Forest_Justification.md.

Run from the repository root:
    python Final_Evidence/scripts/rf_checks.py
Needs pandas. Unzips nothing; reads Task6_rev0_03-11 and Model3_RandomForest.zip.

Writes
  Final_Evidence/analysis/rf_d10_style_check.csv
      Mean scaled MAE over the 15 v1.3 training circuits (all except SE|Plugs & Sockets),
      on the Task 6 common hours, validation and test. Scale = v1.2 training mean
      (Task6_rev0_03-11/data). Not the official D10 score (that uses each model's own
      forecasts); a like-for-like check of whether RF could have been chosen.
  Final_Evidence/analysis/rf_seed_noise.csv
      Seed-to-seed sd and standard error of the 5-seed mean, as % of the score
      (from Model3_RandomForest.zip results/step3_stage2_seeds.csv).
"""
import io
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(".")
T6 = ROOT / "Task6_rev0_03-11"
OUT = ROOT / "Final_Evidence" / "analysis"
MODELS = ["ML_Blend_v1.3", "ML_Chronos_v1.3", "ML_ChronosGBM_v1.3", "ML_GBM_v1.3",
          "ML_RandomForest", "ML_Linear", "B3_persistence"]
HORIZON = {1: "+1h", 6: "+6h", 24: "day-ahead"}


def d10_style():
    scale = pd.read_csv(T6 / "data" / "task6_circuit_scale_train_mean_v1.2.csv").set_index("circuit").scale_Wh
    rows = []
    for split in ["validation", "test"]:
        d = pd.read_csv(T6 / "results" / f"task6_{split}_16circuits" / "metrics_per_circuit.csv")
        d = d[(d.circuit != "SE|Plugs & Sockets") & d.model.isin(MODELS)].copy()
        assert d.circuit.nunique() == 15
        d["scaled_MAE"] = d.MAE_Wh / d.circuit.map(scale)
        g = d.groupby(["horizon_h", "model"]).scaled_MAE.mean().reset_index()
        g["split"] = split
        rows.append(g)
    out = pd.concat(rows)
    out["horizon"] = out.horizon_h.map(HORIZON)
    best = out[out.model != "B3_persistence"].groupby(["split", "horizon"]).scaled_MAE.min()
    out["gap_to_best_ML"] = out.scaled_MAE - out.set_index(["split", "horizon"]).index.map(best)
    out = out[["split", "horizon", "model", "scaled_MAE", "gap_to_best_ML"]].round(4)
    out.to_csv(OUT / "rf_d10_style_check.csv", index=False)
    print(out.pivot_table(index="model", columns=["split", "horizon"], values="scaled_MAE"))


def seed_noise():
    with zipfile.ZipFile(ROOT / "Model3_RandomForest.zip") as z:
        name = [n for n in z.namelist() if n.endswith("results/step3_stage2_seeds.csv")][0]
        s = pd.read_csv(io.BytesIO(z.read(name)))
    a = s.groupby(["horizon", "config", "max_depth", "min_samples_leaf", "max_features"], dropna=False) \
         .sMAE_all16.agg(["mean", "std", "count"]).reset_index()
    a["sd_pct_of_score"] = 100 * a["std"] / a["mean"]
    a["se_pct_of_score"] = a.sd_pct_of_score / a["count"] ** 0.5
    a.round(5).to_csv(OUT / "rf_seed_noise.csv", index=False)
    print(a.groupby("horizon")[["sd_pct_of_score", "se_pct_of_score"]].agg(["min", "max"]).round(2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    d10_style()
    seed_noise()
