"""Synthetic keys and query workloads.  *** YOU IMPLEMENT THIS FILE. ***

Real data (Spotify) shows how the indexes behave on realistic keys.
Synthetic data lets you control one variable at a time: how many keys, what
order they arrive in, how many lookups hit vs miss, how wide a range is.

Rules for every function:

* Use ``rng = random.Random(seed)`` and draw all randomness from ``rng``, so
  the same seed always produces the same output (on any machine).
* Never modify the list you are given; return a new one.

``tests/test_synthetic.py`` checks each function against this spec. Run it
with ``make test``.
"""

from __future__ import annotations

import random
import string
from typing import Any, Optional, Sequence


def random_keys(
    n: int,
    length: int = 8,
    alphabet: str = string.ascii_lowercase,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n`` *distinct* random strings, each exactly ``length`` characters
    long, using only characters from ``alphabet``, in random order.

    Raise ``ValueError`` if ``n`` is larger than the number of possible
    strings (``len(alphabet) ** length``).
    """
    base = len(alphabet)
    space = base ** length
    if n > space:
        raise ValueError(
            f"cannot make {n} distinct strings of length {length} "
            f"from a {base}-char alphabet (only {space} exist)"
        )

    rng = random.Random(seed)
    indices = rng.sample(range(space), n)

    keys = []
    for idx in indices:
        chars = []
        for _ in range(length):
            idx, remainder = divmod(idx, base)
            chars.append(alphabet[remainder])
        keys.append("".join(reversed(chars)))
    return keys


def arrange(
    keys: Sequence[Any],
    order: str,
    seed: Optional[int] = None,
    swap_fraction: float = 0.05,
) -> list[Any]:
    """Return a new list holding the same keys in the requested order.

    order:
        "random"        shuffled
        "sorted"        ascending
        "reversed"      descending
        "nearly_sorted" ascending, then ``round(swap_fraction * len(keys))``
                        swaps of two randomly chosen positions

    Raise ``ValueError`` for any other ``order``.
    """
    rng = random.Random(seed)
    result = list(keys)

    if order == "random":
        rng.shuffle(result)
    elif order == "sorted":
        result.sort()
    elif order == "reversed":
        result.sort(reverse=True)
    elif order == "nearly_sorted":
        result.sort()
        n = len(result)
        num_swaps = round(swap_fraction * n)
        for _ in range(num_swaps):
            i = rng.randrange(n)
            j = rng.randrange(n)
            result[i], result[j] = result[j], result[i]
    else:
        raise ValueError(f"unknown order: {order!r}")

    return result


def point_queries(
    keys: Sequence[str],
    n_queries: int,
    hit_rate: float,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n_queries`` lookup keys in random order.

    Exactly ``round(n_queries * hit_rate)`` of them are *hits*: chosen at
    random (repeats allowed) from ``keys``. The rest are *misses*: random
    strings that are guaranteed NOT to be in ``keys``, each the same length as
    a randomly chosen key from ``keys``.
    """
    rng = random.Random(seed)
    key_list = list(keys)
    key_set = set(key_list)

    n_hits = round(n_queries * hit_rate)
    n_misses = n_queries - n_hits

    queries = [rng.choice(key_list) for _ in range(n_hits)]

    alphabet = string.ascii_lowercase
    for _ in range(n_misses):
        target_len = len(rng.choice(key_list))
        while True:
            candidate = "".join(rng.choice(alphabet) for _ in range(target_len))
            if candidate not in key_set:
                break
        queries.append(candidate)

    rng.shuffle(queries)
    return queries


def range_queries(
    keys: Sequence[Any],
    n_queries: int,
    selectivity: float,
    seed: Optional[int] = None,
) -> list[tuple[Any, Any]]:
    """Return ``n_queries`` ranges ``(lo, hi)`` for ``index.range_search(lo, hi)``.

    Let ``d`` be the number of *distinct* keys and ``w = max(1, round(selectivity * d))``.
    Sort the distinct keys, pick a random starting position that leaves room
    for ``w`` keys, and use the key there as ``lo`` and the key ``w - 1``
    positions later as ``hi``. So exactly ``w`` distinct keys satisfy
    ``lo <= key <= hi``. Works for any comparable keys (strings or numbers).
    """
    rng = random.Random(seed)
    distinct = sorted(set(keys))
    d = len(distinct)
    w = max(1, round(selectivity * d))

    max_start = d - w

    queries = []
    for _ in range(n_queries):
        start = rng.randint(0, max_start)
        lo = distinct[start]
        hi = distinct[start + w - 1]
        queries.append((lo, hi))
    return queries


def prefix_queries(
    keys: Sequence[str],
    n_queries: int,
    prefix_length: int,
    seed: Optional[int] = None,
) -> list[str]:
    """Return ``n_queries`` prefixes for ``index.prefix_search(prefix)``.

    Each prefix is the first ``prefix_length`` characters of a randomly chosen
    key that is at least ``prefix_length`` characters long, so every prefix
    matches at least one key.
    """
    rng = random.Random(seed)
    eligible = [k for k in keys if len(k) >= prefix_length]
    return [rng.choice(eligible)[:prefix_length] for _ in range(n_queries)]
