# INC-01: Sorted list search scans every key instead of using binary search

## Summary

The sorted list's `search` method checked keys one at a time from the front of the list, so each lookup cost O(n) instead of O(log n). At n = 114,000 a lookup took about 3.4 ms, around 3,000 times slower than the `bisect` reference and about as slow as having no index at all. We fixed it by having `search` use the binary search (`_bisect_left`) that the class already had.

## Detection

We saw it in E2 (point lookups on `track_id`). On the log-log plot, the sorted list's line ran right alongside the unsorted list instead of near `ref_bisect`. Those two should behave almost the same, since they're the same idea, but they were about 3,000 times apart. That gap is what made us look closer.

## Expected vs. observed

A binary search over d distinct keys should take about log2(d) comparisons. At n = 114,000 there are 89,741 distinct track IDs, so we expected about 16.5 comparisons per lookup.

What we measured (E2 `point_hit`, luke-mbp16, code_version `65a8adf`, median of 5 reps):

| n | comparisons per lookup | log2(n) | sorted_list ns per lookup | ref_bisect ns per lookup |
| --- | --- | --- | --- | --- |
| 1,000 | 509.9 | 10.0 | 24,125 | 389 |
| 10,000 | 4,780.3 | 13.3 | 260,299 | 436 |
| 114,000 | 46,118.9 | 16.8 | 3,448,541 | 1,153 |

Comparisons per lookup came out to about half the number of distinct keys. That's exactly what you'd get from scanning from the front and stopping once you pass the key.

## Evidence

- Figure: `analysis/figures/inc01_sorted_list_point.png` (made by the INC-01 cell in `analysis/part_d_incidents.ipynb`).
- From n = 1,000 to 114,000, comparisons per lookup grew about 90x. With binary search they should only grow about 1.7x.
- Build cost was fine. E1 build times for `sorted_list` stayed close to `ref_bisect` because `insert` already used `_bisect_left`. Only `search` was slow.
- Ray's runs (ray-pc, code_version `4f595b6`) show the exact same comparison counts, which makes sense since the counters don't depend on the machine.
- Rows used: `E2_point`, luke-mbp16, code_version `65a8adf` (interns' original index code).

## Root cause

`indexes/sorted_list.py`, `SortedListIndex.search`, lines 53–65 of the original file. The method loops through `self._keys` from the start and stops early only once it passes where the key would be. The comment says this lets it "stop as soon as we have passed the place where key would be," which is true, but on average it still looks at half the list.

The class already has `_bisect_left` (lines 27–42), which finds a key's position in O(log n). `insert` and `range_search` both use it, but `search` never did. The answers were still right because scanning a sorted list finds the same key. It just checks far more keys to get there.

## Fix

We replaced the scan with the existing binary search:

```diff
     def search(self, key: Any) -> list[Any]:
-        # The keys are sorted, so we can stop as soon as we have passed the
-        # place where ``key`` would be.
-        comparisons = 0
-        for i, k in enumerate(self._keys):
-            comparisons += 1
-            if k == key:
-                self.stats.comparisons += comparisons
-                return self._values[i]
-            if k > key:
-                break
-        self.stats.comparisons += comparisons
+        pos = self._bisect_left(key)
+        if pos < len(self._keys) and self._keys[pos] == key:
+            return self._values[pos]
         return []
```

`_bisect_left` already adds its comparisons to `stats`, so the counter is still accurate.

Commit: `8a18fc0`. Diff: `git diff 65a8adf..8a18fc0 -- indexes/sorted_list.py`.

## Verification

- `make test` passes after the change.
- On synthetic keys (E5 `point_hit`, 500 hit lookups, luke-mbp16, before `65a8adf`, after `ccf1a10`), comparisons per lookup dropped from 509.0 to 10.0 at n = 1,000, from 4,879.7 to 13.4 at n = 10,000, and from 49,516.0 to 16.7 at n = 100,000. The counts are identical for all four arrival orders. That's right in line with log2(n). Counters are the same on any machine, so these hold everywhere.
- Same machine and workload (E2 `point_hit`, luke-mbp16, before `65a8adf`, after `ccf1a10`, median of 5 reps):

| n | comparisons per lookup (before → after) | sorted_list ns per lookup (before → after) | ref_bisect ns per lookup (after) |
| --- | --- | --- | --- |
| 1,000 | 509.9 → 10.0 | 24,125 → 1,074 | 328 |
| 10,000 | 4,780.3 → 13.3 | 260,299 → 1,597 | 447 |
| 114,000 | 46,118.9 → 16.5 | 3,448,541 → 3,783 | 1,518 |

At n = 114,000 a lookup is now about 900 times faster, and 16.5 comparisons per lookup matches log2(89,741) ≈ 16.5. The fixed sorted list is still about 2.5–3.6 times slower than `ref_bisect`. That gap is the cost of running the same binary search in Python instead of C, not a bug.

## Impact on recommendations

Yes, it changes things. With the bug, the sorted list looked no better than having no index for F1 (track page), so we would have ruled it out. After the fix it's a real O(log n) option for F1. Its range and prefix queries were already fast, so it's now a strong choice for F2 and F3 too, as long as the catalog doesn't need lots of inserts.

## Why the tests didn't catch it

The tests only check that `search` returns the right answer, and a full scan still does. A test on the counters would catch it. For example, build a sorted list with 10,000 keys, run 100 lookups, and check that `stats.comparisons / 100` is at most `2 * log2(10_000)`.
