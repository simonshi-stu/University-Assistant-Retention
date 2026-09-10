#!/usr/bin/env python3
"""Validate normalized course retention tables and write a JSON report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.validation import (  # noqa: E402
    validate_normalized_tables,
    write_validation_report,
)

FILTERED_PATH = PROJECT_ROOT / "data" / "interim" / "gpa_filtered.csv"
METRICS_PATH = PROJECT_ROOT / "data" / "processed" / "course_term_metrics.csv"
REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "validation_report.json"

WINDOW = (2021, 2022, 2023)
TERMS = ("spring", "fall")


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path)


def main() -> int:
    try:
        filtered = _load_csv(FILTERED_PATH)
        metrics = _load_csv(METRICS_PATH)
        report = validate_normalized_tables(
            filtered,
            metrics,
            window=WINDOW,
            terms=TERMS,
        )
        write_validation_report(report, REPORT_PATH)

        summary = {
            "passed": bool(report.get("passed", False)),
            "filtered_rows": int(len(filtered)),
            "metrics_rows": int(len(metrics)),
            "report_path": str(REPORT_PATH),
        }
        print(json.dumps(summary, indent=2, default=str))
        return 0 if summary["passed"] else 1
    except Exception as exc:  # noqa: BLE001
        print(f"validate_data.py failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
