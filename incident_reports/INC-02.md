# INC-02: Hash table grows by a fixed 1,024 buckets, so building it gets slower as it grows

## Summary

When the hash table filled up, `_grow` added a fixed 1,024 buckets instead of doubling the table. Every resize moves every key, so building the index cost O(n²) instead of O(n). At n = 114,000 it resized 117 times and took about 27,300 ns per insert, which is about 120 times slower than the `dict` reference and 34 times slower than its own cost at n = 1,000. We fixed it by doubling the number of buckets on each resize.

## Detection

We saw it in E1 (build cost on `track_id`). A hash table insert should cost about the same no matter how big the table is, so build time per key should stay flat. Ours kept going up as n grew. Meanwhile `ref_dict`, which is the same idea written in C, stayed flat at about 170–230 ns per key. The `resizes` counter was also growing in a straight line with n when it should only grow like log2(n).

## Expected vs. observed

If the table doubles each time, starting from 8 buckets and resizing above a 0.75 load factor, the number of resizes should be about log2(d / 6) for d distinct keys. For 89,741 distinct track IDs that's about 14. The total work spent moving keys stays proportional to n, so build time per key should be flat.

What we measured (E1 `build`, luke-mbp16, code_version `65a8adf`, median of 5 reps):

| n | resizes | hash_table ns per key | ref_dict ns per key |
| --- | --- | --- | --- |
| 1,000 | 2 | 793 | 229 |
| 10,000 | 13 | 1,858 | 172 |
| 40,000 | 47 | 6,067 | 194 |
| 114,000 | 117 | 27,307 | 223 |

Resizes went up by about one for every 768 new keys (1,024 buckets times the 0.75 load factor). Since each resize touches every key, total build cost grows like n².

## Evidence

- Figure: `analysis/figures/inc02_hash_table_build.png` (made by the INC-02 cell in `analysis/part_d_incidents.ipynb`).
- 117 resizes at n = 114,000 lines up exactly with 89,741 distinct keys / 768 ≈ 117, which is what fixed +1,024 steps predict.
- Lookups weren't affected. E2 comparisons per lookup for the hash table stayed around 1.3–1.4 for hits and 0.5–0.7 for misses, because the table still kept the load factor under 0.75. Only building was slow.
- Ray's E1 runs (ray-pc, code_version `fead48c`) show the same 117 resizes.
- Rows used: `E1_build`, luke-mbp16, code_version `65a8adf`.

## Root cause

`indexes/hash_table.py`, `HashTableIndex._grow`, line 60 of the original file:

```python
new_capacity = len(self._buckets) + self.GROWTH_STEP   # GROWTH_STEP = 1024 (line 31)
```

`_grow` rebuilds the whole table and moves every key into new buckets. Because the table only gets 1,024 buckets bigger each time, it fills up again after about 768 more keys and has to move everything again. Over n inserts that's about n / 768 resizes, each one O(n), so O(n²) total.

If the table doubles instead, each resize happens half as often as the one before. The total moving work adds up to O(n), so each insert is O(1) on average. Lookups still returned the right values the whole time because every key was still stored in bucket `hash(key) % len(buckets)`. Only the resize schedule was wrong.

## Fix

```diff
     def _grow(self) -> None:
         """Move every entry into a larger list of buckets."""
-        new_capacity = len(self._buckets) + self.GROWTH_STEP
+        new_capacity = len(self._buckets) * 2
```

`GROWTH_STEP` isn't used anymore. We left it in place to keep the change small.

Commit: `6ed4caf`. Diff: `git diff 65a8adf..6ed4caf -- indexes/hash_table.py`.

## Verification

- `make test` passes after the change.
- On synthetic keys in random order (E5 `build`, luke-mbp16, before `65a8adf`, after `ccf1a10`), resizes dropped from 131 to 15 at n = 100,000 and from 14 to 11 at n = 10,000. Resizes now grow like log2(n).
- Same machine and workload (E1 `build`, luke-mbp16, before `65a8adf`, after `ccf1a10`, median of 5 reps):

| n | resizes (before → after) | hash_table ns per key (before → after) | ref_dict ns per key (after) |
| --- | --- | --- | --- |
| 1,000 | 2 → 8 | 793 → 942 | 210 |
| 10,000 | 13 → 11 | 1,858 → 833 | 169 |
| 40,000 | 47 → 13 | 6,067 → 888 | 175 |
| 114,000 | 117 → 14 | 27,307 → 1,077 | 232 |

Build cost per key is now flat (about 800–1,100 ns from n = 1,000 to 114,000), and at n = 114,000 the build is about 25 times faster. The 14 resizes match the expected log2(89,741 / 6) ≈ 14. At n = 1,000 the fixed version is slightly slower (942 vs 793 ns per key) because doubling from 8 buckets takes more small resizes early on (8 vs 2), while the old +1,024 step jumped straight to a big table. That cost disappears as n grows. The hash table is still about 4–5 times slower than `ref_dict`, which is the Python vs. C difference.

## Impact on recommendations

Yes. With the bug, the hash table had fast lookups but one of the slowest builds, which would have knocked it out of F4 (nightly catalog import) and made it a weaker pick for F1 as the catalog grows. After the fix its build cost per key is flat, so it's the obvious pick for F1 (looking up a track by ID). It can still only answer F2 and F3 by scanning every key, because hashing throws away key order.

## Why the tests didn't catch it

The tests only check that queries return the right values, and a table with a bad resize schedule still returns the right values. A counter test would catch it, for example inserting 100,000 distinct keys and checking that `stats.resizes` is at most `log2(100_000) + 1`.
