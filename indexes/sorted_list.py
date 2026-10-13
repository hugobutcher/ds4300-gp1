"""Sorted list index.

Distinct keys are kept in ascending order in one Python list; the values for
``self._keys[i]`` live in ``self._values[i]``. Keeping the list sorted lets us
find a key with binary search, and makes range queries easy: find where the
range starts, then walk forward until we pass the end.

The price is paid on insert: putting a new key in the middle of a Python list
shifts every key after it one slot to the right.
"""

from __future__ import annotations

from typing import Any

from indexes.base import Index


class SortedListIndex(Index):
    name = "sorted_list"

    def __init__(self) -> None:
        super().__init__()
        self._keys: list[Any] = []
        self._values: list[list[Any]] = []

    def _bisect_left(self, key: Any) -> int:
        """Binary search: index of the first stored key that is >= ``key``.

        Returns ``len(self._keys)`` if every stored key is smaller than ``key``.
        """
        lo, hi = 0, len(self._keys)
        comparisons = 0
        while lo < hi:
            mid = (lo + hi) // 2
            comparisons += 1
            if self._keys[mid] < key:
                lo = mid + 1
            else:
                hi = mid
        self.stats.comparisons += comparisons
        return lo

    def insert(self, key: Any, value: Any) -> None:
        pos = self._bisect_left(key)
        if pos < len(self._keys) and self._keys[pos] == key:
            self._values[pos].append(value)
        else:
            self._keys.insert(pos, key)
            self._values.insert(pos, [value])
        self._size += 1

    def search(self, key: Any) -> list[Any]:
        # The keys are sorted, so we can stop as soon as we have passed the
        # place where ``key`` would be.
        comparisons = 0
        for i, k in enumerate(self._keys):
            comparisons += 1
            if k == key:
                self.stats.comparisons += comparisons
                return self._values[i]
            if k > key:
                break
        self.stats.comparisons += comparisons
        return []

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        result: list[Any] = []
        if lo > hi:
            return result
        i = self._bisect_left(lo)
        comparisons = 0
        while i < len(self._keys):
            comparisons += 1
            if self._keys[i] > hi:
                break
            result.extend(self._values[i])
            i += 1
        self.stats.comparisons += comparisons
        return result

    def structure_info(self) -> dict[str, Any]:
        return {"distinct_keys": len(self._keys)}
