"""Offline tests for the deterministic Phase 5 analysis contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.phase5 import (  # noqa: E402
    build_course_demand_summary,
    build_course_term_demand_metrics,
    build_phase5_outputs,
)


def _metrics(rows):
    base = {
        "Year": 2021,
        "Term": "spring",
        "Subject": "CS",
        "Number": "101",
        "Course Title": "Intro",
        "Students": 10,
        "W": 2,
        "grade_total": 10,
        "W_proxy": 2 / 12,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_demand_and_w_proxy_use_aggregated_count_formula():
    output, metadata = build_course_term_demand_metrics(
        _metrics([{"Students": 15, "W": 5}]),
    )
    row = output.iloc[0]
    assert row["demand_proxy"] == pytest.approx(20)
    assert row["W_proxy"] == pytest.approx(5 / 20)
    assert metadata["rows_with_valid_demand_proxy"] == 1


def test_missing_counts_are_not_zero_filled():
    output, metadata = build_course_term_demand_metrics(_metrics([
        {"Number": "101", "Students": 10, "W": 2},
        {"Number": "102", "Students": None, "W": 5},
    ]))
    row = output.loc[output["Number"] == "102"].iloc[0]
    assert pd.isna(row["demand_proxy"])
    assert pd.isna(row["W_proxy"])
    assert metadata["rows_with_missing_or_negative_counts"] == 1


def test_filtering_and_duplicate_course_term_validation():
    frame = _metrics([
        {"Year": 2020},
        {"Year": 2021, "Term": "fall"},
        {"Year": 2022, "Term": "summer"},
    ])
    output, _ = build_course_term_demand_metrics(frame)
    assert output[["Year", "Term"]].to_records(index=False).tolist() == [
        (2021, "fall"),
    ]

    duplicate = _metrics([{}, {}])
    with pytest.raises(ValueError, match="unique course-term"):
        build_course_term_demand_metrics(duplicate)


def test_course_summary_reconciles_total_demand_and_weighted_w_proxy():
    metrics = _metrics([
        {"Year": 2021, "Students": 10, "W": 0},
        {"Year": 2022, "Students": 20, "W": 5},
    ])
    outputs = build_phase5_outputs(metrics, min_demand_proxy=1)
    summary = outputs["course_summary"]
    row = summary.iloc[0]
    assert row["demand_proxy_total"] == pytest.approx(35)
    assert row["students_total"] == pytest.approx(30)
    assert row["w_total"] == pytest.approx(5)
    assert row["w_proxy_weighted"] == pytest.approx(5 / 35)
    assert row["course_term_count"] == 2


def test_high_demand_threshold_is_deterministic_and_summary_is_reproducible():
    frame = _metrics([
        {"Number": "001", "Students": 10, "W": 0},
        {"Number": "002", "Students": 20, "W": 0},
        {"Number": "003", "Students": 30, "W": 0},
        {"Number": "004", "Students": 40, "W": 0},
    ])
    first = build_phase5_outputs(frame, min_demand_proxy=1)
    second = build_phase5_outputs(frame, min_demand_proxy=1)
    pd.testing.assert_frame_equal(first["course_terms"], second["course_terms"])
    assert first["course_terms"]["is_high_demand"].sum() == 1
    assert first["report"]["ranking_parameters"]["high_demand_threshold"] == pytest.approx(32.5)


def test_summary_requires_phase5_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        build_course_demand_summary(pd.DataFrame({"Subject": ["CS"]}))
