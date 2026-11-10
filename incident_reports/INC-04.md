# INC-04: B+ tree range and prefix queries read the whole tree instead of following the leaf links

## Summary

The B+ tree's `range_search` went into every child of every node and checked every key in every leaf, so every range or prefix query was a full scan of the tree. On `tempo` (E3), every query looked at all 45,653 distinct keys and all 2,197 nodes, even for a range covering 0.01% of the data. That query took about 3.6 ms while the sorted list took about 3 µs. We fixed it so the search goes down to the leaf where the range starts, then moves right along the leaves' `next` links and stops once it passes the end of the range.

## Detection

We saw it in E3 (range queries on `tempo`). The B+ tree's time barely changed with selectivity: 3.6 ms at 0.0001 and 4.0 ms at 0.25. The AVL tree and sorted list both got slower as the ranges got wider, which is what you'd expect. A flat line meant the B+ tree did the same amount of work no matter how small the range was.

E4 (prefix on `track_name`) showed the same thing. The B+ tree took about 6–8 ms at every prefix length, while the AVL tree went from 1.7 ms down to 0.02 ms as prefixes got longer. The counters confirmed it: the B+ tree's `comparisons` and `nodes_visited` per query were the same in every configuration.

## Expected vs. observed

To answer a range query, a B+ tree should go down one path to the first leaf (one node per level), then read only the leaves the range covers. Comparisons should be about log2(n) plus the number of keys in the range. At selectivity 0.0001 on 45,653 distinct tempos, the range holds about 5 keys, so we expected around 20–25 comparisons and only a few nodes.

What we measured (E3 `range` on `tempo`, n = 114,000, luke-mbp16, code_version `65a8adf`, median of 5 reps):

| selectivity | bplus comparisons per query | bplus nodes per query | bplus ns per query | avl comparisons per query | sorted_list ns per query |
| --- | --- | --- | --- | --- | --- |
| 0.0001 | 45,653 | 2,197 | 3,583,951 | 20.1 | 3,183 |
| 0.001 | 45,653 | 2,197 | 3,558,424 | 61.2 | 13,739 |
| 0.01 | 45,653 | 2,197 | 3,559,228 | 472.0 | 92,172 |
| 0.25 | 45,653 | 2,197 | 4,020,906 | 11,427.4 | 1,849,030 |

In E4 (`prefix` on `track_name`, same code_version), the B+ tree did 72,396 comparisons per query at every prefix length from 1 to 5. That's every distinct track name.

## Evidence

- Figure: `analysis/figures/inc04_bplus_range.png` (made by the INC-04 cell in `analysis/part_d_incidents.ipynb`).
- The B+ tree's comparisons per query equal the total number of distinct keys, and its nodes per query equal the total number of nodes in the tree, in every configuration. The only part that grows with selectivity is the time spent copying matches into the result.
- Point lookups were fine (E2), because `search` uses `_find_leaf`, which only visits one node per level.
- The leaves' `next` links were kept up to date by `_split_leaf`, but no query ever used them. Only `structure_info()` did.
- Ray's runs (ray-pc, code_versions `d66c8cb` and `63162da`) show the exact same counts.
- Rows used: `E3_range` and `E4_prefix`, luke-mbp16, code_version `65a8adf`.

## Root cause

`indexes/bplus_tree.py`, `range_search` (line 173) and `_collect_range` (lines 179–189) of the original file. At every internal node, `_collect_range` runs `for child in node.children` without checking whether that child could hold any keys in `[lo, hi]`. At every leaf it checks every key. So every call walks the entire tree.

The whole point of a B+ tree is that its leaves are linked left to right in sorted order. Once you find the leaf where `lo` would go (the same single path a point lookup takes), you can just follow `next` and stop at the first key bigger than `hi`.

The answers were still correct because scanning everything with a `lo <= key <= hi` check, in tree order, returns exactly the right values in the right order. It just reads the whole index to do it. `prefix_search` is built on top of `range_search` in `base.py`, so prefix queries had the same problem.

