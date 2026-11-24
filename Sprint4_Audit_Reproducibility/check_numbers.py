"""Level 2 - MATCHES: is the number written in the documents the number in the result files?

Three kinds of checks (column `type` of audit_checks.csv):
  value     read one cell of a CSV file: the row chosen by `filter`, the column named in `column`
  sha256    the fingerprint (SHA-256) of a file is the one recorded by the team
  function  a small calculation, written below (the name is in column `column`)

Run from the repository root:  python Sprint4_Audit_Reproducibility/check_numbers.py
Writes Sprint4_Audit_Reproducibility/results/L2_results.csv
"""
import json
import re

import pandas as pd

from common import REPO, read_plan, read_table, result, same_value, same_values, save_results, sha256, split_list, tolerance

HORIZONS = ["+1h", "+6h", "day-ahead"]
BLEND = "ML_Blend_v1.3"


def select_rows(table, filter_text):
    """Keep the rows where every 'column=value' of the filter is true."""
    for rule in split_list(filter_text):
        col, value = rule.split("=", 1)
        table = table[table[col].apply(lambda cell: same_value(value, cell, 0))]
    return table


# ---------- small calculations (type = function) ----------

def dataset_shape(path, check):
    d = read_table(path)
    col = next(c for c in ("series_id", "series", "circuit", "zone") if c in d.columns)
    return f"{len(d)} rows; {d[col].nunique()} circuits"


def splits(path, check):
    s = json.loads(path.read_text())["parameters"]["SPLITS"]
    return "/".join([s["train"][0][:10], s["validation"][0][:10], s["test"][0][:10], s["test"][1][:10]])


def gain_vs_b2(path, check):
    """Change of the Blend MAE against Baseline B, in %, per horizon."""
    t = pd.read_csv(path)
    t = t[t["scope"] == "all circuits"]
    out = []
    for h in HORIZONS:
        blend = t[(t.horizon == h) & (t.model == BLEND)]["MAE_Wh"].iloc[0]
        b2 = t[(t.horizon == h) & (t.model == "B2_weekday_hour_median")]["MAE_Wh"].iloc[0]
        out.append(f"{100 * (blend / b2 - 1):.1f}")
    return "/".join(out)


def pairwise_significant(path, check):
    """Is the Blend significantly better than the other model (CI of the difference excludes 0)?"""
    other = check["filter"].split("=")[1]
    t = pd.read_csv(path)
    t = t[t["scope"] == "all circuits"]
    out = []
    for h in HORIZONS:
        row = t[(t.horizon == h) & (((t.model_A == BLEND) & (t.model_B == other)) |
                                    ((t.model_A == other) & (t.model_B == BLEND)))].iloc[0]
        out.append(str(bool(row["significant"]) and row["better"] == BLEND))
    return "/".join(out)


def circuit_wins(path, check):
    other = check["filter"].split("=")[1]
    t = pd.read_csv(path)
    return "/".join(str(t[(t.horizon == h) & (t.model == BLEND) & (t.vs == other)]["circuits_better"].iloc[0])
                    for h in HORIZONS)


def d10_choice(path, check):
    """Rule D10, written again from DECISIONS_v1.2.md:
    1) candidates = models, not baselines; 2) tied = score <= best score + 0.005;
    3) among the tied ones, the lowest scaled RMSE wins; 4) equal RMSE: the simpler model wins.
    (Step 'identical forecasts -> simpler model' is not needed here: no tied forecasts are identical.)"""
    t = pd.read_csv(path)
    t = t[t["candidate"].astype(str) == "True"]
    out = []
    for h in HORIZONS:
        c = t[t.horizon == h]
        tied = c[c.mean_scaled_MAE <= c.mean_scaled_MAE.min() + 0.005]
        out.append(tied.sort_values(["mean_scaled_RMSE", "simplicity"]).iloc[0]["model"])
    return "/".join(out)


def blend_weights(path, check):
    w = json.loads(path.read_text())["horizons"]
    return ";".join("/".join(str(w[h][k]) for k in ("w_gbm", "w_hybrid", "w_chronos")) for h in HORIZONS)


def ashrae_circuits_pass(path, check):
    t = select_rows(pd.read_csv(path), check["filter"])
    t = t[t.level == "circuit"]
    ok = (t.ashrae_hourly_CV_le_30.astype(str) == "True") & (t.ashrae_hourly_NMBE_le_10.astype(str) == "True")
    return str(int(ok.sum()))


def all_true(path, check):
    return str((pd.read_csv(path)["detected"].astype(str) == "True").all())


def alerts_per_day_all(path, check):
    return "/".join(str(v) for v in pd.read_csv(path)["alerts_per_day"])


def backlog_counts(path, check):
    """Count the status column of every 'PB-xx' row of the backlog table."""
    counts = {"Covered": 0, "Partly": 0, "Team": 0, "Pending": 0}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and re.fullmatch(r"PB-\d\d", cells[1]):
            counts[cells[3]] = counts.get(cells[3], 0) + 1
    return "/".join(str(counts[k]) for k in ("Covered", "Partly", "Team", "Pending"))


FUNCTIONS = {f.__name__: f for f in (dataset_shape, splits, gain_vs_b2, pairwise_significant, circuit_wins,
                                     d10_choice, blend_weights, ashrae_circuits_pass, all_true,
                                     alerts_per_day_all, backlog_counts)}


# ---------- one check ----------

def run_check(check):
    path = REPO / check["file"]
    if not path.exists():
        return result(check, "FAIL", "file not found")
    tol = tolerance(check["tolerance"])
    if check["type"] == "sha256":
        obtained = sha256(path)
        return result(check, "PASS" if obtained == check["expected"] else "FAIL", obtained[:16] + "...")
    if check["type"] == "value":
        rows = select_rows(read_table(path), check["filter"])
        if len(rows) != 1:
            return result(check, "FAIL", f"{len(rows)} rows match the filter", "the filter must select one row")
        obtained = str(rows[check["column"]].iloc[0])
    else:
        obtained = FUNCTIONS[check["column"]](path, check)
    if ";" in check["expected"]:  # several groups, for example the weights of three horizons
        ok = all(same_values(e, o, tol) for e, o in zip(check["expected"].split(";"), obtained.split(";")))
    else:
        ok = same_values(check["expected"], obtained, tol)
    return result(check, "PASS" if ok else "FAIL", obtained)


def main():
    rows = []
    for _, check in read_plan("L2").iterrows():
        try:
            rows.append(run_check(check))
        except Exception as e:  # a broken check must not stop the audit
            rows.append(result(check, "ERROR", "", f"{type(e).__name__}: {e}"))
        print(rows[-1]["check_id"], rows[-1]["status"], rows[-1]["obtained"])
    save_results(rows, "L2_results.csv")


if __name__ == "__main__":
    main()
