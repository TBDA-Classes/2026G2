"""Run S05–S10 end to end.

    python run_task7.py --data data/Storey1_ALL_ZONES_FROZEN_v1.0.csv.xz [--out derived]
"""
import argparse
from pathlib import Path

import pandas as pd

import config as C
from task7_pipeline import (load_frozen, recent_regime, aggregate_energy_hourly, hourly_power_current,
                            consistency_check, add_split_and_calendar, save_derived, eligibility, eligibility_to_excel,
                            sha256_file)

ap = argparse.ArgumentParser()
ap.add_argument("--data", type=Path, required=True)
ap.add_argument("--out", type=Path, default=Path("derived"))
a = ap.parse_args()

sha_before = sha256_file(a.data)
df = load_frozen(a.data)                                                     # S05
print(f"S05 loaded {len(df):,} rows, {df.series_id.nunique()} series")
rec = recent_regime(df)
e = aggregate_energy_hourly(rec)                                             # S06
p = hourly_power_current(rec)                                                # S07
h = consistency_check(e.merge(p, on=["series_id", "hour_utc"], how="left"))   # S06b (v1.2)
h = add_split_and_calendar(h)                                                # S08
print(f"S06–S08 hourly rows {len(h):,}; energy valid {h.energy_valid.mean():.1%}; W valid {h.W_valid.mean():.1%}")
print(h.groupby("split").hour_utc.agg(["min", "max", "size"]))
pq, meta = save_derived(h, a.data, a.out)                                    # S09
print(f"S09 wrote {pq} and {meta}")

elig = eligibility(h)                                                        # S10
sens = []                                                                    # v1.2: gap-rule sensitivity
for g in [15, 20, 30]:
    hg = add_split_and_calendar(consistency_check(aggregate_energy_hourly(rec, max_gap=g)
                                                  .merge(p, on=["series_id", "hour_utc"], how="left")))
    el = eligibility(hg)
    for _, r in el.iterrows():
        sens.append({"ENERGY_MAX_GAP": g, "series_id": r.series_id, "train_valid_hours": r.train_valid_hours,
                     "validation_share": r.validation_share, "test_share": r.test_share,
                     "high_coverage": r.high_coverage, "in_training": r.in_training})
sens = pd.DataFrame(sens)
x = eligibility_to_excel(elig, Path(C.ELIGIBILITY_FILE), sens)
print(elig.to_string(index=False)); print(sens.to_string(index=False)); print(f"S10 wrote {x}")

assert sha256_file(a.data) == sha_before, "source file changed!"
print("source file unchanged (sha256 identical before and after)")
