"""Reference indexes built on Python's own C-implemented data structures.

These are *not* part of the main comparison. They show what the same ideas
cost when the inner loops run in C instead of Python:

* ``DictReferenceIndex``   -- a hash table (Python's ``dict``).
* ``BisectReferenceIndex`` -- a sorted list searched with the ``bisect`` module.

They do not count operations: ``stats`` stays at zero.
These files contain no planted bugs; do not modify them.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Any

from indexes.base import Index


class DictReferenceIndex(Index):
    name = "ref_dict"
    counts_operations = False

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[Any, list[Any]] = {}

    def insert(self, key: Any, value: Any) -> None:
        values = self._data.get(key)
        if values is None:
            self._data[key] = [value]
        else:
            values.append(value)
        self._size += 1

    def search(self, key: Any) -> list[Any]:
        return self._data.get(key, [])

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        result: list[Any] = []
        for key, values in self._data.items():
            if lo <= key <= hi:
                result.extend(values)
        return result

    def structure_info(self) -> dict[str, Any]:
        return {"distinct_keys": len(self._data)}


class BisectReferenceIndex(Index):
    name = "ref_bisect"
    counts_operations = False

    def __init__(self) -> None:
        super().__init__()
        self._keys: list[Any] = []
        self._values: list[list[Any]] = []

    def insert(self, key: Any, value: Any) -> None:
        pos = bisect_left(self._keys, key)
        if pos < len(self._keys) and self._keys[pos] == key:
            self._values[pos].append(value)
        else:
            self._keys.insert(pos, key)
            self._values.insert(pos, [value])
        self._size += 1

    def search(self, key: Any) -> list[Any]:
        pos = bisect_left(self._keys, key)
        if pos < len(self._keys) and self._keys[pos] == key:
            return self._values[pos]
        return []

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        if lo > hi:
            return []
        start = bisect_left(self._keys, lo)
        stop = bisect_right(self._keys, hi)
        result: list[Any] = []
        for values in self._values[start:stop]:
            result.extend(values)
        return result

    def structure_info(self) -> dict[str, Any]:
        return {"distinct_keys": len(self._keys)}
