"""Load the Spotify Tracks dataset and turn a column into (key, row_id) pairs.

    from loaders.spotify import load_tracks, key_value_pairs

    tracks = load_tracks()                       # list of dicts, one per CSV row
    pairs = key_value_pairs(tracks, "tempo")     # [(87.917, 0), (77.489, 1), ...]

Facts worth knowing about the data (114,000 rows):

* ``track_id`` is NOT unique: the same song appears once per genre it is
  listed under (89,741 distinct ids).
* ``popularity`` has only 101 distinct values (0-100) and ``track_genre``
  only 114, so those keys have long lists of row ids.
* The file is grouped by ``track_genre`` (1,000 rows per genre).
* One row has no ``track_name``/``artists``/``album_name``; it is skipped
  when those columns are used as keys.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_PATH = Path(os.environ.get("SPOTIFY_CSV", REPO_ROOT / "data" / "spotify_tracks.csv"))


def _text(raw: str) -> str:
    """Normalize text keys for search-as-you-type: case-insensitive, trimmed."""
    return raw.strip().casefold()


#: Columns you can index, and how each raw CSV string becomes a key.
KEY_COLUMNS: dict[str, Callable[[str], Any]] = {
    "track_id": str,
    "track_name": _text,
    "artists": _text,
    "album_name": _text,
    "track_genre": str,
    "popularity": int,
    "duration_ms": int,
    "tempo": float,
    "danceability": float,
    "energy": float,
}


def load_tracks(path: Path | str = DEFAULT_CSV_PATH) -> list[dict[str, str]]:
    """Read the CSV. Each row is a dict of raw strings plus ``row_id`` (an int)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run `make data` to download the dataset.")
    with path.open(newline="", encoding="utf-8") as f:
        rows: list[dict[str, Any]] = list(csv.DictReader(f))
    for row_id, row in enumerate(rows):
        row.pop("", None)  # the CSV's unnamed pandas index column
        row["row_id"] = row_id
    return rows


def key_value_pairs(tracks: list[dict[str, Any]], column: str) -> list[tuple[Any, int]]:
    """Return ``(key, row_id)`` for every track, in file order.

    Rows where the column is empty are skipped. Insert these pairs into an
    index with ``index.insert(key, row_id)``.
    """
    try:
        convert = KEY_COLUMNS[column]
    except KeyError:
        raise ValueError(f"unknown column {column!r}; choose from {sorted(KEY_COLUMNS)}") from None
    pairs: list[tuple[Any, int]] = []
    for row in tracks:
        raw = row[column]
        if raw.strip():
            pairs.append((convert(raw), row["row_id"]))
    return pairs
