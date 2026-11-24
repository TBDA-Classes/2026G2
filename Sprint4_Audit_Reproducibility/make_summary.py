"""Put the results of the three levels together and write the audit summary.

Run from the repository root (after check_files.py, check_numbers.py and rerun_scripts.py):
  python Sprint4_Audit_Reproducibility/make_summary.py
Writes results/audit_matrix.csv (one line per check) and results/audit_summary.md.
"""
import platform
import re
from datetime import date
from importlib import metadata

import pandas as pd

from common import RESULTS, read_plan, result

LEVELS = ["L1 exists", "L2 matches", "L3 reproduces", "manual"]
STATUSES = ["PASS", "FAIL", "ERROR", "NOT RUN", "MANUAL"]
WORST_FIRST = ["ERROR", "FAIL", "NOT RUN", "MANUAL", "PASS"]


def load_results():
    parts = []
    for level in ("L1", "L2", "L3"):
        f = RESULTS / f"{level}_results.csv"
        done = pd.read_csv(f, dtype=str).fillna("") if f.exists() else pd.DataFrame(columns=["check_id"])
        plan = read_plan(level)
        missing = [result(c, "NOT RUN") for _, c in plan.iterrows() if c["check_id"] not in set(done["check_id"])]
        parts += [done, pd.DataFrame(missing)]
    manual = [result(c, "MANUAL", "", c["note"]) for _, c in read_plan("manual").iterrows()]
    parts.append(pd.DataFrame(manual))
    return pd.concat([p for p in parts if len(p)], ignore_index=True).fillna("")


def backlog_table(matrix):
    """Worst status of the checks linked to each backlog item (PB-01 ... PB-58)."""
    rows = []
    for n in range(1, 59):
        pb = f"PB-{n:02d}"
        linked = matrix[matrix["pb"].apply(lambda text: pb in re.split(r"[;\s]+", text))]
        if len(linked):
            worst = min(linked["status"], key=WORST_FIRST.index)
            rows.append((pb, worst, ", ".join(linked["check_id"])))
        else:
            rows.append((pb, "paths only", "L1-02 (the paths cited for this item exist)"))
    return rows


def versions():
    names = ["pandas", "numpy", "scikit-learn", "scipy", "pyarrow", "prophet", "torch", "chronos-forecasting", "dash"]
    out = [f"Python {platform.python_version()} ({platform.system()})"]
    for name in names:
        try:
            out.append(f"{name} {metadata.version(name)}")
        except metadata.PackageNotFoundError:
            out.append(f"{name} not installed")
    return ", ".join(out)


def main():
    matrix = load_results()
    matrix.to_csv(RESULTS / "audit_matrix.csv", index=False, encoding="utf-8")

    counts = pd.crosstab(matrix["level"], matrix["status"]).reindex(index=LEVELS, columns=STATUSES, fill_value=0)
    lines = ["# Audit summary", "",
             f"Date: {date.today().isoformat()}  ", f"Environment: {versions()}", "",
             "## Results by level", "",
             "| Level | " + " | ".join(STATUSES) + " | Total |", "|---|" + "---|" * (len(STATUSES) + 1)]
    for level, row in counts.iterrows():
        lines.append(f"| {level} | " + " | ".join(str(v) for v in row) + f" | {row.sum()} |")
    lines.append(f"| **All** | " + " | ".join(str(v) for v in counts.sum()) + f" | **{counts.values.sum()}** |")

    lines += ["", "## Checks that did not pass", "", "| Check | Status | What | Expected | Obtained | Detail |",
              "|---|---|---|---|---|---|"]
    for _, r in matrix[~matrix["status"].isin(["PASS", "MANUAL"])].iterrows():
        detail = r["detail"].replace("|", "/")[:300]
        lines.append(f"| {r['check_id']} | {r['status']} | {r['what']} | {r['expected']} | {r['obtained']} | {detail} |")

    lines += ["", "## Backlog items", "", "| Item | Worst status | Checks |", "|---|---|---|"]
    lines += [f"| {pb} | {status} | {checks} |" for pb, status, checks in backlog_table(matrix)]

    (RESULTS / "audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(counts)
    print(f"wrote {RESULTS / 'audit_matrix.csv'} and {RESULTS / 'audit_summary.md'}")


if __name__ == "__main__":
    main()
