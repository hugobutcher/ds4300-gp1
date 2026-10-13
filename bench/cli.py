"""Command-line options shared by ``bench.core_suite`` and ``bench.experiments``."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

from bench.machine import REPO_ROOT
from bench.results import DEFAULT_RESULTS_PATH, ResultsWriter

MACHINES_CSV = REPO_ROOT / "machines.csv"


def parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--member", required=True, help="your name or username, e.g. alice")
    p.add_argument("--machine-id", required=True, help="the machine_id of this computer in machines.csv")
    p.add_argument("--reps", type=int, default=5, help="replicates of every measurement (default 5)")
    p.add_argument("--out", type=Path, default=DEFAULT_RESULTS_PATH, help="results CSV (default results/timings.csv)")
    return p


def writer_from_args(args: argparse.Namespace) -> ResultsWriter:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.machine_id):
        sys.exit("--machine-id may only contain letters, digits, '.', '_' and '-'")
    if MACHINES_CSV.exists() and args.machine_id not in MACHINES_CSV.read_text():
        print(f"warning: machine_id {args.machine_id!r} is not in machines.csv yet", file=sys.stderr)
    return ResultsWriter(member=args.member, machine_id=args.machine_id, path=args.out)


def parse(p: argparse.ArgumentParser, argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    args = p.parse_args(argv)
    if args.reps < 1:
        p.error("--reps must be at least 1")
    return args
