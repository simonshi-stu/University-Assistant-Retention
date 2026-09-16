#!/usr/bin/env python3
"""Run the independent six-year stable-course 2024 backtest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from course_retention.course_trajectory import build_course_trajectory_outputs, write_course_trajectory_outputs

RAW_DEFAULT = ROOT / "data" / "raw" / "gpa" / "uiuc-gpa-dataset.csv"
OUTPUT_DEFAULT = ROOT / "data" / "processed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the 2019-2024 stable-course backtest with adaptive term matching.")
    parser.add_argument("--input", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1
    try:
        outputs = build_course_trajectory_outputs(pd.read_csv(args.input))
        paths = write_course_trajectory_outputs(outputs, args.output_dir)
    except (TypeError, ValueError, OSError) as exc:
        print(f"analyze_course_trajectory.py failed: {exc}", file=sys.stderr)
        return 1
    report = outputs["report"]
    summary = {
        "status": report["status"], "source_years": report["source_years"],
        "training_rows": report["training_rows"], "holdout_rows": report["holdout_rows"],
        "metrics_rows": int(len(outputs["metrics"])),
        "paths": {key: str(value) for key, value in paths.items()},
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
