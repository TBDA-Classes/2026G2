"""Rebuild the whole UX package from the repository inputs.   Usage (from anywhere):  python source/run_all.py
Steps (about 1-2 minutes, no GPU, no internet):
  1 prep_presence.py        presence detector hourly series
  2 analysis_occupancy.py   occupancy rule evidence
  3 analysis_standby_wi.py  standby baseline, W and I redundancy
  4 analysis_accuracy.py    MAPE, CV(RMSE), WAPE, band coverage
  5 build_data.py           expected values, alerts, impact -> source/data.json
  6 injection_test.py       injected-anomaly detection test (adds results to data.json)
  7 build_html.py           index.html
Inputs (read-only, in the repository): CLEAN DATA all zones.zip, TBDA_v1.3_ChronosGBM_29-10/{derived,results}, Task6_rev0_03-11/results/predictions."""
import subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
repo = here.parent.parent
need = [repo / "CLEAN DATA all zones.zip", repo / "TBDA_v1.3_ChronosGBM_29-10" / "derived" / "Storey1_hourly_v1.2.parquet",
        repo / "TBDA_v1.3_ChronosGBM_29-10" / "results" / "chronos_test_predictions_v1.3.parquet",
        repo / "Task6_rev0_03-11" / "results" / "predictions" / "ML_Blend_v1.3_test_predictions.csv"]
miss = [str(p) for p in need if not p.exists()]
if miss:
    sys.exit("Missing input(s). Run this script from a clone of the repository, with this folder inside it:\n  " + "\n  ".join(miss))
for step in ["prep_presence", "analysis_occupancy", "analysis_standby_wi", "analysis_accuracy", "build_data", "injection_test", "build_html"]:
    print(f"\n=== {step} ===", flush=True)
    r = subprocess.run([sys.executable, str(here / f"{step}.py")], stdout=subprocess.DEVNULL if step.startswith("analysis") else None)
    if r.returncode: sys.exit(f"step {step} failed")
print("\nDone: index.html, source/data.json, analysis/*.csv")
