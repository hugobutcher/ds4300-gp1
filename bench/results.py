"""Write benchmark measurements to ``results/timings.csv`` in the required format.

One row = one timed batch of operations (or one timed build). Every team
member appends to the same file; ``member`` and ``machine_id`` tell rows apart.

    writer = ResultsWriter(member="alice", machine_id="alice-mbp")

    index.reset_stats()                      # count only this batch
    ns = time_batch(index.search, queries)
    writer.record(
        index,                               # fills index_type, index_param, counters
        experiment="E2_point_lookup", dataset="spotify", key_column="track_id",
        insert_order="file", n_keys=len(pairs), operation="point_hit",
        operation_param=1.0, n_ops=len(queries), rep=0, total_ns=ns,
    )
"""

from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bench.machine import REPO_ROOT, machine_info
from indexes import Index, Stats

DEFAULT_RESULTS_PATH = REPO_ROOT / "results" / "timings.csv"

OPERATIONS = ("build", "point_hit", "point_miss", "point_mixed", "range", "prefix")
INSERT_ORDERS = ("file", "random", "sorted", "reversed", "nearly_sorted")
DATASETS = ("spotify", "synthetic")

#: Columns you must supply to ``record()``.
REQUIRED_FIELDS = (
    "experiment",       # your experiment name, e.g. "E3_range_selectivity"
    "dataset",          # "spotify" or "synthetic"
    "key_column",       # Spotify column used as the key, or a label for synthetic keys
    "insert_order",     # one of INSERT_ORDERS
    "n_keys",           # number of (key, value) pairs inserted
    "operation",        # one of OPERATIONS
    "operation_param",  # hit rate, selectivity, or prefix length; "" for builds
    "n_ops",            # operations in this timed batch (n_keys for a build)
    "rep",              # replicate number: 0, 1, 2, ...
    "total_ns",         # elapsed nanoseconds for the whole batch
)

#: Columns you may supply (left blank otherwise).
OPTIONAL_FIELDS = ("height", "memory_bytes", "notes")

#: Filled in from the index passed to ``record()``. Counters are blank for the
#: reference indexes, which do not count operations.
INDEX_FIELDS = ("index_type", "index_param", *Stats().as_dict())

#: Filled in automatically.
AUTO_FIELDS = ("session_id", "timestamp_utc", "member", "machine_id", *machine_info())

COLUMNS = (*AUTO_FIELDS, *REQUIRED_FIELDS, *INDEX_FIELDS, *OPTIONAL_FIELDS)


class ResultsWriter:
    """Appends validated rows to a CSV file, writing the header if the file is new."""

    def __init__(self, member: str, machine_id: str, path: Path | str = DEFAULT_RESULTS_PATH) -> None:
        if not member or not machine_id:
            raise ValueError("member and machine_id are required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._auto = {
            "session_id": uuid.uuid4().hex[:12],
            "member": member,
            "machine_id": machine_id,
            **machine_info(),
        }
        if self.path.exists() and self.path.stat().st_size > 0:
            with self.path.open(newline="") as f:
                header = next(csv.reader(f))
            if tuple(header) != COLUMNS:
                raise ValueError(
                    f"{self.path} has a different header than this version of bench/results.py; "
                    "move it aside before recording new results"
                )

    @property
    def session_id(self) -> str:
        return str(self._auto["session_id"])

    def record(self, index: Index, **fields: Any) -> None:
        """Append one row describing a batch just run against ``index``.

        The row's counters are ``index.stats`` as they are right now, so call
        ``index.reset_stats()`` before the batch you are measuring.
        """
        missing = [f for f in REQUIRED_FIELDS if f not in fields]
        unknown = [f for f in fields if f not in REQUIRED_FIELDS and f not in OPTIONAL_FIELDS]
        if missing or unknown:
            raise ValueError(f"missing fields {missing}; unknown fields {unknown}")
        if fields["operation"] not in OPERATIONS:
            raise ValueError(f"operation must be one of {OPERATIONS}")
        if fields["insert_order"] not in INSERT_ORDERS:
            raise ValueError(f"insert_order must be one of {INSERT_ORDERS}")
        if fields["dataset"] not in DATASETS:
            raise ValueError(f"dataset must be one of {DATASETS}")

        counters = index.stats.as_dict() if index.counts_operations else dict.fromkeys(index.stats.as_dict(), "")
        row = {
            **self._auto,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **dict.fromkeys(OPTIONAL_FIELDS, ""),
            **fields,
            "index_type": index.name,
            "index_param": index.params(),
            **counters,
        }
        new_file = not self.path.exists() or self.path.stat().st_size == 0
        with self.path.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            if new_file:
                writer.writeheader()
            writer.writerow({c: ("" if row[c] is None else row[c]) for c in COLUMNS})
