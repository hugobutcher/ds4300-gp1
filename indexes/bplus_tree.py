"""B+ tree index.

A B+ tree is a balanced search tree whose nodes hold many keys each, so it is
short and wide instead of tall and thin:

* Internal nodes hold up to ``order - 1`` separator keys and up to ``order``
  children. They only route searches downward.
* Leaves hold the actual keys and their values, in sorted order. Each leaf
  also points to the next leaf to its right, so the leaves form a sorted
  linked list across the bottom of the tree.
* Every leaf is at the same depth. When a node overflows it splits in two and
  pushes a separator key up to its parent; when the root splits, the tree
  grows one level taller.

Databases use B+ trees because one node can be sized to fill one disk page:
a lookup reads one page per level, and a tree of order ~100 holding a
billion keys is only about 5 levels tall. Here everything lives in memory,
but ``stats.nodes_visited`` counts how many "pages" a query would read.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from indexes.base import Index


class _Leaf:
    __slots__ = ("keys", "values", "next")

    def __init__(self) -> None:
        self.keys: list[Any] = []
        self.values: list[list[Any]] = []
        self.next: Optional[_Leaf] = None


class _Internal:
    __slots__ = ("keys", "children")

    def __init__(self) -> None:
        # children[i] holds keys k with keys[i-1] <= k < keys[i]
        self.keys: list[Any] = []
        self.children: list[Union[_Internal, _Leaf]] = []


_Node = Union[_Internal, _Leaf]


class BPlusTreeIndex(Index):
    name = "bplus_tree"

    DEFAULT_ORDER = 32

    def __init__(self, order: int = DEFAULT_ORDER) -> None:
        if order < 3:
            raise ValueError("order must be at least 3")
        super().__init__()
        self.order = order
        self._max_keys = order - 1
        self._root: _Node = _Leaf()

    def params(self) -> str:
        return f"order={self.order}"

    # ------------------------------------------------------- in-node binary search
    def _bisect_left(self, keys: list[Any], key: Any) -> int:
        """Index of the first entry in ``keys`` that is >= ``key``."""
        lo, hi = 0, len(keys)
        comparisons = 0
        while lo < hi:
            mid = (lo + hi) // 2
            comparisons += 1
            if keys[mid] < key:
                lo = mid + 1
            else:
                hi = mid
        self.stats.comparisons += comparisons
        return lo

    def _bisect_right(self, keys: list[Any], key: Any) -> int:
        """Index of the first entry in ``keys`` that is > ``key``."""
        lo, hi = 0, len(keys)
        comparisons = 0
        while lo < hi:
            mid = (lo + hi) // 2
            comparisons += 1
            if key < keys[mid]:
                hi = mid
            else:
                lo = mid + 1
        self.stats.comparisons += comparisons
        return lo

    def _find_leaf(self, key: Any) -> _Leaf:
        """Walk from the root down to the leaf where ``key`` belongs."""
        node = self._root
        visited = 1
        while isinstance(node, _Internal):
            node = node.children[self._bisect_right(node.keys, key)]
            visited += 1
        self.stats.nodes_visited += visited
        return node

    # --------------------------------------------------------------------- insert
    def insert(self, key: Any, value: Any) -> None:
        split = self._insert(self._root, key, value)
        if split is not None:
            separator, right = split
            new_root = _Internal()
            new_root.keys = [separator]
            new_root.children = [self._root, right]
            self._root = new_root
        self._size += 1

    def _insert(self, node: _Node, key: Any, value: Any) -> Optional[tuple[Any, _Node]]:
        """Insert below ``node``. If ``node`` splits, return (separator, new right node)."""
        self.stats.nodes_visited += 1
        if isinstance(node, _Leaf):
            i = self._bisect_left(node.keys, key)
            if i < len(node.keys) and node.keys[i] == key:
                node.values[i].append(value)
                return None
            node.keys.insert(i, key)
            node.values.insert(i, [value])
            if len(node.keys) > self._max_keys:
                return self._split_leaf(node)
            return None

        i = self._bisect_right(node.keys, key)
        split = self._insert(node.children[i], key, value)
        if split is None:
            return None
        separator, right = split
        node.keys.insert(i, separator)
        node.children.insert(i + 1, right)
        if len(node.keys) > self._max_keys:
            return self._split_internal(node)
        return None

    def _split_leaf(self, leaf: _Leaf) -> tuple[Any, _Leaf]:
        mid = len(leaf.keys) // 2
        right = _Leaf()
        right.keys = leaf.keys[mid:]
        right.values = leaf.values[mid:]
        leaf.keys = leaf.keys[:mid]
        leaf.values = leaf.values[:mid]
        right.next = leaf.next
        leaf.next = right
        self.stats.splits += 1
        # The separator is copied up; it also stays in the right leaf.
        return right.keys[0], right

    def _split_internal(self, node: _Internal) -> tuple[Any, _Internal]:
        mid = len(node.keys) // 2
        separator = node.keys[mid]
        right = _Internal()
        right.keys = node.keys[mid + 1:]
        right.children = node.children[mid + 1:]
        node.keys = node.keys[:mid]
        node.children = node.children[:mid + 1]
        self.stats.splits += 1
        # The separator moves up; it is not kept in either half.
        return separator, right

    # -------------------------------------------------------------------- queries
    def search(self, key: Any) -> list[Any]:
        leaf = self._find_leaf(key)
        i = self._bisect_left(leaf.keys, key)
        if i < len(leaf.keys) and leaf.keys[i] == key:
            return leaf.values[i]
        return []

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        result: list[Any] = []
        if lo <= hi:
            self._collect_range(self._root, lo, hi, result)
        return result

    def _collect_range(self, node: _Node, lo: Any, hi: Any, out: list[Any]) -> None:
        """Gather values for keys in [lo, hi] from the subtree under ``node``, in key order."""
        self.stats.nodes_visited += 1
        if isinstance(node, _Leaf):
            for key, values in zip(node.keys, node.values):
                if lo <= key <= hi:
                    out.extend(values)
            self.stats.comparisons += len(node.keys)
            return
        for child in node.children:
            self._collect_range(child, lo, hi, out)

    # ------------------------------------------------------------------ structure
    def structure_info(self) -> dict[str, Any]:
        height = 1
        node = self._root
        while isinstance(node, _Internal):
            node = node.children[0]
            height += 1
        leaves = 0
        keys = 0
        leaf: Optional[_Leaf] = node
        while leaf is not None:
            leaves += 1
            keys += len(leaf.keys)
            leaf = leaf.next
        return {
            "order": self.order,
            "distinct_keys": keys,
            "height": height,
            "leaves": leaves,
            "avg_leaf_fill": keys / (leaves * self._max_keys),
        }
