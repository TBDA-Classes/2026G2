"""Level 3 - REPRODUCES: run the team's scripts again and compare the new files with the files in the repository.

The scripts run in a COPY of the repository, never in the repository itself.
Before a script runs, the files it should create are deleted from the copy, so an old file cannot pass by mistake.

Run from the repository root:
  python Sprint4_Audit_Reproducibility/rerun_scripts.py                 all level-3 checks
  python Sprint4_Audit_Reproducibility/rerun_scripts.py L3-02 L3-05     only some checks
Writes Sprint4_Audit_Reproducibility/results/L3_results.csv and one log file per check in results/logs/.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from common import REPO, RESULTS, compare_tables, read_plan, result, same_values, save_results, split_list, tolerance

COPY = Path(tempfile.gettempdir()) / "tbda_audit_copy"
LOGS = RESULTS / "logs"
TIME_LIMIT = 3600  # seconds per check

# Settings for every script: UTF-8 text, no plot windows
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", MPLBACKEND="Agg", TBDA_REPO=str(COPY))


def make_copy():
    """Fresh copy of the repository (without git files, local caches or this audit folder)."""
    if COPY.exists():
        shutil.rmtree(COPY)
    skip = shutil.ignore_patterns(".git", ".venv", "__pycache__", "cache", "data_live", "Sprint4_Audit_Reproducibility")
    shutil.copytree(REPO, COPY, ignore=skip)
    (COPY / "audit_tmp").mkdir()
    print(f"copy of the repository: {COPY}")


def run(command, folder, log):
    """Run one command (text) in `folder`. Returns True if it finished without error."""
    args = shlex.split(command)
    if args[0] == "python":
        args[0] = sys.executable  # same Python as the audit
    log.write(f"\n$ {command}   (in {folder})\n")
    log.flush()
    p = subprocess.run(args, cwd=folder, env=ENV, stdout=log, stderr=subprocess.STDOUT, timeout=TIME_LIMIT)
    return p.returncode == 0


def run_task6(log):
    """The six comparisons of Task6_rev0_03-11/run_task6_all.sh, written in Python (no bash needed)."""
    folder = COPY / "Task6_rev0_03-11"
    m16 = ("ML_RandomForest ML_Linear ML_GBM_v1.3 ML_Chronos_v1.3 ML_ChronosGBM_v1.3 ML_Blend_v1.3 "
           "B1_last_week B2_weekday_hour_median B3_persistence").split()
    m8 = m16 + ["ML_GBM_v1.0", "ML_Chronos_v1.1"]
    runs = [("task6_test_16circuits", "test", m16, "Test", False),
            ("task6_test_8circuits", "test", m8, "Test", False),
            ("task6_test_16circuits_without_events", "test", m16, "Test", True),
            ("task6_test_8circuits_without_events", "test", m8, "Test", True),
            ("task6_validation_16circuits", "validation", m16, "Validation", False),
            ("task6_validation_8circuits", "validation", m8, "Validation", False)]
    for out, split, models, label, no_events in runs:
        env = dict(ENV, SCALE_FILE="data/task6_circuit_scale_train_mean_v1.2.csv",
                   EVENTS_FILE="data/task6_events_test.csv", OUT_DIR=f"results/{out}", SPLIT_LABEL=label)
        if no_events:
            env["EXCLUDE_EVENTS"] = "1"
        (folder / "results" / out).mkdir(parents=True, exist_ok=True)
        files = [f"results/predictions/{m}_{split}_predictions.csv" for m in models]
        log.write(f"\n$ task6_compare.py -> results/{out}\n")
        log.flush()
        p = subprocess.run([sys.executable, "task6_compare.py", *files], cwd=folder, env=env,
                           stdout=log, stderr=subprocess.STDOUT, timeout=TIME_LIMIT)
        if p.returncode != 0:
            return False
    return True


def get_chronos_weights(log):
    """Put the official Chronos-Bolt weights in weights/ of the copy, as README_v1.3.md asks.
    They are not in git. The first time this downloads them from Hugging Face (about 250 MB).
    The team's script then checks their SHA-256 against chronos_frozen_config_v1.3.json."""
    from huggingface_hub import snapshot_download
    model_dir = COPY / "TBDA_v1.3_ChronosGBM_29-10"
    cfg = json.loads((model_dir / "models" / "chronos_frozen_config_v1.3.json").read_text())
    for size in sorted({c["size"] for c in cfg["horizons"].values()}):
        path = snapshot_download(f"amazon/chronos-bolt-{size}")
        shutil.copytree(path, model_dir / "weights" / f"chronos-bolt-{size}", dirs_exist_ok=True)
        log.write(f"weights chronos-bolt-{size}: {path}\n")


