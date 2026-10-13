"""Common interface shared by every index in this project.

An *index* maps a key (a song title, a tempo, a track id, ...) to the list of
values stored under that key. In this project the values are row ids: the
position of a track in the Spotify CSV file. Inserting the same key twice
appends to that key's list of row ids.

Every index supports four queries:

    search(key)              exact-match ("point") lookup
    range_search(lo, hi)     all values whose key k satisfies lo <= k <= hi
    prefix_search(prefix)    all values whose (string) key starts with prefix
    len(index)               number of (key, value) pairs stored

Every index also keeps operation counters in ``index.stats`` (see ``Stats``).
Counters are deterministic: the same keys inserted in the same order and the
same queries always produce the same counts, on any machine. Timings are not.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

# The largest Unicode code point. Every string that starts with ``prefix``
# sorts between ``prefix`` and ``prefix + PREFIX_UPPER_BOUND``, so a prefix
# query can be answered as a range query.
PREFIX_UPPER_BOUND = "\U0010ffff"


@dataclass
class Stats:
    """Operation counters. Every field starts at 0; reset with ``index.reset_stats()``.

    comparisons    Keys examined while looking for a key (one per key examined,
                   even if the code compares it with both ``<`` and ``==``).
    nodes_visited  Tree nodes (AVL, B+ tree) or hash buckets touched.
    rotations      AVL rebalancing rotations performed.
    splits         B+ tree node splits performed.
    resizes        Hash table resizes (rebuilds with more buckets) performed.
    """

    comparisons: int = 0
    nodes_visited: int = 0
    rotations: int = 0
    splits: int = 0
    resizes: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class Index(ABC):
    """Abstract base class for all indexes.

    Keys within one index must all be mutually comparable (all strings, or all
    numbers). Values can be anything; this project stores integer row ids.
    """

    #: Short name used in result files, e.g. ``"avl_tree"``.
    name: str = "abstract"

    #: True if the index keeps operation counters in ``stats``. The reference
    #: indexes (built on Python's C-implemented ``dict`` and ``bisect``) do not.
    counts_operations: bool = True

    def __init__(self) -> None:
        self.stats = Stats()
        self._size = 0

    def reset_stats(self) -> None:
        """Set every operation counter back to zero."""
        self.stats = Stats()

    def __len__(self) -> int:
        """Number of (key, value) pairs inserted so far."""
        return self._size

    @abstractmethod
    def insert(self, key: Any, value: Any) -> None:
        """Store ``value`` under ``key``. Duplicate keys are allowed."""

    @abstractmethod
    def search(self, key: Any) -> list[Any]:
        """Return the list of values stored under ``key`` ([] if absent).

        The returned list may be the index's internal list: do not modify it.
        """

    @abstractmethod
    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        """Return all values whose key k satisfies ``lo <= k <= hi``.

        Ordered indexes return values in key order. Unordered indexes (hash
        table, unsorted list, dict reference) return them in no particular order.
        Returns [] if ``lo > hi``.
        """

    def prefix_search(self, prefix: str) -> list[Any]:
        """Return all values whose string key starts with ``prefix``."""
        return self.range_search(prefix, prefix + PREFIX_UPPER_BOUND)

    def params(self) -> str:
        """Constructor options that change behavior, e.g. ``"order=64"``; "" if none."""
        return ""

    def structure_info(self) -> dict[str, Any]:
        """Shape of the data structure (height, number of buckets, ...).

        Computed by walking the structure, so it can be slow on big indexes;
        call it after timing, not during.
        """
        return {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(size={len(self)})"
