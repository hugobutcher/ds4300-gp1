# INC-03: AVL rotations update heights in the wrong order, so the tree rotates too much and grows too tall

## Summary

Both AVL rotation methods recalculated the new parent's height before its child's, so the parent's height was based on an old value. Those wrong heights made `_rebalance` misjudge whether the tree was balanced. At n = 100,000 random keys the tree did about 21 times more rotations than it should have, and it ended up 24–25 levels tall, which is more than an AVL tree is ever supposed to be (about 1.44·log2(n) ≈ 24). Swapping the order of the two `_update_height` calls in each rotation fixes it.

## Detection

We saw it in E5 (insert order, synthetic keys). The `rotations` counter for the AVL tree at n = 100,000 was over a million, more than 10 per insert. A working AVL tree does at most one rebalance per insert (one single rotation, or a double rotation that counts as two), so it should stay at or under about one rotation per insert. The `height` from `structure_info()` was also above the maximum height an AVL tree can have. E1 backed this up: the AVL tree had the slowest build of any index (about 13,400 ns per key at n = 114,000).

## Expected vs. observed

An AVL tree's height is at most about 1.44·log2(n + 2). Inserting keys in sorted order should give a nearly perfect tree with height ⌈log2(n + 1)⌉, which is 10, 14, and 17 for n = 1,000, 10,000, and 100,000. Inserts should average at most about one rotation each, and never more than two.

What we measured (E5 `build`, luke-mbp16, code_version `65a8adf`, median of 5 reps):

| n | order | rotations | rotations per insert | height | perfect height | AVL max (1.44·log2 n) |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 | random | 6,638 | 6.6 | 14 | 10 | 14.4 |
| 1,000 | nearly_sorted | 6,176 | 6.2 | 15 | 10 | 14.4 |
| 10,000 | random | 101,983 | 10.2 | 19 | 14 | 19.1 |
| 10,000 | nearly_sorted | 82,091 | 8.2 | 21 | 14 | 19.1 |
| 100,000 | random | 1,465,504 | 14.7 | 24 | 17 | 23.9 |
| 100,000 | nearly_sorted | 1,035,937 | 10.4 | 25 | 17 | 23.9 |
| 100,000 | sorted | 1,139,341 | 11.4 | 21 | 17 | 23.9 |

Rotations per insert keep going up with n instead of staying around 1, and several heights are above the AVL maximum.

## Evidence

- Figure: `analysis/figures/inc03_avl_height.png` (made by the INC-03 cell in `analysis/part_d_incidents.ipynb`), which shows tree height by insert order next to the AVL maximum and the perfect height.
- The height comes from `structure_info()`, which walks the actual tree instead of trusting the stored `height` fields, so it shows the tree's real shape.
- Ray's E5 runs (ray-pc, code_version `549fa40`) show the exact same rotation counts and heights.
- Rows used: `E5_order`, luke-mbp16, code_version `65a8adf`; also `E1_build` at the same code_version for build cost.

## Root cause

`indexes/avl_tree.py`, `_rotate_right` lines 62–63 and `_rotate_left` lines 80–81 of the original file.

In `_rotate_right(y)`, after the pointers are swapped, `x` is the new parent and `y` is now its right child. A node's height is 1 plus its taller child's height, so `y` (the child) has to be updated first. The code did it the other way around:

```python
_update_height(x)   # uses y.height, which is still y's OLD height from before the rotation
_update_height(y)   # y is right now, but x was already calculated from the old value
```

That leaves `x.height` too big. `_rotate_left` has the same mistake mirrored (`y` is the new parent but gets updated before `x`). The wrong heights then feed into `_balance()` at every node on the way back up, which causes rotations that aren't needed and skips some that are.

The results were still correct because a rotation never breaks the binary search tree order, so every key can still be found. Lookups just walk a taller tree, and inserts do a lot more rotation work.

## Fix

Update the child first, then the new parent, in both rotations:

```diff
@@ _rotate_right
         # x and y swapped places; refresh their stored heights.
-        _update_height(x)
         _update_height(y)
+        _update_height(x)
@@ _rotate_left
         # x and y swapped places; refresh their stored heights.
-        _update_height(y)
         _update_height(x)
+        _update_height(y)
```

Commit: `0fb63d9`. Diff: `git diff 65a8adf..0fb63d9 -- indexes/avl_tree.py`.

## Verification

- `make test` passes after the change.
- On synthetic keys (counters and heights are the same on any machine):

| n | rotations, random order (before → after) | height, random (before → after) | height, sorted (before → after) |
| --- | --- | --- | --- |
| 1,000 | 6,283 → 698 | 14 → 12 | 14 → 10 |
| 10,000 | 102,999 → 6,964 | 20 → 16 | 17 → 14 |
| 100,000 | 1,468,521 → 70,101 | 28 → 20 | 21 → 17 |

After the fix, sorted input builds a perfectly balanced tree and random input stays under the AVL maximum.

- Same machine and workload (E5 `build`, luke-mbp16, before `65a8adf`, after `ccf1a10`, median of 5 reps):

| n | order | rotations per insert (before → after) | height (before → after) | perfect height | build ns per key (before → after) |
| --- | --- | --- | --- | --- | --- |
| 1,000 | random | 6.6 → 0.7 | 14 → 12 | 10 | 7,878 → 4,674 |
| 100,000 | random | 14.7 → 0.7 | 24 → 20 | 17 | 16,204 → 7,980 |
| 100,000 | sorted | 11.4 → 1.0 | 21 → 17 | 17 | 11,577 → 8,779 |
| 100,000 | reversed | 11.4 → 1.0 | 21 → 17 | 17 | 11,263 → 8,425 |
| 100,000 | nearly_sorted | 10.4 → 1.2 | 25 → 20 | 17 | 12,290 → 9,415 |

Every height is now under the AVL maximum (23.9 at n = 100,000), and sorted and reversed input give the perfect height at every n. Rotations per insert no longer grow with n. They sit at about 0.7 for random input and 1.0–1.2 for sorted, reversed, and nearly sorted input, which fits the textbook behavior: sorted input triggers about one rotation per insert, and the swapped keys in nearly sorted input add a few double rotations. Build time per key dropped by about 1.3–2 times, with the biggest gain on random input at n = 100,000 (16,204 → 7,980 ns).

## Impact on recommendations

It probably doesn't change the final pick for any feature, but it changes the comparison. With the bug, the AVL tree had the most expensive build of any index, which would have ruled it out for F4 (catalog import) and made it look worse than it is for F3 (tempo ranges). After the fix it builds much faster and lookups do fewer comparisons, so it's a fair runner-up for F1 and F3. Any comparison between the AVL tree and the B+ tree has to use the fixed numbers.

## Why the tests didn't catch it

The tests check that answers are correct, and an unbalanced binary search tree still gives correct answers. A test on the tree's shape would catch it. For example, after inserting n keys, check that `structure_info()["height"]` is at most `1.44 * log2(n + 2)`, that inserting 2^k − 1 sorted keys gives height exactly k, and that `stats.rotations` is at most 2n (one double rotation per insert at most).
