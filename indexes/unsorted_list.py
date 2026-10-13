"""Baseline: no index at all.

Every (key, value) pair is appended to one Python list in arrival order, the
way rows land in a table with no index. Inserting is cheap; every query has to
look at every entry (a "full scan").
"""

from __future__ import annotations

from typing import Any

from indexes.base import Index


class UnsortedListIndex(Index):
    name = "unsorted_list"

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[tuple[Any, Any]] = []

    def insert(self, key: Any, value: Any) -> None:
        self._entries.append((key, value))
        self._size += 1

    def search(self, key: Any) -> list[Any]:
        # Duplicates can be anywhere in the list, so scan all of it.
        result = [v for k, v in self._entries if k == key]
        self.stats.comparisons += len(self._entries)
        return result

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        result = [v for k, v in self._entries if lo <= k <= hi]
        self.stats.comparisons += len(self._entries)
        return result

    def structure_info(self) -> dict[str, Any]:
        return {"entries": len(self._entries)}
