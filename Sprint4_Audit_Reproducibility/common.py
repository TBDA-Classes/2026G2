"""Small helpers used by all audit scripts.

The audit folder must sit in the root of the repository (next to Task6_rev0_03-11, etc.).
Another repository folder can be given with the environment variable TBDA_REPO.
"""
import hashlib
import os
from pathlib import Path

import numpy as np
import pandas as pd

AUDIT_DIR = Path(__file__).resolve().parent
REPO = Path(os.environ.get("TBDA_REPO", AUDIT_DIR.parent)).resolve()
PLAN = AUDIT_DIR / "audit_checks.csv"
RESULTS = AUDIT_DIR / "results"


def read_plan(level):
    """Rows of the audit plan for one level: "L1", "L2", "L3" or "manual"."""
    plan = pd.read_csv(PLAN, dtype=str, encoding="utf-8").fillna("")
    return plan[plan["level"].str.startswith(level)]


def split_list(text):
    """'a;b; c' -> ['a', 'b', 'c']"""
    return [part.strip() for part in text.split(";") if part.strip()]


def tolerance(text):
    """'exact' or '' -> 0.0; '0.05' -> 0.05; '1e-6 Wh' -> 1e-06."""
    text = text.strip()
    if text in ("", "exact"):
        return 0.0
    return float(text.split()[0])


def same_value(expected, obtained, tol):
    """Compare one expected value with one obtained value (numbers with a tolerance, text exactly)."""
    try:
        return abs(float(expected) - float(obtained)) <= tol + 1e-12
    except ValueError:
        return str(expected).strip() == str(obtained).strip()


def same_values(expected, obtained, tol):
    """Compare 'a/b/c' with 'x/y/z', value by value."""
    e, o = str(expected).split("/"), str(obtained).split("/")
    return len(e) == len(o) and all(same_value(a, b, tol) for a, b in zip(e, o))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_table(path):
    path = Path(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)


def compare_tables(new_path, old_path, tol):
    """Is the new table the same as the old one? Returns (True/False, short explanation).

    Numbers may differ by at most `tol`. Text must be equal. Row order does not matter.
    """
    new, old = read_table(new_path), read_table(old_path)
    if list(new.columns) != list(old.columns):
        return False, f"different columns: {sorted(set(new.columns) ^ set(old.columns))}"
    if len(new) != len(old):
        return False, f"different number of rows: {len(new)} vs {len(old)}"
    numbers = [c for c in old.columns if pd.api.types.is_float_dtype(old[c])]
    others = [c for c in old.columns if c not in numbers]
    if others:  # sort both tables the same way
        new = new.sort_values(others, kind="stable").reset_index(drop=True)
        old = old.sort_values(others, kind="stable").reset_index(drop=True)
    for c in others:  # empty cells count as equal
        if not (new[c].astype(str).fillna("") == old[c].astype(str).fillna("")).all():
            return False, f"column '{c}' has different values"
    max_diff = 0.0
    for c in numbers:
        a = pd.to_numeric(new[c], errors="coerce").to_numpy(float)
        b = old[c].to_numpy(float)
        if not (np.isnan(a) == np.isnan(b)).all():
            return False, f"column '{c}' has empty values in different rows"
        both = ~np.isnan(a)
        if both.any():
            max_diff = max(max_diff, float(np.max(np.abs(a[both] - b[both]))))
    if max_diff <= tol:
        return True, f"same ({len(old)} rows, largest difference {max_diff:.2g})"
    return False, f"largest difference {max_diff:.3g} is above the tolerance {tol}"


def result(check, status, obtained="", detail=""):
    """One line of the results table."""
    return {"check_id": check["check_id"], "level": check["level"], "pb": check["pb"], "claim": check["claim"],
            "what": check["what"], "status": status, "expected": check["expected"],
            "obtained": obtained, "detail": detail}


def save_results(rows, name):
    RESULTS.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(RESULTS / name, index=False, encoding="utf-8")
    print(f"wrote {RESULTS / name} ({len(rows)} checks)")
