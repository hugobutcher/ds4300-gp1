"""The CORE benchmark suite (provided; do not modify).

Every team member runs this exact workload on their own computer:

    make core MEMBER=alice MACHINE=alice-mbp

Because the workload and random seeds are fixed, the operation counters
(comparisons, nodes_visited, ...) must come out identical on every machine;
only the timings should differ. That makes these rows the controlled
experiment for the hardware comparison in your report. Rows are tagged
``experiment = "CORE"``.

Run it once on the code as handed out, and again after your bug fixes; the
``code_version`` column tells the two apart.
"""

from __future__ import annotations

import random
import time
from typing import Optional, Sequence

from bench.cli import parse, parser, writer_from_args
from bench.results import ResultsWriter
from bench.timing import time_batch, time_build
from indexes import ALL_INDEXES, make_index
from loaders.spotify import key_value_pairs, load_tracks

SEED = 4300
SIZES = (10_000, 114_000)
N_POINT = 1_000
N_RANGE = 200
RANGE_SELECTIVITY = 0.01
PREFIX_LENGTH = 3


def _workloads(tracks):
    rng = random.Random(SEED)
    ids = key_value_pairs(tracks, "track_id")
    id_set = {k for k, _ in ids}
    hits = [k for k, _ in rng.sample(ids, N_POINT)]
    # Reversed ids look like real ids but are (checked) not in the data.
    misses = [k[::-1] for k in hits if k[::-1] not in id_set]

    tempo = key_value_pairs(tracks, "tempo")
    distinct = sorted({k for k, _ in tempo})
    width = round(RANGE_SELECTIVITY * len(distinct))
    starts = [rng.randrange(len(distinct) - width + 1) for _ in range(N_RANGE)]
    ranges = [(distinct[s], distinct[s + width - 1]) for s in starts]

    names = key_value_pairs(tracks, "track_name")
    long_names = [k for k, _ in names if len(k) >= PREFIX_LENGTH]
    prefixes = [rng.choice(long_names)[:PREFIX_LENGTH] for _ in range(N_RANGE)]
    return ids, hits, misses, tempo, ranges, names, prefixes


def run(writer: ResultsWriter, reps: int) -> None:
    tracks = load_tracks()
    ids, hits, misses, tempo, ranges, names, prefixes = _workloads(tracks)

    def record(index, key_column, n_keys, operation, operation_param, n_ops, rep, ns, height=""):
        writer.record(
            index, experiment="CORE", dataset="spotify", key_column=key_column,
            insert_order="file", n_keys=n_keys, operation=operation,
            operation_param=operation_param, n_ops=n_ops, rep=rep, total_ns=ns, height=height,
        )

    for name in ALL_INDEXES:
        started = time.perf_counter()
        for rep in range(reps):
            for n in SIZES:
                index = make_index(name)
                ns = time_build(index, ids[:n])
                record(index, "track_id", n, "build", "", n, rep, ns)

            # `index` now holds every track_id.
            for operation, queries in (("point_hit", hits), ("point_miss", misses)):
                index.reset_stats()
                ns = time_batch(index.search, queries)
                record(index, "track_id", len(ids), operation, "", len(queries), rep, ns)

            index = make_index(name)
            time_build(index, tempo)
            index.reset_stats()
            ns = time_batch(lambda q: index.range_search(*q), ranges)
            record(index, "tempo", len(tempo), "range", RANGE_SELECTIVITY, len(ranges), rep, ns)

            index = make_index(name)
            time_build(index, names)
            index.reset_stats()
            ns = time_batch(index.prefix_search, prefixes)
            record(index, "track_name", len(names), "prefix", PREFIX_LENGTH, len(prefixes), rep, ns)
        print(f"  {name:<14} done in {time.perf_counter() - started:6.1f}s", flush=True)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse(parser(__doc__.splitlines()[0]), argv)
    writer = writer_from_args(args)
    print(f"CORE suite, {args.reps} reps, session {writer.session_id} -> {writer.path}")
    run(writer, args.reps)


if __name__ == "__main__":
    main()
