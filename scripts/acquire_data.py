#!/usr/bin/env python3
"""CLI entry point for acquiring course retention data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _insert_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire course retention data from official sources.")
    parser.add_argument("--years", nargs=3, type=int, default=[2021, 2022, 2023])
    parser.add_argument("--terms", nargs="+", choices=["spring", "fall"], default=["spring", "fall"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    _insert_src_on_path()
    from course_retention.acquisition import AcquisitionIncompleteError, acquire

    args = build_parser().parse_args(argv)
    try:
        summary = acquire(tuple(args.years), tuple(args.terms), args.force, args.allow_partial)
    except AcquisitionIncompleteError as exc:
        print(json.dumps({"status": "incomplete", "error": str(exc)}))
        return 1
    except (TypeError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    print(json.dumps(summary, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
