"""Hash table index (the idea behind Python's ``dict``), written in plain Python.

The table is a list of *buckets*. Each bucket is a small Python list of
``(key, values)`` entries. To find a key:

    1. compute ``hash(key)`` -- an integer Python derives from the key,
    2. take it modulo the number of buckets to pick a bucket,
    3. look through that one bucket for the key.

If the buckets stay short, a lookup only examines a handful of entries no
matter how many keys are stored. To keep buckets short, the table adds more
buckets once it holds more than ``MAX_LOAD_FACTOR`` keys per bucket on
average, and moves every key into the new, larger bucket list.

Hashing scatters keys on purpose, so the table has no idea which keys are
"near" each other: a range or prefix query must examine every key.
"""

from __future__ import annotations

from typing import Any

from indexes.base import Index


class HashTableIndex(Index):
    name = "hash_table"

    INITIAL_CAPACITY = 8
    MAX_LOAD_FACTOR = 0.75   # average keys per bucket before the table grows
    GROWTH_STEP = 1024       # buckets added each time the table grows

    def __init__(self, capacity: int = INITIAL_CAPACITY) -> None:
        super().__init__()
        self._buckets: list[list[tuple[Any, list[Any]]]] = [[] for _ in range(capacity)]
        self._num_keys = 0

    def _bucket_for(self, key: Any) -> list[tuple[Any, list[Any]]]:
        self.stats.nodes_visited += 1
        return self._buckets[hash(key) % len(self._buckets)]

    def insert(self, key: Any, value: Any) -> None:
        bucket = self._bucket_for(key)
        comparisons = 0
        for entry_key, values in bucket:
            comparisons += 1
            if entry_key == key:
                values.append(value)
                break
        else:
            bucket.append((key, [value]))
            self._num_keys += 1
        self.stats.comparisons += comparisons
        self._size += 1
        if self._num_keys > len(self._buckets) * self.MAX_LOAD_FACTOR:
            self._grow()

    def _grow(self) -> None:
        """Move every entry into a larger list of buckets."""
        new_capacity = len(self._buckets) + self.GROWTH_STEP
        new_buckets: list[list[tuple[Any, list[Any]]]] = [[] for _ in range(new_capacity)]
        for bucket in self._buckets:
            for entry in bucket:
                new_buckets[hash(entry[0]) % new_capacity].append(entry)
        self._buckets = new_buckets
        self.stats.resizes += 1

    def search(self, key: Any) -> list[Any]:
        bucket = self._bucket_for(key)
        comparisons = 0
        for entry_key, values in bucket:
            comparisons += 1
            if entry_key == key:
                self.stats.comparisons += comparisons
                return values
        self.stats.comparisons += comparisons
        return []

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        # No ordering to exploit: check every key in every bucket.
        result: list[Any] = []
        for bucket in self._buckets:
            for entry_key, values in bucket:
                if lo <= entry_key <= hi:
                    result.extend(values)
        self.stats.comparisons += self._num_keys
        self.stats.nodes_visited += len(self._buckets)
        return result

    def structure_info(self) -> dict[str, Any]:
        longest = max((len(b) for b in self._buckets), default=0)
        return {
            "distinct_keys": self._num_keys,
            "buckets": len(self._buckets),
            "load_factor": self._num_keys / len(self._buckets),
            "longest_bucket": longest,
        }
