"""Check that a submission has everything graders need (run with `make check`).

Prints PASS / WARN / FAIL lines and exits non-zero if anything FAILs. It checks
that deliverables are present and well formed, not that they are good.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from bench.core_suite import SIZES  # noqa: E402
from bench.results import COLUMNS, DEFAULT_RESULTS_PATH  # noqa: E402
from indexes import ALL_INDEXES, MAIN_INDEXES, Stats  # noqa: E402

MACHINE_COLUMNS = [
    "machine_id", "member", "computer_model", "cpu_model", "cpu_cores",
    "ram_gb", "os", "docker_cpus", "docker_memory_gb", "power",
]
REQUIRED_EXPERIMENTS = ("E1", "E2", "E3", "E4", "E5", "E6")
MIN_REPS = 5
CORE_OPERATIONS = ("build", "point_hit", "point_miss", "range", "prefix")
COUNTERS = tuple(Stats().as_dict())

failures = 0


def report(level: str, message: str) -> None:
    global failures
    if level == "FAIL":
        failures += 1
    print(f"[{level}] {message}")


def check_machines() -> dict[str, dict[str, str]]:
    path = REPO / "machines.csv"
    if not path.exists():
        report("FAIL", "machines.csv is missing")
        return {}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != MACHINE_COLUMNS:
            report("FAIL", f"machines.csv header must be: {','.join(MACHINE_COLUMNS)}")
            return {}
        rows = list(reader)
    machines: dict[str, dict[str, str]] = {}
    for i, row in enumerate(rows, start=2):
        blank = [c for c in MACHINE_COLUMNS if not (row.get(c) or "").strip()]
        if blank:
            report("FAIL", f"machines.csv line {i}: blank {blank}")
        if row["machine_id"] in machines:
            report("FAIL", f"machines.csv line {i}: duplicate machine_id {row['machine_id']!r}")
        machines[row["machine_id"]] = row
    if machines:
        report("PASS", f"machines.csv lists {len(machines)} machine(s)")
    else:
        report("FAIL", "machines.csv has no rows")
    return machines


def load_results() -> list[dict[str, str]]:
    path = DEFAULT_RESULTS_PATH
    if not path.exists():
        report("FAIL", f"{path.relative_to(REPO)} is missing")
        return []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            report("FAIL", "results/timings.csv header does not match bench/results.py (was it edited by hand?)")
            return []
        rows = list(reader)
    report("PASS", f"results/timings.csv has {len(rows):,} rows")
    return rows


def check_results(rows: list[dict[str, str]], machines: dict[str, dict[str, str]]) -> None:
    unknown = sorted({r["machine_id"] for r in rows} - set(machines))
    if unknown:
        report("FAIL", f"machine_id(s) in results but not in machines.csv: {unknown}")
    if any(r["in_docker"] != "True" for r in rows):
        report("FAIL", "some rows were not measured inside the Docker container (in_docker != True)")
    dirty = {r["code_version"] for r in rows if r["code_version"].endswith("-dirty") or r["code_version"] == "unknown"}
    if dirty:
        report("WARN", f"rows measured on uncommitted code: {sorted(dirty)}; commit before measuring")

    # CORE: every machine, every index and operation, enough reps, under some code_version.
    core: dict[tuple, set] = defaultdict(set)
    for r in rows:
        if r["experiment"] == "CORE":
            size = r["n_keys"] if r["operation"] == "build" else "*"
            core[(r["machine_id"], r["code_version"], r["index_type"], r["operation"], size)].add(r["rep"])
    for machine_id in machines:
        complete_versions = set()
        for version in {k[1] for k in core if k[0] == machine_id}:
            needed = [
                (machine_id, version, idx, op, size)
                for idx in ALL_INDEXES for op in CORE_OPERATIONS
                for size in ([str(n) for n in SIZES] if op == "build" else ["*"])
            ]
            if all(len(core.get(k, ())) >= MIN_REPS for k in needed):
                complete_versions.add(version)
        if len(complete_versions) >= 2:
            report("PASS", f"CORE complete on {machine_id} for code versions {sorted(complete_versions)}")
        elif complete_versions:
            report("FAIL", f"CORE complete on {machine_id} for only one code version {sorted(complete_versions)}; "
                           "run it before and after your fixes")
        else:
            report("FAIL", f"no complete CORE run (all indexes x operations x {MIN_REPS} reps) on {machine_id}")

    # Counters must agree across machines for the same code version.
    counters: dict[tuple, set] = defaultdict(set)
    for r in rows:
        if r["experiment"] == "CORE" and r["comparisons"] != "":
            key = (r["code_version"], r["index_type"], r["operation"], r["n_keys"])
            counters[key].add(tuple(r[c] for c in COUNTERS))
    mismatched = sorted({k[0] for k, v in counters.items() if len(v) > 1})
    if mismatched:
        report("WARN", f"CORE counters differ between runs of the same code version(s) {mismatched}; "
                       "explain this in Part E")

    # Required experiments.
    for exp_id in REQUIRED_EXPERIMENTS:
        mine = [r for r in rows if re.match(rf"{exp_id}(_|$)", r["experiment"])]
        if not mine:
            report("FAIL", f"no rows for experiment {exp_id} (experiment names must start with '{exp_id}_')")
            continue
        reps: dict[tuple, set] = defaultdict(set)
        for r in mine:
            config = tuple(r[c] for c in (
                "code_version", "machine_id", "experiment", "key_column", "insert_order",
                "index_type", "index_param", "n_keys", "operation", "operation_param"))
            reps[config].add(r["rep"])
        thin = sum(1 for v in reps.values() if len(v) < MIN_REPS)
        indexes = {r["index_type"] for r in mine}
        level = "WARN" if thin else "PASS"
        report(level, f"{exp_id}: {len(mine):,} rows, {len(reps)} configurations"
                      + (f", {thin} with fewer than {MIN_REPS} reps" if thin else ""))
        if exp_id != "E6" and not set(MAIN_INDEXES) <= indexes:
            report("WARN", f"{exp_id}: missing indexes {sorted(set(MAIN_INDEXES) - indexes)}")


def check_incidents() -> None:
    folder = REPO / "incident_reports"
    template = (folder / "TEMPLATE.md").read_text()
    headings = re.findall(r"^## .+$", template, flags=re.M)
    reports = sorted(p for p in folder.glob("INC-*.md"))
    if not reports:
        report("FAIL", "no incident reports (incident_reports/INC-01.md, ...)")
    for path in reports:
        text = path.read_text()
        missing = [h for h in headings if h not in text]
        if missing:
            report("FAIL", f"{path.name}: missing sections {missing}")
        elif "<one-line title" in text:
            report("FAIL", f"{path.name}: title not filled in")
        else:
            report("PASS", f"{path.name}: all sections present")


def check_analysis() -> None:
    notebooks = [p for p in (REPO / "analysis").glob("*.ipynb") if p.name != "starter.ipynb"]
    if notebooks:
        report("PASS", f"analysis notebooks: {[p.name for p in notebooks]}")
    else:
        report("FAIL", "no analysis notebook in analysis/ (other than starter.ipynb)")


def main() -> int:
    machines = check_machines()
    rows = load_results()
    if rows:
        check_results(rows, machines)
    check_incidents()
    check_analysis()
    print("\nAll checks passed." if not failures else f"\n{failures} check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
