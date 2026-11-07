"""Your experiments.  *** YOU EXTEND THIS FILE. ***

Run one experiment, or all of them:

    make experiments MEMBER=alice MACHINE=alice-mbp                 # all
    make experiments MEMBER=alice MACHINE=alice-mbp ONLY=example     # one

``example_point_lookups`` below is the summer 2024 interns' one finished experiment, and it works. Copy its
pattern for each experiment the README asks for (E1-E6), and register each
new function in ``EXPERIMENTS`` at the bottom of this file.

The pattern, for every configuration you measure:
    1. prepare keys and queries OUTSIDE the timed region,
    2. build a fresh index (time it with ``time_build`` if build cost matters),
    3. ``index.reset_stats()``, then time one batch with ``time_batch``,
    4. ``writer.record(index, ...)`` one row,
    5. repeat for ``reps`` replicates.
"""

from __future__ import annotations

import random
import time
from typing import Callable, Optional, Sequence

from bench.cli import parse, parser, writer_from_args
from bench.results import ResultsWriter
from bench.timing import build_memory_bytes, time_batch, time_build
from indexes import ALL_INDEXES, make_index
from loaders.spotify import key_value_pairs, load_tracks
from datagen.synthetic import point_queries, range_queries, prefix_queries

SEED = 4300


def example_point_lookups(writer: ResultsWriter, tracks: list[dict], reps: int) -> None:
    """Build cost and point-lookup (hit) cost on track_id as the index grows."""
    pairs = key_value_pairs(tracks, "track_id")  # file order
    rng = random.Random(SEED)

    for n in (1_000, 10_000, len(pairs)):
        subset = pairs[:n]
        queries = [key for key, _ in rng.sample(subset, 500)]  # every query is a hit

        for name in ALL_INDEXES:
            # Memory once per configuration (tracing is slow; never time it).
            memory = build_memory_bytes(lambda: make_index(name), subset)

            for rep in range(reps):
                common = dict(
                    experiment="example", dataset="spotify", key_column="track_id",
                    insert_order="file", n_keys=n, rep=rep,
                )

                index = make_index(name)
                ns = time_build(index, subset)
                writer.record(
                    index, **common, operation="build", operation_param="",
                    n_ops=n, total_ns=ns, memory_bytes=memory,
                )

                index.reset_stats()
                ns = time_batch(index.search, queries)
                writer.record(
                    index, **common, operation="point_hit", operation_param=1.0,
                    n_ops=len(queries), total_ns=ns,
                    height=index.structure_info().get("height", ""),
                )
            print(f"  n={n:>7,}  {name:<14} done", flush=True)


def e1_build(writer, tracks, reps):
    """E1: How does build cost grow with n? How much memory does each index use?

    Minimum design: track_id in file order; at least 6 sizes from 1,000 to 114,000;
    record memory_bytes
    """
    # Get every (track_id, row number) pair, in the same order as the file
    pairs = key_value_pairs(tracks, "track_id")

    # Try each dataset size, from small to all 114,000 songs
    for n in [1000, 2000, 5000, 10000, 20000, 40000, 80000, 114000]:
        # Use only the first n songs
        data = pairs[:n]

        # Test each of the 7 indexes
        for name in ALL_INDEXES:
            # Measure memory once, on its own, because measuring memory slows things down
            memory = build_memory_bytes(lambda: make_index(name), data)

            # Repeat the timing several times to see how much it varies
            for rep in range(reps):
                # Start with a brand new, empty index every time
                index = make_index(name)

                # Load all n songs into the index and time how long it takes
                ns = time_build(index, data)

                # Save one row to results/timings.csv describing this measurement
                writer.record(
                    index, experiment="E1_build", dataset="spotify",
                    key_column="track_id", insert_order="file",
                    n_keys=n, operation="build", operation_param="",
                    n_ops=n, rep=rep, total_ns=ns, memory_bytes=memory,
                )


