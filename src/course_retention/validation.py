"""Validation helpers for course-retention tables.

This module validates normalized tables and performs a strict time-based split
by academic year. The split uses the first two years of the window for
training and the third year for holdout. No section-level inference is
performed here; validation is table-level only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .config import validate_window, window_train_holdout
from .normalization import GRADE_COLUMNS, NUMERIC_COLUMNS, REQUIRED_COLUMNS, GROUP_KEYS


def _strict_window(window: Any) -> tuple[int, int, int]:
    if not isinstance(window, tuple) or len(window) != 3:
        raise ValueError("window must be a tuple of length 3")
    for value in window:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("window elements must be ints")
    validate_window(window)
    window_train_holdout(window)
    return window


def _strict_terms(terms: Any) -> tuple[str, ...]:
    if not isinstance(terms, tuple) or not terms:
        raise ValueError("terms must be a non-empty tuple")
    seen = set()
    normalized = []
    for term in terms:
        if not isinstance(term, str):
            raise ValueError("terms must contain strings")
        lowered = term.strip().lower()
        if lowered not in ("spring", "fall"):
            raise ValueError("terms must be spring or fall")
        if lowered in seen:
            raise ValueError("terms must not contain duplicates")
        seen.add(lowered)
        normalized.append(lowered)
    return tuple(normalized)


def split_by_window(
    metrics: pd.DataFrame, window=(2021, 2022, 2023)
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return temporal train and holdout copies without random shuffling."""
    window = _strict_window(window)
    if not isinstance(metrics, pd.DataFrame):
        raise ValueError("metrics must be a DataFrame")
    if metrics.empty:
        raise ValueError("metrics must be non-empty")
    if "Year" not in metrics.columns:
        raise ValueError("metrics must have a Year column")

    years = pd.to_numeric(metrics["Year"], errors="coerce")
    if years.isna().any():
        raise ValueError("Year contains non-numeric values")
    if not (years == years.astype("int64")).all():
        raise ValueError("Year values must be integers")
    if not years.isin(list(window)).all():
        raise ValueError("Year values must be within window")

    train_years, holdout_year = window_train_holdout(window)
    train = metrics[years.isin(train_years)].copy()
    holdout = metrics[years == holdout_year].copy()
    if train.empty:
        raise ValueError("train split is empty")
    if holdout.empty:
        raise ValueError("holdout split is empty")
    return train, holdout


def validate_normalized_tables(
    filtered,
    metrics,
    window=(2021, 2022, 2023),
    terms=("spring", "fall"),
) -> dict:
    """Return a lean, JSON-serializable validation report without mutation."""
    window = _strict_window(window)
    terms = _strict_terms(terms)
    checks: dict[str, bool] = {}
    errors: list[str] = []

    filtered_rows = int(len(filtered)) if isinstance(filtered, pd.DataFrame) else 0
    metrics_rows = int(len(metrics)) if isinstance(metrics, pd.DataFrame) else 0
    train_rows = 0
    holdout_rows = 0

    filtered_required = list(REQUIRED_COLUMNS)
    metrics_required = (
        list(GROUP_KEYS)
        + list(GRADE_COLUMNS)
        + ["W", "Students", "grade_total", "W_proxy"]
        + ["share_" + column for column in GRADE_COLUMNS]
    )

    if not isinstance(filtered, pd.DataFrame):
        checks["filtered_is_dataframe"] = False
        errors.append("filtered is not a DataFrame")
    else:
        checks["filtered_is_dataframe"] = True
        missing = [column for column in filtered_required if column not in filtered.columns]
        checks["filtered_has_required_columns"] = not missing
        if missing:
            errors.append("filtered missing columns: " + ", ".join(missing))

    if not isinstance(metrics, pd.DataFrame):
        checks["metrics_is_dataframe"] = False
        errors.append("metrics is not a DataFrame")
    else:
        checks["metrics_is_dataframe"] = True
        missing = [column for column in metrics_required if column not in metrics.columns]
        checks["metrics_has_required_columns"] = not missing
        if missing:
            errors.append("metrics missing columns: " + ", ".join(missing))

    for label, frame in (("filtered", filtered), ("metrics", metrics)):
        if isinstance(frame, pd.DataFrame) and "Year" in frame.columns:
            years = pd.to_numeric(frame["Year"], errors="coerce")
            ok = bool(years.notna().all() and years.isin(list(window)).all())
            checks[f"{label}_year_in_window"] = ok
            if not ok:
                errors.append(f"{label} Year values outside window or non-numeric")
        else:
            checks[f"{label}_year_in_window"] = False
            errors.append(f"{label} missing Year column")

        if isinstance(frame, pd.DataFrame) and "Term" in frame.columns:
            lowered = frame["Term"].astype(str).str.strip().str.lower()
            ok = bool(lowered.isin(list(terms)).all())
            checks[f"{label}_term_in_terms"] = ok
            if not ok:
                errors.append(f"{label} Term values outside terms")
        else:
            checks[f"{label}_term_in_terms"] = False
            errors.append(f"{label} missing Term column")

    if isinstance(metrics, pd.DataFrame) and all(column in metrics.columns for column in GROUP_KEYS):
        duplicate = metrics.duplicated(subset=list(GROUP_KEYS)).any()
        checks["metrics_group_keys_unique"] = not bool(duplicate)
        if duplicate:
            errors.append("metrics GROUP_KEYS contain duplicates")
    else:
        checks["metrics_group_keys_unique"] = False
        errors.append("metrics missing GROUP_KEYS columns")

    if isinstance(metrics, pd.DataFrame) and "W_proxy" in metrics.columns:
        proxy = pd.to_numeric(metrics["W_proxy"], errors="coerce").dropna()
        ok = bool(((proxy >= 0) & (proxy <= 1)).all())
        checks["metrics_w_proxy_in_range"] = ok
        if not ok:
            errors.append("metrics W_proxy values outside [0, 1]")
    else:
        checks["metrics_w_proxy_in_range"] = False
        errors.append("metrics missing W_proxy column")

    sums_ok = True
    sum_columns = list(GRADE_COLUMNS) + ["W", "Students"]
    if isinstance(filtered, pd.DataFrame) and isinstance(metrics, pd.DataFrame):
        for column in sum_columns:
            if column not in filtered.columns or column not in metrics.columns:
                sums_ok = False
                errors.append("cannot compare sums for column: " + column)
                continue
            filtered_sum = pd.to_numeric(filtered[column], errors="coerce").fillna(0).sum()
            metrics_sum = pd.to_numeric(metrics[column], errors="coerce").fillna(0).sum()
            if abs(float(filtered_sum) - float(metrics_sum)) > 1e-6:
                sums_ok = False
                errors.append("sum mismatch for column: " + column)
    else:
        sums_ok = False
    checks["column_sums_match"] = sums_ok

    try:
        train, holdout = split_by_window(metrics, window=window)
        train_rows = int(len(train))
        holdout_rows = int(len(holdout))
        checks["split_by_window"] = True
    except Exception as exc:
        checks["split_by_window"] = False
        errors.append("split_by_window failed: " + str(exc))

    return {
        "passed": bool(all(checks.values()) and not errors),
        "checks": checks,
        "errors": errors,
        "filtered_rows": filtered_rows,
        "metrics_rows": metrics_rows,
        "train_rows": train_rows,
        "holdout_rows": holdout_rows,
    }


def write_validation_report(report: Mapping[str, Any], path) -> Path:
    """Write a deterministic JSON validation report and return its Path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    target.write_text(payload + "\n", encoding="utf-8")
    return target
