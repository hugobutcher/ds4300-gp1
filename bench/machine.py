"""Facts about the machine the benchmark is running on, captured automatically.

Inside Docker on macOS or Windows, the container runs in a Linux virtual
machine: ``mem_total_gb`` and ``cpu_count`` describe that VM (whatever Docker
Desktop is allowed to use), not the laptop. That is why each team member also
fills in ``machines.csv`` by hand with the laptop's real specs.
"""

from __future__ import annotations

import os
import platform
import subprocess
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            name, _, value = line.partition(":")
            if name.strip() in ("model name", "Model", "Hardware"):
                return value.strip()
    return platform.processor() or "unknown"


def _mem_total_gb() -> float | None:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024**2, 2)
    return None


def _git_version() -> str:
    """Short commit hash, plus ``-dirty`` if tracked code differs from that commit."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no", "--", "indexes", "datagen", "bench"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{commit}-dirty" if dirty else commit


@lru_cache(maxsize=1)
def machine_info() -> dict[str, object]:
    return {
        "code_version": _git_version(),
        "python_version": platform.python_version(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu_model_detected": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "mem_total_gb": _mem_total_gb(),
        "in_docker": Path("/.dockerenv").exists(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", ""),
    }
