"""Spec tests for datagen/synthetic.py -- the file YOU implement.

These fail until you implement the functions. Each test checks one promise
from the docstrings.
"""

from __future__ import annotations

import string
from collections import Counter

import pytest

from datagen.synthetic import arrange, point_queries, prefix_queries, random_keys, range_queries


# ------------------------------------------------------------------ random_keys
def test_random_keys_are_distinct_fixed_length_and_use_the_alphabet():
    keys = random_keys(5000, length=6, alphabet="abc123", seed=1)
    assert len(keys) == 5000
    assert len(set(keys)) == 5000
    assert all(len(k) == 6 for k in keys)
    assert set("".join(keys)) <= set("abc123")


def test_random_keys_are_reproducible_and_seed_dependent():
    assert random_keys(100, seed=42) == random_keys(100, seed=42)
    assert random_keys(100, seed=42) != random_keys(100, seed=43)


def test_random_keys_are_not_in_sorted_order():
    keys = random_keys(1000, seed=3)
    assert keys != sorted(keys)


def test_random_keys_can_use_every_possible_string():
    keys = random_keys(8, length=3, alphabet="ab", seed=0)
    assert sorted(keys) == ["aaa", "aab", "aba", "abb", "baa", "bab", "bba", "bbb"]


def test_random_keys_rejects_impossible_requests():
    with pytest.raises(ValueError):
        random_keys(9, length=3, alphabet="ab")


# ---------------------------------------------------------------------- arrange
KEYS = [f"k{i:04d}" for i in range(1000)][::-7] + [f"k{i:04d}" for i in range(1000)][1::7]


@pytest.mark.parametrize("order", ["random", "sorted", "reversed", "nearly_sorted"])
def test_arrange_keeps_the_same_keys_and_does_not_modify_input(order):
    original = list(KEYS)
    result = arrange(KEYS, order, seed=5)
    assert KEYS == original
    assert Counter(result) == Counter(KEYS)


def test_arrange_orders():
    assert arrange(KEYS, "sorted") == sorted(KEYS)
    assert arrange(KEYS, "reversed") == sorted(KEYS, reverse=True)
    shuffled = arrange(KEYS, "random", seed=5)
    assert shuffled not in (sorted(KEYS), sorted(KEYS, reverse=True))
    assert shuffled == arrange(KEYS, "random", seed=5)


def test_nearly_sorted_is_mostly_in_place():
    keys = list(range(10_000))
    result = arrange(keys, "nearly_sorted", seed=8, swap_fraction=0.05)
    moved = sum(1 for i, k in enumerate(result) if k != i)
    # 500 swaps move at most 1,000 keys (fewer if a swap repeats a position).
    assert 0 < moved <= 1000
    assert arrange(keys, "nearly_sorted", seed=8, swap_fraction=0.0) == keys


def test_arrange_rejects_unknown_order():
    with pytest.raises(ValueError):
        arrange(KEYS, "zigzag")


# ---------------------------------------------------------------- point_queries
WORDS = ["love", "lovely", "hey jude", "yesterday", "help", "imagine", "let it be"]


@pytest.mark.parametrize("hit_rate", [0.0, 0.25, 0.5, 1.0])
def test_point_queries_have_exact_hit_count(hit_rate):
    queries = point_queries(WORDS, 400, hit_rate, seed=11)
    assert len(queries) == 400
    hits = sum(1 for q in queries if q in WORDS)
    assert hits == round(400 * hit_rate)


def test_point_query_misses_look_like_keys():
    lengths = {len(w) for w in WORDS}
    misses = [q for q in point_queries(WORDS, 300, 0.0, seed=2) if q not in WORDS]
    assert len(misses) == 300
    assert all(isinstance(q, str) and len(q) in lengths for q in misses)


def test_point_queries_are_shuffled_and_reproducible():
    queries = point_queries(WORDS, 200, 0.5, seed=9)
    is_hit = [q in WORDS for q in queries]
    assert is_hit != sorted(is_hit) and is_hit != sorted(is_hit, reverse=True)
    assert queries == point_queries(WORDS, 200, 0.5, seed=9)


# ---------------------------------------------------------------- range_queries
@pytest.mark.parametrize("selectivity", [0.0, 0.01, 0.1, 0.5, 1.0])
def test_range_queries_cover_exactly_w_distinct_keys(selectivity):
    keys = [t / 10 for t in range(500, 2000)] * 2  # duplicates on purpose
    distinct = sorted(set(keys))
    width = max(1, round(selectivity * len(distinct)))
    queries = range_queries(keys, 50, selectivity, seed=4)
    assert len(queries) == 50
    for lo, hi in queries:
        assert lo in distinct and hi in distinct
        assert sum(1 for k in distinct if lo <= k <= hi) == width


def test_range_queries_work_on_strings_and_vary():
    queries = range_queries(list(string.ascii_lowercase), 30, 0.2, seed=1)
    assert all(hi > lo for lo, hi in queries)
    assert len(set(queries)) > 1
    assert queries == range_queries(list(string.ascii_lowercase), 30, 0.2, seed=1)


# --------------------------------------------------------------- prefix_queries
def test_prefix_queries_match_at_least_one_key():
    queries = prefix_queries(WORDS, 100, 3, seed=6)
    assert len(queries) == 100
    assert all(len(p) == 3 and any(w.startswith(p) for w in WORDS) for p in queries)
    assert queries == prefix_queries(WORDS, 100, 3, seed=6)


def test_prefix_queries_skip_short_keys():
    queries = prefix_queries(["ab", "abcdef", "x"], 50, 4, seed=0)
    assert set(queries) == {"abcd"}
