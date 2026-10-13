"""Correctness tests for every index.

These all pass on the code as handed out. Passing them says the indexes
return the right answers; it says nothing about how fast they are.
"""

from __future__ import annotations

import random
from collections import defaultdict

import pytest

from indexes import ALL_INDEXES, Index, make_index

ORDERED = {"sorted_list", "avl_tree", "bplus_tree", "ref_bisect"}

# Every index, plus small B+ tree orders so that tiny inputs still cause splits.
CASES = [(name, {}) for name in ALL_INDEXES] + [
    ("bplus_tree", {"order": 3}),
    ("bplus_tree", {"order": 4}),
]
IDS = [name + "".join(f"-{k}{v}" for k, v in opts.items()) for name, opts in CASES]


@pytest.fixture(params=CASES, ids=IDS)
def new_index(request):
    name, options = request.param
    return lambda: make_index(name, **options)


def build(make, pairs) -> Index:
    index = make()
    for key, value in pairs:
        index.insert(key, value)
    return index


def expected_map(pairs):
    expected = defaultdict(list)
    for key, value in pairs:
        expected[key].append(value)
    return expected


def test_empty_index(new_index):
    index = new_index()
    assert len(index) == 0
    assert index.search("anything") == []
    assert index.range_search("a", "z") == []
    assert index.prefix_search("a") == []


def test_duplicate_keys_keep_insertion_order(new_index):
    index = build(new_index, [("b", 1), ("a", 2), ("b", 3), ("c", 4), ("b", 5)])
    assert index.search("b") == [1, 3, 5]
    assert index.search("a") == [2]
    assert len(index) == 5


@pytest.mark.parametrize("missing", ["", "0", "aa", "bb", "zzz"])
def test_missing_keys(new_index, missing):
    index = build(new_index, [("a", 1), ("b", 2), ("c", 3)])
    assert index.search(missing) == []


def test_range_bounds_are_inclusive(new_index):
    index = build(new_index, [(k, k * 10) for k in [5, 1, 9, 3, 7]])
    assert sorted(index.range_search(3, 7)) == [30, 50, 70]
    assert sorted(index.range_search(4, 6)) == [50]
    assert index.range_search(6, 6) == []
    assert sorted(index.range_search(-100, 100)) == [10, 30, 50, 70, 90]
    assert index.range_search(7, 3) == []


def test_ordered_indexes_return_ranges_in_key_order(new_index):
    index = new_index()
    if index.name not in ORDERED:
        pytest.skip("unordered index")
    pairs = [(k, k) for k in random.Random(1).sample(range(1000), 300)]
    for key, value in pairs:
        index.insert(key, value)
    assert index.range_search(100, 600) == sorted(k for k, _ in pairs if 100 <= k <= 600)


def test_prefix_search(new_index):
    titles = ["love story", "love", "lovely", "lover", "loud", "lo", "glove", "beyoncé", "bey"]
    index = build(new_index, [(t, i) for i, t in enumerate(titles)])
    assert sorted(index.prefix_search("love")) == [0, 1, 2, 3]
    assert sorted(index.prefix_search("lo")) == [0, 1, 2, 3, 4, 5]
    assert sorted(index.prefix_search("bey")) == [7, 8]
    assert index.prefix_search("x") == []
    assert sorted(index.prefix_search("")) == list(range(len(titles)))


def test_float_keys(new_index):
    tempos = [120.0, 87.917, 120.0, 140.5, 60.25]
    index = build(new_index, [(t, i) for i, t in enumerate(tempos)])
    assert index.search(120.0) == [0, 2]
    assert sorted(index.range_search(87.917, 120.0)) == [0, 1, 2]


@pytest.mark.parametrize("order", ["random", "sorted", "reversed"])
def test_matches_a_dict_on_random_workload(new_index, order):
    rng = random.Random(4300)
    pairs = [(rng.randrange(2000), i) for i in range(5000)]
    if order == "sorted":
        pairs.sort()
    elif order == "reversed":
        pairs.sort(reverse=True)
    index = build(new_index, pairs)
    expected = expected_map(pairs)

    assert len(index) == len(pairs)
    for key in range(-1, 2001):
        assert index.search(key) == expected.get(key, [])
    for _ in range(200):
        lo, hi = sorted(rng.randrange(-10, 2010) for _ in range(2))
        want = sorted(v for k, vs in expected.items() if lo <= k <= hi for v in vs)
        assert sorted(index.range_search(lo, hi)) == want


def test_string_keys_match_a_dict(new_index):
    rng = random.Random(7)
    words = ["".join(rng.choices("abcde", k=rng.randint(1, 4))) for _ in range(3000)]
    pairs = [(w, i) for i, w in enumerate(words)]
    index = build(new_index, pairs)
    expected = expected_map(pairs)
    for word in set(words) | {"zzzz", "", "f"}:
        assert index.search(word) == expected.get(word, [])
    for prefix in ["a", "ab", "abc", "e", "ed", "f"]:
        want = sorted(v for k, vs in expected.items() if k.startswith(prefix) for v in vs)
        assert sorted(index.prefix_search(prefix)) == want


def test_stats_count_and_reset(new_index):
    index = build(new_index, [(k, k) for k in range(100)])
    index.reset_stats()
    assert all(v == 0 for v in index.stats.as_dict().values())
    index.search(42)
    if index.counts_operations:
        assert index.stats.comparisons > 0
    else:
        assert all(v == 0 for v in index.stats.as_dict().values())


def test_unknown_index_name():
    with pytest.raises(ValueError):
        make_index("skip_list")
