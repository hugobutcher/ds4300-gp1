"""Download the Spotify Tracks dataset into ``data/``.

    python -m loaders.download          (or: make data)

The file comes from a pinned revision of the Hugging Face mirror of the Kaggle
"Spotify Tracks Dataset" (maharshipandya), so every student gets exactly the
same bytes; the SHA-256 checksum is verified after download.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

from loaders.spotify import DEFAULT_CSV_PATH

REVISION = "635b034f69257814eff850a5c2b3346fe458134f"
URL = (
    "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset/"
    f"resolve/{REVISION}/dataset.csv"
)
SHA256 = "b202fa49909b2d5cef71a04b1d21243cfeb36414535f2ca9272aa646721177bd"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    target = DEFAULT_CSV_PATH
    if target.exists() and sha256_of(target) == SHA256:
        print(f"{target} already present and verified.")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    print(f"Downloading {URL}\n        -> {target}")
    urllib.request.urlretrieve(URL, partial)
    actual = sha256_of(partial)
    if actual != SHA256:
        partial.unlink()
        print(f"Checksum mismatch: expected {SHA256}, got {actual}", file=sys.stderr)
        return 1
    partial.replace(target)
    print("Done; checksum verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
