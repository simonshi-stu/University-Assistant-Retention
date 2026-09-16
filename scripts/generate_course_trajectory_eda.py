#!/usr/bin/env python3
"""Write compact six-year EDA tables without fitting a model."""
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

from course_retention.course_trajectory import aggregate_stable_course_terms, build_trajectory_eda

RAW_DEFAULT = ROOT / "data" / "raw" / "gpa" / "uiuc-gpa-dataset.csv"
OUTPUT_DEFAULT = ROOT / "data" / "processed"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write reproducible 2019-2024 Spring/Fall EDA outputs.")
    parser.add_argument("--input", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT)
    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"input file not found: {args.input}", file=sys.stderr)
        return 1
    try:
        raw = pd.read_csv(args.input)
        metrics, _ = aggregate_stable_course_terms(raw)
        eda = build_trajectory_eda(raw, metrics)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "report": args.output_dir / "course_trajectory_eda_report.json",
            "inventory": args.output_dir / "course_trajectory_eda_inventory.csv",
            "coverage": args.output_dir / "course_trajectory_eda_year_term_coverage.csv",
            "subject_distribution": args.output_dir / "course_trajectory_eda_subject_distribution.csv",
            "numeric_summary": args.output_dir / "course_trajectory_eda_numeric_summary.csv",
            "join_audit": args.output_dir / "course_trajectory_eda_join_audit.csv",
        }
        paths["report"].write_text(json.dumps(eda["report"], indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        for key in ("inventory", "coverage", "subject_distribution", "numeric_summary", "join_audit"):
            eda[key].to_csv(paths[key], index=False)
    except (TypeError, ValueError, OSError, pd.errors.ParserError) as exc:
        print(f"generate_course_trajectory_eda.py failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": eda["report"]["status"], "filtered_rows": eda["report"]["filtered_rows"], "paths": {key: str(path) for key, path in paths.items()}}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
