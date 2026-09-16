"""Normalization utilities for UIUC course-term grade distributions.

Raw grain: the source CSV is a course-term-instructor grade distribution. Each
row describes one instructor's grade counts for a given course in a given term.
There is no section id in the raw data, so downstream metrics are at the
course-term grain, never at the section grain.

``w_mark_share`` is strictly ``W / (Students + W)``. It is a derived course-
term share, not an official withdrawal rate; missing inputs are not zero-filled.
"""

from __future__ import annotations

import pathlib
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .config import DATA_RAW_DIR, PRIMARY_TERMS, validate_window


GRADE_COLUMNS = (
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F",
)
GRADE_POINT_MAP = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7, "F": 0.0,
}
NUMERIC_COLUMNS = GRADE_COLUMNS + ("W", "Students")
REQUIRED_COLUMNS = (
    "Year", "Term", "YearTerm", "Subject", "Number", "Course Title", "Sched Type",
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F",
    "W", "Students", "Primary Instructor",
)
GROUP_KEYS = ("Year", "Term", "Subject", "Number", "Course Title")
DUP_KEYS = (
    "Year", "Term", "Subject", "Number", "Course Title", "Sched Type", "Primary Instructor",
)


def _validate_terms(terms: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(terms, tuple):
        raise TypeError("terms must be a tuple")
    if len(terms) == 0:
        raise ValueError("terms must be non-empty")
    normalized = []
    for term in terms:
        if not isinstance(term, str):
            raise TypeError("terms entries must be strings")
        value = term.strip().lower()
        if value not in PRIMARY_TERMS:
            raise ValueError(f"unsupported term: {term!r}")
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise ValueError("terms must not contain duplicates")
    return tuple(normalized)


def _validate_window(window: Sequence[int]) -> tuple[int, int, int]:
    if not isinstance(window, tuple):
        raise TypeError("window must be a tuple")
    if len(window) != 3:
        raise ValueError("window must contain exactly three years")
    for year in window:
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError("window years must be ints")
    validate_window(window)
    return (window[0], window[1], window[2])


def _check_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def load_gpa_raw(
    path=None,
    window=(2021, 2022, 2023),
    terms=("spring", "fall"),
) -> pd.DataFrame:
    if path is None:
        path = Path(DATA_RAW_DIR) / "gpa" / "uiuc-gpa-dataset.csv"
    frame = pd.read_csv(path)
    _check_columns(frame, REQUIRED_COLUMNS)
    return normalize_gpa(frame, window, terms)


def normalize_gpa(
    frame,
    window=(2021, 2022, 2023),
    terms=("spring", "fall"),
) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    window_t = _validate_window(window)
    terms_t = _validate_terms(terms)
    _check_columns(frame, REQUIRED_COLUMNS)

    out = frame.copy()
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce")
    out["Term"] = out["Term"].astype("string").str.strip().str.lower()
    out = out[out["Year"].isin(window_t)]
    out = out[out["Term"].isin(terms_t)]
    for column in NUMERIC_COLUMNS:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out.reset_index(drop=True)


def build_course_term_metrics(frame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    _check_columns(frame, REQUIRED_COLUMNS)
    work = frame.copy()
    for column in NUMERIC_COLUMNS:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    grouped = work.groupby(list(GROUP_KEYS), dropna=False, sort=True)
    aggregations = {column: "sum" for column in NUMERIC_COLUMNS}
    metrics = grouped.agg(aggregations).reset_index()
    metrics["grade_total"] = metrics[list(GRADE_COLUMNS)].sum(axis=1, min_count=1)

    w_sum = metrics["W"]
    students_sum = metrics["Students"]
    denominator = w_sum + students_sum
    valid = w_sum.notna() & students_sum.notna() & (denominator > 0)
    w_proxy = pd.Series(pd.NA, index=metrics.index, dtype="Float64")
    w_proxy.loc[valid] = w_sum.loc[valid] / denominator.loc[valid]
    metrics["W_proxy"] = w_proxy
    metrics["w_mark_share"] = w_proxy
    grade_points = sum(metrics[column] * GRADE_POINT_MAP[column] for column in GRADE_COLUMNS)
    metrics["grade_point_mean"] = grade_points.div(metrics["grade_total"].where(metrics["grade_total"] > 0))

    for column in GRADE_COLUMNS:
        denominator = metrics["grade_total"]
        valid = denominator.notna() & (denominator > 0) & metrics[column].notna()
        share = pd.Series(pd.NA, index=metrics.index, dtype="Float64")
        share.loc[valid] = metrics.loc[valid, column] / denominator.loc[valid]
        metrics[f"share_{column}"] = share

    ordered = list(GROUP_KEYS) + list(GRADE_COLUMNS) + [
        "W", "Students", "W_proxy", "w_mark_share", "grade_total", "grade_point_mean",
    ] + [f"share_{column}" for column in GRADE_COLUMNS]
    return metrics[ordered].reset_index(drop=True)


def _count_non_numeric(series: pd.Series) -> int:
    coerced = pd.to_numeric(series, errors="coerce")
    return int((series.notna() & coerced.isna()).sum())


def build_quality_report(raw, filtered, metrics, window, terms) -> dict:
    if not isinstance(raw, pd.DataFrame):
        raise TypeError("raw must be a pandas DataFrame")
    if not isinstance(filtered, pd.DataFrame):
        raise TypeError("filtered must be a pandas DataFrame")
    if not isinstance(metrics, pd.DataFrame):
        raise TypeError("metrics must be a pandas DataFrame")
    window_t = _validate_window(window)
    terms_t = _validate_terms(terms)
    _check_columns(raw, REQUIRED_COLUMNS)
    _check_columns(filtered, REQUIRED_COLUMNS)

    raw_year = pd.to_numeric(raw["Year"], errors="coerce")
    raw_term = raw["Term"].astype("string").str.strip().str.lower()
    scope = raw.loc[raw_year.isin(window_t) & raw_term.isin(terms_t)]
    raw_non_numeric = {
        column: _count_non_numeric(scope[column]) for column in NUMERIC_COLUMNS
    }
    filtered_missing = {
        column: int(filtered[column].isna().sum()) for column in filtered.columns
    }

    return {
        "raw_rows": int(len(raw)),
        "filtered_rows": int(len(filtered)),
        "course_term_rows": int(len(metrics)),
        "window": list(window_t),
        "terms": list(terms_t),
        "filtered_missing_counts": filtered_missing,
        "raw_non_numeric_counts_in_scope": raw_non_numeric,
        "duplicate_rows": int(raw.duplicated(subset=list(DUP_KEYS), keep=False).sum()),
        "source_grain": "course-term-instructor grade distribution",
        "metrics_grain": "course-term",
        "filter_order": [
            "validate window and terms", "check raw header", "coerce Year and normalize Term",
            "filter window and terms", "coerce numeric grade/W/Students columns",
            "aggregate course-term metrics",
        ],
        "w_mark_share_formula": "w_mark_share = W / (Students + W), only when both sums are available and denominator > 0",
        "grade_point_mean_definition": "Estimated weighted mean from A+ through F counts on a 4.0-style scale; not an official GPA.",
        "no_section_id": True,
        "limitations": ["source has no section id", "w_mark_share is not an official withdrawal rate", "grade_point_mean is not an official GPA"],
    }


def write_quality_report(report, path) -> pathlib.Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    with out.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, ensure_ascii=False, default=str)
        handle.write("\n")
    return out
