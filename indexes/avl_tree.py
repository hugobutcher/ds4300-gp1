"""AVL tree index.

A binary search tree that keeps itself balanced: for every node, the heights
of its left and right subtrees differ by at most 1. When an insert breaks that
rule, the tree fixes it with one or two *rotations* on the way back up from
the insert. A balanced tree with n keys has height about log2(n), so a lookup
examines about log2(n) keys.
"""

from __future__ import annotations

from typing import Any, Optional

from indexes.base import Index


class AVLNode:
    __slots__ = ("key", "values", "left", "right", "height")

    def __init__(self, key: Any, value: Any) -> None:
        self.key = key
        self.values: list[Any] = [value]
        self.left: Optional[AVLNode] = None
        self.right: Optional[AVLNode] = None
        self.height = 1  # a node with no children has height 1


def _height(node: Optional[AVLNode]) -> int:
    return node.height if node is not None else 0


def _update_height(node: AVLNode) -> None:
    node.height = 1 + max(_height(node.left), _height(node.right))


def _balance(node: AVLNode) -> int:
    """Left subtree height minus right subtree height."""
    return _height(node.left) - _height(node.right)


class AVLTreeIndex(Index):
    name = "avl_tree"

    def __init__(self) -> None:
        super().__init__()
        self._root: Optional[AVLNode] = None

    # ----------------------------------------------------------------- rotations
    def _rotate_right(self, y: AVLNode) -> AVLNode:
        """
                y                x
               / \\             / \\
              x   C    ==>     A   y
             / \\                  / \\
            A   B                B   C
        """
        x = y.left
        assert x is not None
        y.left = x.right
        x.right = y
        # x and y swapped places; refresh their stored heights.
        _update_height(x)
        _update_height(y)
        self.stats.rotations += 1
        return x

    def _rotate_left(self, x: AVLNode) -> AVLNode:
        """
              x                    y
             / \\                  / \\
            A   y      ==>       x   C
               / \\              / \\
              B   C            A   B
        """
        y = x.right
        assert y is not None
        x.right = y.left
        y.left = x
        # x and y swapped places; refresh their stored heights.
        _update_height(y)
        _update_height(x)
        self.stats.rotations += 1
        return y

    def _rebalance(self, node: AVLNode) -> AVLNode:
        _update_height(node)
        balance = _balance(node)
        if balance > 1:  # left side too tall
            assert node.left is not None
            if _balance(node.left) < 0:  # left-right case
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:  # right side too tall
            assert node.right is not None
            if _balance(node.right) > 0:  # right-left case
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    # -------------------------------------------------------------------- insert
    def insert(self, key: Any, value: Any) -> None:
        self._root = self._insert(self._root, key, value)
        self._size += 1

    def _insert(self, node: Optional[AVLNode], key: Any, value: Any) -> AVLNode:
        if node is None:
            return AVLNode(key, value)
        self.stats.nodes_visited += 1
        self.stats.comparisons += 1
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.values.append(value)
            return node  # tree shape did not change
        return self._rebalance(node)

    # ------------------------------------------------------------------- queries
    def search(self, key: Any) -> list[Any]:
        node = self._root
        visited = 0
        while node is not None:
            visited += 1
            if key < node.key:
                node = node.left
            elif key > node.key:
                node = node.right
            else:
                break
        self.stats.nodes_visited += visited
        self.stats.comparisons += visited
        return node.values if node is not None else []

    def range_search(self, lo: Any, hi: Any) -> list[Any]:
        result: list[Any] = []
        if lo <= hi:
            self._range(self._root, lo, hi, result)
        return result

    def _range(self, node: Optional[AVLNode], lo: Any, hi: Any, out: list[Any]) -> None:
        """In-order walk that skips subtrees that cannot contain keys in [lo, hi]."""
        if node is None:
            return
        self.stats.nodes_visited += 1
        self.stats.comparisons += 1
        if lo < node.key:
            self._range(node.left, lo, hi, out)
        if lo <= node.key <= hi:
            out.extend(node.values)
        if node.key < hi:
            self._range(node.right, lo, hi, out)

    # ----------------------------------------------------------------- structure
    def structure_info(self) -> dict[str, Any]:
        """Walks the whole tree; the height is measured, not read from nodes."""
        nodes = 0
        height = 0
        stack: list[tuple[AVLNode, int]] = [(self._root, 1)] if self._root else []
        while stack:
            node, depth = stack.pop()
            nodes += 1
            height = max(height, depth)
            if node.left is not None:
                stack.append((node.left, depth + 1))
            if node.right is not None:
                stack.append((node.right, depth + 1))
        return {"distinct_keys": nodes, "height": height}