def dash_band_coverage(log):
    """Ask the Dash app for the share of test hours inside its 90 % band, per horizon."""
    code = ("import sys, json; sys.path.insert(0, 'Sprint4_Task3_UX_Dash/core'); import data_layer as D; "
            "c = D.interval_coverage('test'); print(json.dumps([round(100 * v, 1) for v in c['coverage']]))")
    p = subprocess.run([sys.executable, "-c", code], cwd=COPY, env=ENV, capture_output=True, text=True)
    log.write(p.stdout + p.stderr)
    return json.loads(p.stdout.strip().splitlines()[-1])


def files_to_compare(check):
    """Pairs (new file in the copy, original file in the repository)."""
    pairs = []
    outputs = split_list(check["output"])
    originals = split_list(check["file"])
    for i, pattern in enumerate(originals):
        if outputs:  # the script writes to another place
            pairs.append((COPY / outputs[i], REPO / pattern))
        else:  # the script writes to the same place; a * pattern is allowed
            for original in sorted(REPO.glob(pattern)):
                pairs.append((COPY / original.relative_to(REPO), original))
    return pairs


def run_check(check, log):
    command = check["command"]
    tol = tolerance(check["tolerance"])

    if command == "function":  # only L3-05 (Dash band)
        obtained = "/".join(str(v) for v in dash_band_coverage(log))
        return result(check, "PASS" if same_values(check["expected"], obtained, tol) else "FAIL", obtained)

    pairs = files_to_compare(check) if check["file"] and check["expected"] != "all pass" else []
    for new, original in pairs:  # delete old copies, so the script must make them again
        if new.exists() and new != original:
            new.unlink()

    if command == "task6_all":
        ok = run_task6(log)
    elif command == "chronos_test":
        get_chronos_weights(log)
        ok = run("python run_v13_chronos_test.py", COPY / "TBDA_v1.3_ChronosGBM_29-10", log)
    else:
        ok = all(run(c, COPY, log) for c in command.split("; "))
    if not ok:
        return result(check, "FAIL", "script failed", f"see results/logs/{check['check_id']}.txt")
    if not pairs:
        return result(check, "PASS", "script finished without error")

    problems, notes = [], []
    for new, original in pairs:
        if not new.exists():
            problems.append(f"{new.name}: not created")
        elif new.suffix == ".json":  # compare the content, so line endings changed by git do not matter
            same = json.loads(new.read_text(encoding="utf-8")) == json.loads(original.read_text(encoding="utf-8"))
            (notes if same else problems).append(f"{new.name}: {'identical' if same else 'different'}")
        else:
            same, why = compare_tables(new, original, tol)
            (notes if same else problems).append(f"{new.name}: {why}")
    status = "PASS" if not problems else "FAIL"
    return result(check, status, f"{len(pairs) - len(problems)} of {len(pairs)} files the same",
                  " | ".join(problems + notes))


def main():
    only = sys.argv[1:]
    make_copy()
    LOGS.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, check in read_plan("L3").iterrows():
        if only and check["check_id"] not in only:
            continue
        start = time.time()
        print(f"{check['check_id']} {check['what']} ...", flush=True)
        with open(LOGS / f"{check['check_id']}.txt", "w", encoding="utf-8") as log:
            try:
                row = run_check(check, log)
            except Exception as e:  # a broken check must not stop the audit
                row = result(check, "ERROR", "", f"{type(e).__name__}: {e}")
        row["seconds"] = round(time.time() - start)
        rows.append(row)
        print(f"   {row['status']}  {row['obtained']}  ({row['seconds']} s)")
    old_file = RESULTS / "L3_results.csv"
    if only and old_file.exists():  # keep the results of the checks that were not run this time
        old = pd.read_csv(old_file, dtype=str).fillna("")
        rows = [r for r in old.to_dict("records") if r["check_id"] not in only] + rows
        rows.sort(key=lambda r: r["check_id"])
    save_results(rows, "L3_results.csv")


if __name__ == "__main__":
    main()