## Fix

```diff
     def range_search(self, lo: Any, hi: Any) -> list[Any]:
         result: list[Any] = []
-        if lo <= hi:
-            self._collect_range(self._root, lo, hi, result)
+        if lo > hi:
+            return result
+        leaf: Optional[_Leaf] = self._find_leaf(lo)
+        i = self._bisect_left(leaf.keys, lo)
+        while leaf is not None:
+            while i < len(leaf.keys):
+                self.stats.comparisons += 1
+                if leaf.keys[i] > hi:
+                    return result
+                result.extend(leaf.values[i])
+                i += 1
+            leaf = leaf.next
+            i = 0
+            if leaf is not None:
+                self.stats.nodes_visited += 1
         return result
```

We also removed `_collect_range`, since nothing else used it. The counters still work: `_find_leaf` counts the nodes on the way down, `_bisect_left` counts the comparisons to find the starting spot, and the loop counts one comparison per key it checks and one node per extra leaf it moves to.

Commit: `ccf1a10`. Diff: `git diff 65a8adf..ccf1a10 -- indexes/bplus_tree.py`.

## Verification

- `make test` passes after the change, and results still come back in key order.
- On 100,000 synthetic keys at selectivity 0.001 (100 keys per range), comparisons per query dropped from 100,000 to 118 and nodes visited from 4,854 to 9. At n = 10,000 they dropped from 10,000 to 25 comparisons and from 473 to 4 nodes. The work now depends on how many keys are in the range, the same as for the sorted list and AVL tree.
- Same machine and workload (E3 `range` on `tempo`, luke-mbp16, before `65a8adf`, after `ccf1a10`, median of 5 reps):

| selectivity | bplus comparisons per query (before → after) | bplus nodes per query (before → after) | bplus ns per query (before → after) | sorted_list ns per query (after) |
| --- | --- | --- | --- | --- |
| 0.0001 | 45,653 → 21.9 | 2,197 → 4.2 | 3,583,951 → 4,914 | 3,073 |
| 0.001 | 45,653 → 62.9 | 2,197 → 6.1 | 3,558,424 → 11,617 | 11,631 |
| 0.01 | 45,653 → 473.9 | 2,197 → 25.0 | 3,559,228 → 83,536 | 78,716 |
| 0.25 | 45,653 → 11,429.8 | 2,197 → 529.0 | 4,020,906 → 1,880,925 | 1,876,016 |

The B+ tree's cost now rises with selectivity like the other ordered indexes, and its comparison counts are almost the same as the sorted list's. Narrow ranges got the biggest speedup (about 730 times faster at 0.0001). Wide ranges improved less (about 2 times at 0.25) because most of that time goes to copying the matching rows into the result, which any index has to do.

- Prefix queries (E4 on `track_name`, same commits): comparisons per query dropped from 72,396 to 3,661 at prefix length 1 and to 40.4 at length 5. Time per query dropped from 6,629,667 to 724,521 ns at length 1 and from 6,315,838 to 10,314 ns at length 5.
- E6 (B+ tree order) was rerun on `ccf1a10` too, so its range results now measure tree order instead of this bug.

## Impact on recommendations

Yes, a lot. With the bug, the B+ tree was one of the worst options for F3 (workout-mode tempo ranges) and the worst for F2 (search-as-you-type prefixes), so we never would have recommended it for either. That actually contradicts the interns' own claim that the B+ tree is "the answer for everything." After the fix it's one of the top options for F2 and F3. E6 (B+ tree order) has to be rerun too, because its range results were measuring this bug rather than the effect of tree order.

## Why the tests didn't catch it

The tests check that range and prefix results are correct and in key order, and a full scan gets both right. A counter test would catch it. For example, build a tree with 10,000 keys, run a range that covers about 10 keys, and check that `stats.nodes_visited` is at most the tree's height plus 2 and `stats.comparisons` is at most 50.
