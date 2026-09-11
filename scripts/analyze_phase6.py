#!/usr/bin/env python3
"""Run the deterministic Phase 6 model and profile analysis."""

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

from course_retention.phase6 import (  # noqa: E402
    DEFAULT_HIGH_RISK_QUANTILE,
    DEFAULT_RANDOM_STATE,
    build_phase6_outputs,
    write_phase6_outputs,
)


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "course_term_demand_metrics.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run time-aware high-W-risk models and course profiles.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--years", nargs=3, type=int, default=[2021, 2022, 2023], help="three consecutive approved years within 2021..2025; default: 2021 2022 2023")
    parser.add_argument("--terms", nargs="+", choices=["spring", "fall"], default=["spring", "fall"])
    parser.add_argument("--high-risk-quantile", type=float, default=DEFAULT_HIGH_RISK_QUANTILE)
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1
    try:
        metrics = pd.read_csv(args.input)
        outputs = build_phase6_outputs(
            metrics,
            window=tuple(args.years),
            terms=tuple(args.terms),
            high_risk_quantile=args.high_risk_quantile,
            random_state=args.random_state,
        )
        paths = write_phase6_outputs(outputs, args.output_dir)
    except (TypeError, ValueError, OSError) as exc:
        print(f"analyze_phase6.py failed: {exc}", file=sys.stderr)
        return 1
    report = outputs["report"]
    holdout = [row for row in report.get("holdout_metrics", []) if row.get("model") != "majority_baseline"]
    summary = {
        "status": report["status"],
        "feature_rows": report["row_counts"]["feature_rows"],
        "train_rows": report["row_counts"]["train_rows"],
        "holdout_rows": report["row_counts"]["holdout_rows"],
        "risk_threshold": report["label"]["threshold"],
        "threshold_operator": report["label"]["operator"],
        "models": report["models"]["fit_status"],
        "holdout_model_count": len(holdout),
        "profile_status": report["profile"].get("status"),
        "paths": {key: str(value) for key, value in paths.items()},
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
