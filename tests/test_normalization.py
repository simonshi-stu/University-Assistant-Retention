"""Offline tests for the real UIUC GPA normalization contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.normalization import (  # noqa: E402
    GRADE_COLUMNS,
    build_course_term_metrics,
    normalize_gpa,
)


def _frame(rows):
    base = {
        "Year": 2021,
        "Term": "spring",
        "YearTerm": "2021-sp",
        "Subject": "CS",
        "Number": "101",
        "Course Title": "Intro",
        "Sched Type": "Lecture",
        "W": 0,
        "Students": 10,
        "Primary Instructor": "A",
    }
    for grade in GRADE_COLUMNS:
        base[grade] = 0
    output = []
    for row in rows:
        current = dict(base)
        current.update(row)
        output.append(current)
    return pd.DataFrame(output)


def test_window_filter_keeps_only_three_years():
    frame = _frame([{"Year": 2020}, {"Year": 2021}, {"Year": 2022}, {"Year": 2023}, {"Year": 2024}])
    out = normalize_gpa(frame, (2021, 2022, 2023), ("spring", "fall"))
    assert sorted(out["Year"].unique().tolist()) == [2021, 2022, 2023]


def test_term_filter_keeps_only_spring_and_fall():
    frame = _frame([{"Term": "spring"}, {"Term": "fall"}, {"Term": "summer"}, {"Term": "winter"}])
    out = normalize_gpa(frame, (2021, 2022, 2023), ("spring", "fall"))
    assert sorted(out["Term"].unique().tolist()) == ["fall", "spring"]


def test_missing_required_column_raises():
    frame = _frame([{}]).drop(columns=["Students"])
    with pytest.raises(ValueError):
        normalize_gpa(frame, (2021, 2022, 2023), ("spring", "fall"))


def test_w_proxy_uses_students_plus_w():
    frame = _frame([{"W": 5, "Students": 15}])
    metrics = build_course_term_metrics(frame)
    assert metrics.iloc[0]["W_proxy"] == pytest.approx(5 / 20)


def test_course_term_aggregation_preserves_counts_and_weighting():
    frame = _frame([
        {"Primary Instructor": "A", "A": 3, "Students": 10},
        {"Primary Instructor": "B", "A": 1, "Students": 5},
    ])
    metrics = build_course_term_metrics(frame)
    assert len(metrics) == 1
    row = metrics.iloc[0]
    assert row["Students"] == 15
    assert row["A"] == 4
    assert row["share_A"] == pytest.approx(1.0)


def test_non_numeric_values_are_coerced_to_na():
    frame = _frame([{"A": "not-a-number", "Students": "bad"}])
    out = normalize_gpa(frame, (2021, 2022, 2023), ("spring", "fall"))
    assert pd.isna(out.iloc[0]["A"])
    assert pd.isna(out.iloc[0]["Students"])


def test_terms_and_window_are_strictly_validated():
    frame = _frame([{}])
    with pytest.raises((TypeError, ValueError)):
        normalize_gpa(frame, [2021, 2022, 2023], ("spring", "fall"))
    with pytest.raises((TypeError, ValueError)):
        normalize_gpa(frame, (2021, 2022, 2023), ("summer",))


def test_output_is_reproducible():
    frame = _frame([
        {"Primary Instructor": "A", "A": 2, "Students": 4},
        {"Primary Instructor": "B", "B": 1, "Students": 3},
    ])
    first = build_course_term_metrics(frame)
    second = build_course_term_metrics(frame)
    pd.testing.assert_frame_equal(first, second)