def e2_point(writer, tracks, reps):
    """E2: How does point-lookup cost grow with n, for hits and for misses?

    Minimum design: track_id; the same sizes as E1; point_queries with hit rates 1.0 and 0.0
    """
    # Get every (track_id, row number) pair, in the same order as the file
    pairs = key_value_pairs(tracks, "track_id")

    # Same sizes as E1
    for n in [1000, 2000, 5000, 10000, 20000, 40000, 80000, 114000]:
        # Use only the first n songs
        data = pairs[:n]

        # Pull out just the track IDs
        keys = [key for key, value in data]

        # 500 that find a song (hits) and 500 that find nothing (misses)
        # 500 matches the interns' example
        hits = point_queries(keys, 500, 1.0, seed=SEED)
        misses = point_queries(keys, 500, 0.0, seed=SEED)

        # Test each of the 7 indexes
        for name in ALL_INDEXES:
            # Build the index once, not timing build
            index = make_index(name)
            for key, value in data:
                index.insert(key, value)

            # Repeat the timing to see variation
            for rep in range(reps):
                # Time the hits
                index.reset_stats()
                ns = time_batch(index.search, hits)
                writer.record(
                    index, experiment="E2_point", dataset="spotify",
                    key_column="track_id", insert_order="file",
                    n_keys=n, operation="point_hit", operation_param=1.0,
                    n_ops=len(hits), rep=rep, total_ns=ns,
                )

                # Time the misses
                index.reset_stats()
                ns = time_batch(index.search, misses)
                writer.record(
                    index, experiment="E2_point", dataset="spotify",
                    key_column="track_id", insert_order="file",
                    n_keys=n, operation="point_miss", operation_param=0.0,
                    n_ops=len(misses), rep=rep, total_ns=ns,
                )


def e3_range(writer, tracks, reps):
    """E3: How does range-query cost depend on how much of the data the range covers?

    Minimum design: tempo, all 114k rows; selectivities 0.0001, 0.001, 0.01, 0.05, 0.1, 0.25
    """
    # Get every (tempo, row number) pair, in the same order as the file
    pairs = key_value_pairs(tracks, "tempo")

    # Pull out the tempos
    keys = [key for key, value in pairs]

    for name in ALL_INDEXES:
        # Build the index once, not timing build
        index = make_index(name)
        for key, value in pairs:
            index.insert(key, value)

        # Try each range width
        for selectivity in [0.0001, 0.001, 0.01, 0.05, 0.1, 0.25]:
            # 200 ranges of this width, same batch size as CORE
            ranges = range_queries(keys, 200, selectivity, seed=SEED)

            # Repeat the timing to see variation
            for rep in range(reps):
                # Time the ranges
                index.reset_stats()
                ns = time_batch(lambda r: index.range_search(r[0], r[1]), ranges)
                writer.record(
                    index, experiment="E3_range", dataset="spotify",
                    key_column="tempo", insert_order="file",
                    n_keys=len(pairs), operation="range", operation_param=selectivity,
                    n_ops=len(ranges), rep=rep, total_ns=ns,
                )


def e4_prefix(writer, tracks, reps):
    """E4: How does prefix-search cost depend on prefix length?

    Minimum design: track_name; prefix lengths 1 through 5
    """
    # Get every (track_name, row number) pair, in the same order as the file
    pairs = key_value_pairs(tracks, "track_name")

    # Pull the track names
    keys = [key for key, value in pairs]

    # Test each of the 7 indexes
    for name in ALL_INDEXES:
        # Build the index once, not timing build
        index = make_index(name)
        for key, value in pairs:
            index.insert(key, value)

        # Try each prefix length.
        # Essentially like typing 1 to 5 letters
        for length in [1, 2, 3, 4, 5]:
            # 200 prefixes of this length, same batch size as CORE
            prefixes = prefix_queries(keys, 200, length, seed=SEED)

            # Repeat the timing to see variation
            for rep in range(reps):
                # Time the prefix searches
                index.reset_stats()
                ns = time_batch(index.prefix_search, prefixes)
                writer.record(
                    index, experiment="E4_prefix", dataset="spotify",
                    key_column="track_name", insert_order="file",
                    n_keys=len(pairs), operation="prefix", operation_param=length,
                    n_ops=len(prefixes), rep=rep, total_ns=ns,
                )

# Register experiments here: name -> function(writer, tracks, reps).
EXPERIMENTS: dict[str, Callable[[ResultsWriter, list[dict], int], None]] = {
    "example": example_point_lookups,
    "E1_build": e1_build,  # E1: build cost and memory as n grows
    "E2_point": e2_point,  # E2: hit and miss cost as n grows
    "E3_range": e3_range,  # E3: range cost as the range widens
    "E4_prefix": e4_prefix,  # E4: prefix cost as it gets longer
}


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = parser("Run your experiments.")
    p.add_argument("--only", choices=sorted(EXPERIMENTS), help="run just this experiment")
    args = parse(p, argv)
    writer = writer_from_args(args)
    tracks = load_tracks()
    names = [args.only] if args.only else list(EXPERIMENTS)
    for name in names:
        print(f"{name}: {args.reps} reps, session {writer.session_id}", flush=True)
        started = time.perf_counter()
        EXPERIMENTS[name](writer, tracks, args.reps)
        print(f"{name}: finished in {time.perf_counter() - started:.1f}s", flush=True)


if __name__ == "__main__":
    main()
