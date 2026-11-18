"""Level 1 - EXISTS: are the files that the documents talk about really in the repository?

Two kinds of checks (column `type` of audit_checks.csv):
  exists     the files in column `file` exist (a * pattern is allowed)
  doc_paths  every path written between `backticks` in a document exists

Run from the repository root:  python Sprint4_Audit_Reproducibility/check_files.py
Writes Sprint4_Audit_Reproducibility/results/L1_results.csv
"""
import re

from common import REPO, read_plan, result, save_results, split_list

# All files of the repository, as text like "Task6_rev0_03-11/RESULTS.md"
ALL_FILES = [p.relative_to(REPO).as_posix() for p in REPO.rglob("*")
             if ".git" not in p.parts and "Sprint4_Audit_Reproducibility" not in p.parts]


def find(path):
    """Files that match `path`. A bare pattern like '*guide*' is searched in every folder."""
    if "/" not in path and "*" in path:
        return [p for p in REPO.rglob(path) if "Sprint4_Audit_Reproducibility" not in p.parts]
    return list(REPO.glob(path))


def check_exists(check):
    paths = split_list(check["file"])
    found = {p: len(find(p)) for p in paths}
    missing = [p for p, n in found.items() if n == 0]
    expected = check["expected"]
    if expected.endswith(" files"):  # for example "11 files"
        n = sum(found.values())
        status = "PASS" if n == int(expected.split()[0]) else "FAIL"
        return result(check, status, f"{n} files")
    if missing:
        return result(check, "FAIL", "not found", "missing: " + "; ".join(missing))
    return result(check, "PASS", "found")


def paths_in_document(text):
    """Text between backticks that looks like a file or a folder."""
    out = []
    for token in re.findall(r"`([^`\n]+)`", text):
        token = token.strip()
        if " " in token and not token.endswith(".zip"):
            continue  # a command or a sentence, not a path
        if token.startswith("."):
            continue  # a folder made when the app runs, like .venv
        if token.endswith("/") or re.search(r"\.[A-Za-z]{2,7}$", token):
            out.append(token)
    return out


def expand(token):
    """'a_{test,validation}.csv' -> ['a_test.csv', 'a_validation.csv']"""
    m = re.search(r"\{([^}]+)\}", token)
    if not m:
        return [token]
    return [token[:m.start()] + part + token[m.end():] for part in m.group(1).split(",")]


def path_exists(token):
    """True if the path exists from the repository root, or as the end of a longer path
    (documents often write a path relative to a folder named just before)."""
    token = token.rstrip("/")
    if token.startswith("_"):  # short form for the end of a file name, like `_META.json`
        return any(f.endswith(token) for f in ALL_FILES)
    if "*" in token:
        return bool(find(token)) or any(re.fullmatch(".*" + re.escape(token).replace(r"\*", ".*"), f) for f in ALL_FILES)
    return (REPO / token).exists() or any(f.endswith("/" + token) for f in ALL_FILES)


def check_doc_paths(check):
    doc = REPO / check["file"]
    if not doc.exists():
        return result(check, "FAIL", "document not found")
    text = doc.read_text(encoding="utf-8")
    for rule in split_list(check["filter"]):  # for example DOC/=Sprint4_Task4_Documentation/
        short, full = rule.split("=")
        text = text.replace("`" + short, "`" + full)
    tokens = sorted({t for token in paths_in_document(text) for t in expand(token)})
    missing = [t for t in tokens if not path_exists(t)]
    status = "PASS" if not missing else "FAIL"
    return result(check, status, f"{len(missing)} missing of {len(tokens)}", "; ".join(missing))


def main():
    rows = []
    for _, check in read_plan("L1").iterrows():
        if check["type"] == "exists":
            rows.append(check_exists(check))
        elif check["type"] == "doc_paths":
            rows.append(check_doc_paths(check))
        print(rows[-1]["check_id"], rows[-1]["status"], rows[-1]["obtained"])
    save_results(rows, "L1_results.csv")


if __name__ == "__main__":
    main()
