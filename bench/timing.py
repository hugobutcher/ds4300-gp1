"""Measurement helpers (provided; no planted bugs).

All timings use ``time.perf_counter_ns()`` (a high-resolution wall clock)
around a *batch* of operations, with Python's garbage collector paused so a
collection does not land inside one measurement at random. Divide the total
by the number of operations to get time per operation; timing one tiny
operation at a time mostly measures the timer itself.
"""

from __future__ import annotations

import gc
import time
import tracemalloc
from typing import Any, Callable, Iterable, Sequence

from indexes import Index


class _GCPaused:
    def __enter__(self) -> None:
        self._was_enabled = gc.isenabled()
        gc.collect()
        gc.disable()

    def __exit__(self, *exc: object) -> None:
        if self._was_enabled:
            gc.enable()


def time_batch(operation: Callable[[Any], Any], inputs: Iterable[Any]) -> int:
    """Call ``operation(x)`` for every ``x`` in ``inputs``; return total elapsed ns.

    Example::

        ns = time_batch(index.search, queries)
        ns = time_batch(lambda q: index.range_search(*q), ranges)
    """
    inputs = list(inputs)  # materialize outside the timed region
    with _GCPaused():
        start = time.perf_counter_ns()
        for x in inputs:
            operation(x)
        end = time.perf_counter_ns()
    return end - start


def time_build(index: Index, pairs: Sequence[tuple[Any, Any]]) -> int:
    """Insert every ``(key, value)`` pair into ``index``; return total elapsed ns."""
    insert = index.insert
    with _GCPaused():
        start = time.perf_counter_ns()
        for key, value in pairs:
            insert(key, value)
        end = time.perf_counter_ns()
    return end - start


def build_memory_bytes(make_index: Callable[[], Index], pairs: Sequence[tuple[Any, Any]]) -> int:
    """Memory (bytes) allocated by building an index from ``pairs``.

    ``make_index`` is a zero-argument function returning an empty index, e.g.
    ``lambda: make_index("bplus_tree", order=64)``. Key objects already exist
    in ``pairs`` and are shared with the index, so they are not counted: the
    result is the memory the *structure* adds. Tracing slows Python down a lot,
    so never time a build while measuring its memory.
    """
    with _GCPaused():
        tracemalloc.start()
        try:
            before, _ = tracemalloc.get_traced_memory()
            index = make_index()
            for key, value in pairs:
                index.insert(key, value)
            after, _ = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    del index
    return after - before
