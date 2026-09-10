#!/usr/bin/env python3
"""Run the deterministic Phase 5 demand and W-proxy analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.phase5 import (  # noqa: E402
    DEFAULT_HIGH_DEMAND_QUANTILE,
    DEFAULT_MIN_DEMAND_PROXY,
    build_phase5_outputs,
    write_phase5_outputs,
)


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "course_term_metrics.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze UIUC demand and W-based withdrawal proxy.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--years", nargs=3, type=int, default=[2021, 2022, 2023])
    parser.add_argument("--terms", nargs="+", choices=["spring", "fall"], default=["spring", "fall"])
    parser.add_argument("--high-demand-quantile", type=float, default=DEFAULT_HIGH_DEMAND_QUANTILE)
    parser.add_argument("--min-demand-proxy", type=int, default=DEFAULT_MIN_DEMAND_PROXY)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1
    try:
        metrics = pd.read_csv(args.input)
        outputs = build_phase5_outputs(
            metrics,
            window=tuple(args.years),
            terms=tuple(args.terms),
            high_demand_quantile=args.high_demand_quantile,
            min_demand_proxy=args.min_demand_proxy,
        )
        paths = write_phase5_outputs(outputs, args.output_dir)
    except (TypeError, ValueError, OSError) as exc:
        print(f"analyze_phase5.py failed: {exc}", file=sys.stderr)
        return 1

    summary = {
        "status": outputs["report"]["status"],
        "course_term_rows": int(len(outputs["course_terms"])),
        "course_rows": int(len(outputs["course_summary"])),
        "valid_demand_rows": outputs["report"]["row_counts"]["valid_demand_rows"],
        "valid_w_proxy_rows": outputs["report"]["row_counts"]["valid_w_proxy_rows"],
        "paths": {key: str(value) for key, value in paths.items()},
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
