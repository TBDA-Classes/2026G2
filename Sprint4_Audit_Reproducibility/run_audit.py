"""Run the whole audit: level 1, level 2, level 3, then the summary.

Run from the repository root:
  python Sprint4_Audit_Reproducibility/run_audit.py            everything (level 3 takes about 30-60 minutes)
  python Sprint4_Audit_Reproducibility/run_audit.py --quick    levels 1 and 2 only (a few seconds)
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
steps = ["check_files.py", "check_numbers.py", "rerun_scripts.py", "make_summary.py"]
if "--quick" in sys.argv:
    steps.remove("rerun_scripts.py")

for step in steps:
    print(f"\n===== {step} =====", flush=True)
    subprocess.run([sys.executable, str(HERE / step)], check=True)
