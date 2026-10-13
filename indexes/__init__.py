"""Index implementations for Practical 1.

Use ``make_index(name, **options)`` to build an index by name, e.g.
``make_index("bplus_tree", order=64)``.
"""

from __future__ import annotations

from typing import Any

from indexes.avl_tree import AVLTreeIndex
from indexes.base import Index, Stats
from indexes.bplus_tree import BPlusTreeIndex
from indexes.hash_table import HashTableIndex
from indexes.reference import BisectReferenceIndex, DictReferenceIndex
from indexes.sorted_list import SortedListIndex
from indexes.unsorted_list import UnsortedListIndex

#: The five indexes you are comparing.
MAIN_INDEXES: dict[str, type[Index]] = {
    UnsortedListIndex.name: UnsortedListIndex,
    SortedListIndex.name: SortedListIndex,
    HashTableIndex.name: HashTableIndex,
    AVLTreeIndex.name: AVLTreeIndex,
    BPlusTreeIndex.name: BPlusTreeIndex,
}

#: C-backed reference points (see indexes/reference.py).
REFERENCE_INDEXES: dict[str, type[Index]] = {
    DictReferenceIndex.name: DictReferenceIndex,
    BisectReferenceIndex.name: BisectReferenceIndex,
}

ALL_INDEXES: dict[str, type[Index]] = {**MAIN_INDEXES, **REFERENCE_INDEXES}


def make_index(name: str, **options: Any) -> Index:
    """Create an empty index by name. ``options`` go to the constructor."""
    try:
        cls = ALL_INDEXES[name]
    except KeyError:
        raise ValueError(f"unknown index {name!r}; choose from {sorted(ALL_INDEXES)}") from None
    return cls(**options)


__all__ = [
    "ALL_INDEXES",
    "AVLTreeIndex",
    "BPlusTreeIndex",
    "BisectReferenceIndex",
    "DictReferenceIndex",
    "HashTableIndex",
    "Index",
    "MAIN_INDEXES",
    "REFERENCE_INDEXES",
    "SortedListIndex",
    "Stats",
    "UnsortedListIndex",
    "make_index",
]
