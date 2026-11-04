"""Task 6 — rebuild Model 1 (Linear Regression, all 16 circuits, design B) from PARAMETERS.md.

The original task1_linear_all16.py was not in the repository. Pooled LAD (QuantileRegressor, alpha 0.001), no circuit
identity, trained on the 8 NE/NW circuits, each circuit scaled by its own training mean. The rebuilt test forecasts
match results/linear_test_predictions_all16.csv within 0.0005 Wh, so its validation forecasts can be used.
Run inside the Task78_rev0_19-10 folder:  python3 task6_linear_rebuild.py
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '../Task6_rev0_03-11'); import minipq
pd.read_parquet = lambda p, **k: minipq.read_parquet(p)
import config as C
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import QuantileRegressor
from task7_baselines import load_derived, forecast_tasks
from task8_model import FEATURES, _series_frames, fit_cutoff, build_features, series_scale, predictions_frame
CAT = ["hour", "weekday"]; NUM = [f for f in FEATURES if f not in CAT + ["is_weekend"]]
h = load_derived(); fr = _series_frames(h)
S8 = ["NE|HVAC","NE|Plugs & Sockets","NW|Emerg. Lighting","NW|HVAC","NW|Hand Dryer","NW|Lighting","NW|Plugs & Sockets","NW|RACK"]
ALL = sorted(h.series_id.unique()); out = []
for hz in C.HORIZONS:
    cut = fit_cutoff(h, hz, S8)
    sc = series_scale(h, cut)                                     # every circuit, own training mean
    t = forecast_tasks(h, hz, "train", S8); t = t[t.target_time < cut].reset_index(drop=True)
    F = build_features(h, t, sc, frames=fr); F = F[F.y_scaled.notna()]
    prep = ColumnTransformer([("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True), StandardScaler()), NUM),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
    m = make_pipeline(prep, QuantileRegressor(quantile=0.5, alpha=0.001, solver="highs")).fit(F[NUM + CAT], F.y_scaled)
    print(hz, "train rows", len(F))
    for sp in ("validation", "test"):
        T = build_features(h, forecast_tasks(h, hz, sp, ALL), sc, frames=fr)
        out.append(predictions_frame(T, np.clip(m.predict(T[NUM + CAT]), 0, None) * T.scale.to_numpy(), "linear_regression"))
P = pd.concat(out, ignore_index=True); P.to_pickle("results/task6_linear_rebuild.pkl")
# compare test with official file
o = pd.read_csv("results/linear_test_predictions_all16.csv")
o["target_hour"] = pd.to_datetime(o.target_hour, utc=True)
circ = "zone" if o.zone.astype(str).str.contains("\\|").any() else "circuit_zone"
o = o.rename(columns={circ: "series_id"}); hm = {1: "+1h", 6: "+6h", 24: "day-ahead"}; o["horizon"] = o.horizon_h.map(hm)
T = P[P.split == "test"].merge(o, left_on=["series_id", "horizon", "target_time"], right_on=["series_id", "horizon", "target_hour"])
print("rows matched", len(T), "max abs diff Wh", np.nanmax(np.abs(T.y_pred - T.predicted_Wh)))
