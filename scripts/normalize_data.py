#!/usr/bin/env python3
"""Normalize UIUC GPA raw data into interim and processed artifacts."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.normalization import (  # noqa: E402
    build_course_term_metrics,
    build_quality_report,
    load_gpa_raw,
    normalize_gpa,
    write_quality_report,
)

WINDOW = (2021, 2022, 2023)
TERMS = ("spring", "fall")

RAW_PATH = PROJECT_ROOT / "data" / "raw" / "gpa" / "uiuc-gpa-dataset.csv"
FILTERED_PATH = PROJECT_ROOT / "data" / "interim" / "gpa_filtered.csv"
METRICS_PATH = PROJECT_ROOT / "data" / "processed" / "course_term_metrics.csv"
REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "data_quality_report.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    try:
        raw = pd.read_csv(RAW_PATH)
        filtered = load_gpa_raw(path=RAW_PATH, window=WINDOW, terms=TERMS)
        filtered = normalize_gpa(filtered, WINDOW, TERMS)
        metrics = build_course_term_metrics(filtered)
        report = build_quality_report(
            raw=raw,
            filtered=filtered,
            metrics=metrics,
            window=WINDOW,
            terms=TERMS,
        )

        for path in (FILTERED_PATH, METRICS_PATH, REPORT_PATH):
            _ensure_parent(path)
        filtered.to_csv(FILTERED_PATH, index=False)
        metrics.to_csv(METRICS_PATH, index=False)
        write_quality_report(report, REPORT_PATH)

        print(str(FILTERED_PATH))
        print(str(METRICS_PATH))
        print(str(REPORT_PATH))
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
