"""Stable-course historical backtest for the 2019--2024 UIUC data.

This is an independent extension of the accepted 2021--2023 analysis.  The
course identity is the stable ``Subject + Number`` key. Course titles are
retained for display and audit, but do not split a course number into variants.
Recognisable special-topic offerings are excluded from the continuity/model
input and written to a separate audit table because their titles can represent
a different research topic every term.

Ordinary courses use prior calendar-year observations regardless of
Spring/Fall. A course observed in only one season uses that same season so a
seasonal offering is not matched to the wrong term.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .normalization import GRADE_COLUMNS, REQUIRED_COLUMNS, build_course_term_metrics

BASE_COURSE_KEY = ("Subject", "Number")
COURSE_KEY = ("Subject", "Number", "course_variant")
TERMS = ("spring", "fall")
YEARS = tuple(range(2019, 2025))
TARGET_YEARS = (2022, 2023, 2024)
TRAIN_YEARS = (2022, 2023)
HOLDOUT_YEAR = 2024
LAG_FEATURES = tuple(f"lag{lag}_{field}" for lag in (1, 2, 3) for field in ("w_flag", "w_mark_share", "demand_proxy", "students", "grade_point_mean"))
# Keep one historical outcome family and one historical scale family. The
# other lag columns remain in the audit table and support persistence only.
NUMERIC_FEATURES = ("course_level", "lag1_w_mark_share", "lag2_w_mark_share", "lag3_w_mark_share", "lag1_grade_point_mean", "lag2_grade_point_mean", "lag3_grade_point_mean", "lag1_log_demand_proxy")
CATEGORICAL_FEATURES = ("Subject", "Term")
MODEL_NAMES = ("constant_baseline", "persistence_baseline", "logistic_regression", "random_forest")
OUTPUT_PREFIX = "course_trajectory_"
MIN_HISTORY_YEARS = 3

GRADE_POINT_MAP = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7, "F": 0.0,
}
SPECIAL_TOPIC_PATTERN = re.compile(
    r"\b(?:special|selected)\s+topics?\b|\badvanced\s+special\s+topics?\b|"
    r"\bspecial\s+research\s+problems?\b",
    flags=re.IGNORECASE,
)


def _check_frame(frame: pd.DataFrame) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    missing = [c for c in ("Year", "Term", "Subject", "Number", "Students", "W") if c not in frame]
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def _course_level(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return float(min(900, max(0, int(number) // 100 * 100))) if np.isfinite(number) else np.nan


def _display_title(values: pd.Series) -> str:
    values = values.dropna().astype(str).str.strip()
    if values.empty:
        return ""
    counts = values.value_counts()
    return sorted(counts[counts == counts.max()].index.tolist())[0]


def normalize_course_title(value: Any) -> str:
    """Normalize harmless title punctuation/spacing differences for identity."""
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def is_special_topic_title(value: Any) -> bool:
    """Return whether a title is an identifiable rotating-topics offering."""
    if pd.isna(value):
        return False
    return bool(SPECIAL_TOPIC_PATTERN.search(str(value)))


def _special_topic_key_counts(frame: pd.DataFrame, special_mask: pd.Series) -> dict[str, int]:
    """Count special-topic keys by whether ordinary rows share the key.

    Special-topic rows are filtered out of the ordinary trajectory, but an
    overlapping Subject + Number key remains represented by its ordinary rows.
    These counts keep row exclusion separate from stable-key exclusion.
    """
    key_columns = list(BASE_COURSE_KEY)
    special_keys = frame.loc[special_mask, key_columns].drop_duplicates()
    ordinary_keys = frame.loc[~special_mask, key_columns].drop_duplicates()
    overlap_keys = special_keys.merge(
        ordinary_keys,
        on=key_columns,
        how="inner",
        validate="one_to_one",
    )
    only_keys = special_keys.merge(
        ordinary_keys,
        on=key_columns,
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    return {
        "special_topic_course_keys_with_rows": int(len(special_keys)),
        "special_topic_only_course_keys_excluded": int((only_keys["_merge"] == "left_only").sum()),
        "special_topic_overlap_course_keys_retained": int(len(overlap_keys)),
    }


def build_special_topic_audit(raw: pd.DataFrame) -> pd.DataFrame:
    """Summarise excluded special-topic source rows for evidence and review."""
    _check_frame(raw)
    work = raw.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    work = work.loc[work["Year"].isin(YEARS) & work["Term"].isin(TERMS)].copy()
    work = work.loc[work["Course Title"].map(is_special_topic_title)].copy()
    columns = ["Year", "Term", "Subject", "Number", "Course Title", "source_rows", "Students", "W"]
    if work.empty:
        return pd.DataFrame(columns=columns)
    for column in ("Students", "W"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    return (
        work.groupby(["Year", "Term", "Subject", "Number", "Course Title"], dropna=False, sort=True)
        .agg(source_rows=("Subject", "size"), Students=("Students", "sum"), W=("W", "sum"))
        .reset_index()[columns]
    )


def build_instructor_audit(raw: pd.DataFrame) -> pd.DataFrame:
    """Retain course-term instructor context without using names as causality."""
    _check_frame(raw)
    columns = ["Year", "Term", "Subject", "Number", "instructor_count", "instructors_observed", "source_rows"]
    if "Primary Instructor" not in raw.columns:
        return pd.DataFrame(columns=columns)
    work = raw.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    work = work.loc[work["Year"].isin(YEARS) & work["Term"].isin(TERMS)].copy()
    if "Course Title" in work:
        work = work.loc[~work["Course Title"].map(is_special_topic_title)].copy()
    def instructors(values: pd.Series) -> str:
        names = sorted({str(value).strip() for value in values.dropna() if str(value).strip()})
        return " | ".join(names)
    return (
        work.groupby(["Year", "Term", "Subject", "Number"], dropna=False, sort=True)
        .agg(instructor_count=("Primary Instructor", "nunique"), instructors_observed=("Primary Instructor", instructors), source_rows=("Subject", "size"))
        .reset_index()[columns]
    )


def aggregate_stable_course_terms(raw: pd.DataFrame, years: Sequence[int] = YEARS, terms: Sequence[str] = TERMS) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize raw rows and aggregate on the stable Subject + Number key.

    Special/selected-topics rows are excluded before aggregation. This keeps
    rotating research topics from changing the continuity count of an ordinary
    course with the same number, while the excluded rows remain auditable.
    """
    _check_frame(raw)
    years = tuple(int(y) for y in years)
    terms = tuple(str(t).strip().lower() for t in terms)
    if years != YEARS or terms != TERMS:
        raise ValueError("trajectory input must be filtered to 2019..2024 spring/fall")
    work = raw.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    work = work.loc[work["Year"].isin(years) & work["Term"].isin(terms)].copy()
    for column in ("W", "Students", *GRADE_COLUMNS):
        if column in work:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    for column in GRADE_COLUMNS:
        if column not in work:
            work[column] = np.nan
    special_mask = work["Course Title"].map(is_special_topic_title) if "Course Title" in work else pd.Series(False, index=work.index)
    special_raw_rows = int(special_mask.sum())
    special_key_counts = _special_topic_key_counts(work, special_mask)
    work = work.loc[~special_mask].copy()
    work["_normalized_title"] = work["Course Title"].map(normalize_course_title) if "Course Title" in work else ""
    same_term_title_counts = work.groupby([*BASE_COURSE_KEY, "Year", "Term"], dropna=False)["_normalized_title"].nunique()
    collision_pairs = same_term_title_counts.loc[same_term_title_counts > 1]
    collision_bases = set((key[0], key[1]) for key in collision_pairs.index)
    all_title_counts = work.groupby(list(BASE_COURSE_KEY), dropna=False)["_normalized_title"].nunique()
    multi_title_bases = set(all_title_counts.loc[all_title_counts > 1].index.tolist())
    # The course number is the stable identity requested by the user. Title
    # changes remain visible in the audit but never create a new course key.
    work["course_variant"] = "base"
    grouped = work.groupby(["Year", "Term", *COURSE_KEY], dropna=False, sort=True)
    metrics = grouped[list(GRADE_COLUMNS) + ["W", "Students"]].sum(min_count=1).reset_index()
    titles = grouped["Course Title"].agg(_display_title).reset_index(name="Course Title") if "Course Title" in work else None
    if titles is not None:
        metrics = metrics.merge(titles, on=["Year", "Term", *COURSE_KEY], how="left", validate="one_to_one")
    else:
        metrics["Course Title"] = ""
    metrics["grade_total"] = metrics[list(GRADE_COLUMNS)].sum(axis=1, min_count=1)
    grade_points = metrics.loc[:, list(GRADE_COLUMNS)].mul(pd.Series(GRADE_POINT_MAP)).sum(axis=1, min_count=1)
    metrics["grade_point_mean"] = grade_points.div(metrics["grade_total"].where(metrics["grade_total"] > 0))
    metrics["demand_proxy"] = metrics["Students"] + metrics["W"]
    metrics["W_proxy"] = metrics["W"].div(metrics["demand_proxy"].where(metrics["demand_proxy"] > 0))
    # New semantic name for user-facing explanations; W_proxy remains as a
    # compatibility alias for the older processed tables and tests.
    metrics["w_mark_share"] = metrics["W_proxy"]
    metrics["w_flag"] = (metrics["W"].fillna(0) > 0).astype(int)
    metrics["course_level"] = metrics["Number"].map(_course_level)
    metrics = metrics.sort_values(["Year", "Term", "Subject", "Number"], kind="mergesort").reset_index(drop=True)
    audit = build_title_audit(metrics, raw=work)
    # A same-year collision can create variants without proving that the title
    # changed across years.  Count only base keys whose per-year title sets
    # differ, while retaining ``multi_title_base_count`` for the broader
    # variant-allocation audit.
    title_sets_by_year = work.groupby([*BASE_COURSE_KEY, "Year"], dropna=False)["_normalized_title"].agg(
        lambda values: tuple(sorted(set(values)))
    )
    cross_year_change_bases = {
        base_key
        for base_key, values in title_sets_by_year.groupby(level=list(range(len(BASE_COURSE_KEY))))
        if len(set(values.tolist())) > 1
    }
    cross_year_changes = int(len(cross_year_change_bases))
    meta = {
        "source_years": list(years), "source_terms": list(terms),
        "raw_input_rows": int(len(raw)), "raw_rows_in_scope": int(len(work) + special_raw_rows), "included_rows_in_scope": int(len(work)), "course_term_rows": int(len(metrics)),
        "course_keys": int(metrics.loc[:, list(BASE_COURSE_KEY)].drop_duplicates().shape[0]),
        "title_audit_rows": int(len(audit)),
        "title_changed_course_keys": cross_year_changes,
        "collision_base_key_count": int(len(collision_bases)),
        "collision_course_term_count": int(len(collision_pairs)),
        "multi_title_base_count": int(len(multi_title_bases)),
        "variant_count": int(metrics.loc[:, list(COURSE_KEY)].drop_duplicates().shape[0]),
        "special_topic_raw_rows_excluded": special_raw_rows,
        **special_key_counts,
        "cross_year_title_change_base_key_count": cross_year_changes,
        "all_observed_title_change_base_key_count": int(len(multi_title_bases)),
        "stable_course_key": "Subject + Number; course_variant is always base for included ordinary offerings",
        "title_is_display_only": True,
        "title_audit_basis": "All distinct Course Title values from filtered ordinary source rows, grouped by Subject + Number; the representative metric title is not used for this audit.",
        "title_identity_policy": "Course Title is display-only and audited; title edits do not split the stable Subject + Number key. Recognisable Special/Selected Topics rows are excluded before aggregation and retained in a separate audit.",
        "special_topic_rule": SPECIAL_TOPIC_PATTERN.pattern,
        "special_topic_filter_semantics": "Special/Selected Topics rows are excluded; only special-topic-only Subject + Number keys are absent from the ordinary trajectory, while overlapping keys are retained through their ordinary rows.",
        "grade_point_mean_definition": "Estimated mean grade points from A+ through F counts on a 4.0-style scale; not an official student GPA.",
    }
    return metrics, meta


def build_title_audit(metrics: pd.DataFrame, raw: pd.DataFrame | None = None) -> pd.DataFrame:
    """Audit all observed ordinary titles for each stable course key.

    When ``raw`` is supplied, it is restricted to the six-year Spring/Fall
    scope and special-topic rows are removed before titles are collected. This
    preserves same-course-term title variants that are collapsed to one
    representative title in ``metrics``.
    """
    rows = []
    if raw is None:
        source = metrics
        grouping_key = list(COURSE_KEY) if "course_variant" in metrics.columns else list(BASE_COURSE_KEY)
    else:
        _check_frame(raw)
        source = raw.copy()
        source["Year"] = pd.to_numeric(source["Year"], errors="coerce")
        source["Term"] = source["Term"].astype("string").str.strip().str.lower()
        source = source.loc[source["Year"].isin(YEARS) & source["Term"].isin(TERMS)].copy()
        if "Course Title" in source:
            source = source.loc[~source["Course Title"].map(is_special_topic_title)].copy()
        grouping_key = list(BASE_COURSE_KEY)
    include_variant = "course_variant" in metrics.columns
    for key, group in source.groupby(grouping_key, dropna=False, sort=True):
        titles = sorted(set(group["Course Title"].dropna().astype(str)))
        record = {"Subject": key[0], "Number": key[1], "title_count": len(titles), "titles_observed": " | ".join(titles), "title_changed": len(titles) > 1}
        if include_variant:
            record["course_variant"] = "base" if raw is not None else key[2]
        rows.append(record)
    columns = ["Subject", "Number"] + (["course_variant"] if include_variant else []) + ["title_count", "titles_observed", "title_changed"]
    return pd.DataFrame(rows, columns=columns)


def _longest_consecutive(values: Sequence[int]) -> int:
    """Return the longest run of consecutive integer years."""
    ordered = sorted({int(value) for value in values})
    if not ordered:
        return 0
    longest = current = 1
    for left, right in zip(ordered, ordered[1:]):
        current = current + 1 if right == left + 1 else 1
        longest = max(longest, current)
    return longest


def _term_match_mode(group: pd.DataFrame) -> str:
    """Use year-only history unless a course is genuinely one-season."""
    terms = {str(term).strip().lower() for term in group["Term"].dropna()}
    return "same_term" if len(terms) == 1 else "any_term"


def build_course_continuity_diagnostics(
    metrics: pd.DataFrame,
    source_years: Sequence[int] = YEARS,
    source_terms: Sequence[str] = TERMS,
    min_history_years: int = MIN_HISTORY_YEARS,
) -> pd.DataFrame:
    """Describe offering continuity without turning absent offerings into zeroes.

    The unit is the stable Subject + Number key. A missing course-term is
    represented only by a missing observation; no synthetic zero row is created.
    Eligibility follows the matching rule: ordinary courses use any term in a
    prior calendar year, while genuinely one-season courses use that season.
    """
    if "course_variant" not in metrics.columns:
        raise ValueError("metrics must contain course_variant")
    years = tuple(int(year) for year in source_years)
    terms = tuple(str(term).lower() for term in source_terms)
    if not years or not terms:
        raise ValueError("source years and terms must be non-empty")
    rows: list[dict[str, Any]] = []
    grouping = [*BASE_COURSE_KEY]
    for key, group in metrics.groupby(grouping, dropna=False, sort=True):
        subject, number = key
        variant = "base"
        observed = {(int(year), str(term).lower()) for year, term in zip(group["Year"], group["Term"])}
        observed_years = sorted({year for year, _ in observed})
        spring_years = sorted({year for year, term in observed if term == "spring"})
        fall_years = sorted({year for year, term in observed if term == "fall"})
        term_match_mode = _term_match_mode(group)
        expected_count = len(years) * len(terms)
        coverage = len(observed) / expected_count if expected_count else np.nan
        if coverage == 1.0:
            continuity_class = "continuous_both_terms"
        elif spring_years and not fall_years and len(spring_years) == len(years):
            continuity_class = "seasonal_spring"
        elif fall_years and not spring_years and len(fall_years) == len(years):
            continuity_class = "seasonal_fall"
        else:
            continuity_class = "intermittent"
        history = {}
        for target_year in TARGET_YEARS:
            if term_match_mode == "same_term":
                history[str(target_year)] = {
                    term: int(all((target_year - lag, term) in observed for lag in (1, 2, 3)))
                    for term in TERMS
                }
            else:
                history[str(target_year)] = {"any_term": int(all(target_year - lag in observed_years for lag in (1, 2, 3)))}
        backtest_eligible = any(history.get(str(HOLDOUT_YEAR), {}).values())
        training_eligible = any(
            value
            for year in TRAIN_YEARS
            for value in history.get(str(year), {}).values()
        )
        if backtest_eligible:
            excluded_reason = ""
        elif not observed:
            excluded_reason = "no_observed_course_term"
        elif len(observed_years) < min_history_years:
            excluded_reason = "fewer_than_minimum_observed_years"
        elif term_match_mode == "same_term":
            excluded_reason = "seasonal_series_lacks_three_same_term_history"
        else:
            excluded_reason = "ordinary_series_lacks_three_prior_year_history"
        period_labels = [f"{year} {term}" for year, term in sorted(observed)]
        primary_observed = {(year, term) for year, term in observed if year in (2021, 2022, 2023)}
        primary_years = sorted({year for year, _ in primary_observed})
        bridge_2024 = sorted({term for year, term in observed if year == 2024})
        rows.append({
            "Subject": subject, "Number": number, "course_variant": variant,
            "observed_years": ", ".join(map(str, observed_years)),
            "observed_terms": ", ".join(term for term in TERMS if any(t == term for _, t in observed)),
            "observed_periods": " | ".join(period_labels),
            "observed_year_count": len(observed_years),
            "observed_period_count": len(observed),
            "expected_period_count": expected_count,
            "period_coverage": coverage,
            "spring_count": len(spring_years), "fall_count": len(fall_years),
            "spring_years": ", ".join(map(str, spring_years)),
            "fall_years": ", ".join(map(str, fall_years)),
            "max_consecutive_spring_years": _longest_consecutive(spring_years),
            "max_consecutive_fall_years": _longest_consecutive(fall_years),
            "continuity_class": continuity_class,
            "term_match_mode": term_match_mode,
            "primary_2021_2023_observed_year_count": len(primary_years),
            "primary_2021_2023_observed_period_count": len(primary_observed),
            "primary_2021_2023_years": ", ".join(map(str, primary_years)),
            "bridge_2024_terms": ", ".join(bridge_2024),
            "is_seasonal_or_intermittent": continuity_class != "continuous_both_terms",
            "training_eligible": bool(training_eligible),
            "backtest_2024_eligible": bool(backtest_eligible),
            "same_term_history_2022": any(history.get("2022", {}).values()),
            "same_term_history_2023": any(history.get("2023", {}).values()),
            "same_term_history_2024": bool(backtest_eligible),
            "excluded_reason": excluded_reason,
        })
    columns = [
        "Subject", "Number", "course_variant", "observed_years", "observed_terms", "observed_periods",
        "observed_year_count", "observed_period_count", "expected_period_count", "period_coverage",
        "spring_count", "fall_count", "spring_years", "fall_years", "max_consecutive_spring_years",
        "max_consecutive_fall_years", "continuity_class", "term_match_mode",
        "primary_2021_2023_observed_year_count", "primary_2021_2023_observed_period_count",
        "primary_2021_2023_years", "bridge_2024_terms", "is_seasonal_or_intermittent",
        "training_eligible", "backtest_2024_eligible", "same_term_history_2022",
        "same_term_history_2023", "same_term_history_2024", "excluded_reason",
    ]
    return pd.DataFrame(rows, columns=columns)


def build_trajectory_eda(raw: pd.DataFrame, metrics: pd.DataFrame | None = None) -> dict[str, Any]:
    """Create compact, reproducible EDA tables for the six-year source slice."""
    _check_frame(raw)
    work = raw.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    filtered_all = work.loc[work["Year"].isin(YEARS) & work["Term"].isin(TERMS)].copy()
    special_mask = filtered_all["Course Title"].map(is_special_topic_title) if "Course Title" in filtered_all else pd.Series(False, index=filtered_all.index)
    special_key_counts = _special_topic_key_counts(filtered_all, special_mask)
    filtered = filtered_all.loc[~special_mask].copy()
    if metrics is None:
        metrics, _ = aggregate_stable_course_terms(raw)
    numeric_candidates = [column for column in [*GRADE_COLUMNS, "W", "Students"] if column in filtered.columns]
    inventory_rows = []
    for name, frame in (("raw_input", raw), ("six_year_spring_fall_source", filtered_all), ("six_year_spring_fall_analysis", filtered), ("course_term_metrics", metrics)):
        inventory_rows.append({
            "table": name, "rows": int(len(frame)), "columns": int(len(frame.columns)),
            "duplicate_rows": int(frame.duplicated(keep=False).sum()),
            "missing_cells": int(frame.isna().sum().sum()),
            "dtypes": json.dumps({column: str(dtype) for column, dtype in frame.dtypes.items()}, ensure_ascii=False),
        })
    inventory = pd.DataFrame(inventory_rows)
    coverage = filtered.groupby(["Year", "Term"], as_index=False).agg(
        source_rows=("Subject", "size"), source_students=("Students", "sum"), source_w=("W", "sum"),
    )
    metric_coverage = metrics.groupby(["Year", "Term"], as_index=False).agg(
        metric_rows=("Subject", "size"), metric_students=("Students", "sum"), metric_w=("W", "sum"),
    )
    coverage = coverage.merge(metric_coverage, on=["Year", "Term"], how="outer", validate="one_to_one").fillna(0)
    coverage["students_total_difference"] = coverage["source_students"] - coverage["metric_students"]
    coverage["w_total_difference"] = coverage["source_w"] - coverage["metric_w"]
    subject_distribution = filtered.groupby("Subject", as_index=False).agg(
        source_rows=("Subject", "size"), course_numbers=("Number", "nunique"),
        students=("Students", "sum"), W=("W", "sum"),
    ).sort_values("source_rows", ascending=False, kind="mergesort")
    numeric_summary_rows = []
    for column in numeric_candidates:
        values = pd.to_numeric(filtered[column], errors="coerce")
        numeric_summary_rows.append({
            "field": column, "non_null": int(values.notna().sum()), "missing": int(values.isna().sum()),
            "min": values.min(), "median": values.median(), "mean": values.mean(), "max": values.max(),
            "non_numeric_in_scope": int(filtered[column].notna().sum() - values.notna().sum()),
        })
    numeric_summary = pd.DataFrame(numeric_summary_rows)
    source_key = [column for column in ["Year", "Term", "Subject", "Number", "Course Title", "Sched Type", "Primary Instructor"] if column in filtered.columns]
    group_key = ["Year", "Term", "Subject", "Number"]
    group_sizes = filtered.groupby(group_key, dropna=False).size()
    join_audit = pd.DataFrame([{
        "from_table": "six_year_spring_fall", "to_table": "course_term_metrics",
        "source_key_columns": " + ".join(source_key), "target_key_columns": " + ".join(group_key),
        "relationship": "many_to_one", "source_rows": int(len(filtered)),
        "target_rows": int(len(metrics)), "target_key_duplicates": int(metrics.duplicated(group_key, keep=False).sum()),
        "source_groups_with_multiple_rows": int((group_sizes > 1).sum()),
        "join_cardinality_valid": bool(metrics.duplicated(group_key, keep=False).sum() == 0),
    }])
    report = {
        "status": "generated_pending_supervisor_review", "source_years": list(YEARS), "source_terms": list(TERMS),
        "filtered_rows": int(len(filtered)), "filtered_source_rows": int(len(filtered_all)), "filtered_columns": int(len(filtered.columns)),
        "source_grain": "course-term-instructor grade distribution", "metrics_grain": "course-term",
        "filter_before_aggregation": True, "missing_is_not_zero": True,
        "w_semantics": "W means Withdraw and is the count of formal W marks in the final grade distribution; exact withdrawal timing is not in this file.",
        "w_zero_semantics": "W=0 means no W mark was observed in the aggregated final-grade records. It does not by itself prove no earlier drop, adaptation, or sudden difficulty change.",
        "drop_semantics": "Registration/drop events and timestamps are unavailable. W is an observed final-grade mark, not a complete drop-event series.",
        "pass_rate_or_gpa_available": False,
        "pass_rate_or_gpa_fields_found": [column for column in filtered.columns if column.lower() in {"pass", "pass rate", "gpa", "average gpa", "mean gpa"}],
        "estimated_grade_point_mean_available": True,
        "estimated_grade_point_mean_semantics": "Weighted mean of reported A+ through F counts on a 4.0-style scale; not an official student GPA.",
        "special_topic_rows_excluded": int(special_mask.sum()),
        "special_topic_course_terms_with_rows": int(filtered_all.loc[special_mask, ["Year", "Term", "Subject", "Number"]].drop_duplicates().shape[0]),
        **special_key_counts,
        "special_topic_filter_semantics": "Special/Selected Topics rows are excluded; only special-topic-only Subject + Number keys are absent from the ordinary trajectory, while overlapping keys are retained through their ordinary rows.",
        "reconciliation_all_zero": bool((coverage[["students_total_difference", "w_total_difference"]] == 0).all().all()),
        "tables": ["inventory", "year_term_coverage", "subject_distribution", "numeric_summary", "join_audit"],
    }
    return {"report": report, "inventory": inventory, "coverage": coverage, "subject_distribution": subject_distribution, "numeric_summary": numeric_summary, "join_audit": join_audit}


def build_same_term_lags(metrics: pd.DataFrame) -> pd.DataFrame:
    """Add adaptive lag 1--3 calendar years for the stable course key.

    Ordinary courses use the prior year's combined Spring/Fall history. A
    course that appears in only one season uses same-season history. The
    target remains a course-term row, so the current term is still visible in
    the model and in the audit output.
    """
    _check_frame(metrics)
    required = ["demand_proxy", "W_proxy", "w_flag", "course_level", "Course Title", "grade_point_mean"]
    missing = [c for c in required if c not in metrics]
    if missing:
        raise ValueError(f"metrics missing trajectory fields: {missing}")
    result = metrics.copy()
    if "course_variant" not in result.columns:
        result["course_variant"] = "base"
    base = result.loc[:, [*COURSE_KEY, "Term", "Year", "w_flag", "W_proxy", "w_mark_share", "demand_proxy", "Students", "grade_point_mean", "grade_total", "W"]].copy()
    base = base.rename(columns={"W_proxy": "w_proxy", "Students": "students"})
    mode_lookup = (
        result.groupby(list(COURSE_KEY), dropna=False)["Term"].nunique()
        .map(lambda count: "same_term" if int(count) == 1 else "any_term")
        .rename("term_match_mode")
        .reset_index()
    )
    result = result.merge(mode_lookup, on=list(COURSE_KEY), how="left", validate="many_to_one", sort=False)
    for lag in (1, 2, 3):
        fields = ("w_flag", "w_mark_share", "w_proxy", "demand_proxy", "students", "grade_point_mean")
        same_prior = base.loc[:, [*COURSE_KEY, "Term", "Year", *fields]].copy()
        same_prior["Year"] = same_prior["Year"] + lag
        same_prior = same_prior.rename(columns={field: f"lag{lag}_{field}_same" for field in fields})
        result = result.merge(same_prior, on=[*COURSE_KEY, "Term", "Year"], how="left", validate="one_to_one", sort=False)

        yearly = base.copy()
        yearly["grade_points_total"] = yearly["grade_point_mean"] * yearly["grade_total"]
        yearly = (
            yearly.groupby([*COURSE_KEY, "Year"], dropna=False, sort=False)
            .agg(w_flag=("w_flag", "max"), W=("W", "sum"), students=("students", "sum"), demand_proxy=("demand_proxy", "sum"), grade_total=("grade_total", "sum"), grade_points_total=("grade_points_total", "sum"))
            .reset_index()
        )
        yearly["w_mark_share"] = yearly["W"].div(yearly["demand_proxy"].where(yearly["demand_proxy"] > 0))
        yearly["w_proxy"] = yearly["w_mark_share"]
        yearly["grade_point_mean"] = yearly["grade_points_total"].div(yearly["grade_total"].where(yearly["grade_total"] > 0))
        yearly["Year"] = yearly["Year"] + lag
        yearly = yearly.rename(columns={field: f"lag{lag}_{field}_any" for field in fields})
        result = result.merge(yearly.loc[:, [*COURSE_KEY, "Year", *[f"lag{lag}_{field}_any" for field in fields]]], on=[*COURSE_KEY, "Year"], how="left", validate="many_to_one", sort=False)
        for field in fields:
            same_name = f"lag{lag}_{field}_same"
            any_name = f"lag{lag}_{field}_any"
            result[f"lag{lag}_{field}"] = result[any_name].where(result["term_match_mode"].eq("any_term"), result[same_name])
            result.drop(columns=[same_name, any_name], inplace=True)
        result[f"lag{lag}_w_proxy"] = result[f"lag{lag}_w_mark_share"]
    lag_flags = [f"lag{lag}_w_flag" for lag in (1, 2, 3)]
    result["history_year_count"] = result.loc[:, lag_flags].notna().sum(axis=1).astype(int)
    result["has_three_same_term_years"] = result["history_year_count"].eq(3)
    result["lag1_log_demand_proxy"] = np.log1p(result["lag1_demand_proxy"].where(result["lag1_demand_proxy"] >= 0))
    result["eligible_target"] = result["Year"].isin(TARGET_YEARS) & result["has_three_same_term_years"]
    result["split"] = np.where(result["Year"].eq(HOLDOUT_YEAR), "holdout", np.where(result["Year"].isin(TRAIN_YEARS), "train", "lag_initialization"))
    return result


def _preprocessor(train: pd.DataFrame | None = None) -> ColumnTransformer:
    categories = None
    if train is not None:
        categories = []
        for feature in CATEGORICAL_FEATURES:
            counts = train[feature].astype("string").value_counts(dropna=False)
            ordered = sorted(counts.index.tolist(), key=lambda value: (-int(counts.loc[value]), str(value)))
            categories.append([str(value) for value in ordered])
    encoder = OneHotEncoder(categories=categories, drop="first", handle_unknown="ignore") if categories else OneHotEncoder(drop="first", handle_unknown="ignore")
    return ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(NUMERIC_FEATURES)),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", encoder)]), list(CATEGORICAL_FEATURES)),
    ])


def _safe_metric(fn, *args, **kwargs):
    try:
        value = float(fn(*args, **kwargs))
        return value if np.isfinite(value) else None
    except (ValueError, TypeError):
        return None


def metric_row(model: str, split: str, scope: str, y_true: np.ndarray, probability: np.ndarray, prediction: np.ndarray, recall_fraction: float = .20, recall_applicable: bool = True) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=int); p = np.asarray(probability, dtype=float); pred = np.asarray(prediction, dtype=int)
    classes = np.unique(y)
    tie_reason = None
    if not recall_applicable:
        tie_reason = (
            "constant probabilities create arbitrary row ties; metric is intentionally not reported"
            if model == "constant_baseline"
            else "discrete persistence scores create arbitrary row ties; metric is intentionally not reported"
        )
    row = {"model": model, "split": split, "scope": scope, "rows": int(len(y)), "positive_count": int(y.sum()), "negative_count": int((1-y).sum()), "status": "ok" if len(classes) == 2 else "one_class", "average_precision_ap": None, "roc_auc": None, "brier_score": _safe_metric(brier_score_loss, y, p), "precision": _safe_metric(precision_score, y, pred, zero_division=0), "recall": _safe_metric(recall_score, y, pred, zero_division=0), "f1": _safe_metric(f1_score, y, pred, zero_division=0), "balanced_accuracy": _safe_metric(balanced_accuracy_score, y, pred) if len(classes) == 2 else None, "recall_at_20pct": None, "recall_at_20pct_status": "computed" if recall_applicable else "not_applicable_ties", "recall_at_20pct_not_applicable_reason": tie_reason, "recall_at_20pct_rows": int(max(1, np.ceil(len(y)*recall_fraction))), "tn": None, "fp": None, "fn": None, "tp": None}
    if len(classes) == 2:
        row["average_precision_ap"] = _safe_metric(average_precision_score, y, p)
        row["roc_auc"] = _safe_metric(roc_auc_score, y, p)
        row["tn"], row["fp"], row["fn"], row["tp"] = (int(x) for x in confusion_matrix(y, pred, labels=[0, 1]).ravel())
        if recall_applicable:
            order = np.argsort(-p, kind="mergesort")[:row["recall_at_20pct_rows"]]
            row["recall_at_20pct"] = float(y[order].sum() / y.sum()) if y.sum() else None
    return row


def fit_course_trajectory(metrics: pd.DataFrame, metadata: Mapping[str, Any], random_state: int = 42) -> dict[str, Any]:
    work = build_same_term_lags(metrics)
    continuity = build_course_continuity_diagnostics(metrics)
    targets = work.loc[work["eligible_target"]].copy()
    train = targets.loc[targets["Year"].isin(TRAIN_YEARS)].copy()
    holdout = targets.loc[targets["Year"].eq(HOLDOUT_YEAR)].copy()
    if train.empty or holdout.empty:
        raise ValueError("trajectory needs 2022/2023 training rows and 2024 holdout rows")
    y_train = train["w_flag"].astype(int).to_numpy(); y_holdout = holdout["w_flag"].astype(int).to_numpy()
    prevalence = float(y_train.mean())
    predictions = []
    models = {}
    models["constant_baseline"] = (lambda frame, n: np.full(n, prevalence, dtype=float), lambda p: (p >= .5).astype(int))
    persistence_train = train["lag1_w_flag"].fillna(prevalence).astype(float).to_numpy()
    persistence_holdout = holdout["lag1_w_flag"].fillna(prevalence).astype(float).to_numpy()
    for split_name, frame, probs in (("train", train, persistence_train), ("holdout", holdout, persistence_holdout)):
        predictions.extend(_prediction_records("persistence_baseline", split_name, frame, probs, (probs >= .5).astype(int)))
    for split_name, frame, probs in (("train", train, np.full(len(train), prevalence)), ("holdout", holdout, np.full(len(holdout), prevalence))):
        predictions.extend(_prediction_records("constant_baseline", split_name, frame, probs, (probs >= .5).astype(int)))

    if len(np.unique(y_train)) >= 2:
        for name, estimator in (("logistic_regression", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=random_state)), ("random_forest", RandomForestClassifier(n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=random_state, n_jobs=1))):
            pipe = Pipeline([("preprocess", _preprocessor(train)), ("model", estimator)])
            pipe.fit(train.loc[:, list(NUMERIC_FEATURES)+list(CATEGORICAL_FEATURES)], y_train)
            models[name] = pipe
            for split_name, frame, y in (("train", train, y_train), ("holdout", holdout, y_holdout)):
                probs = pipe.predict_proba(frame.loc[:, list(NUMERIC_FEATURES)+list(CATEGORICAL_FEATURES)])[:, 1]
                predictions.extend(_prediction_records(name, split_name, frame, probs, (probs >= .5).astype(int)))
    pred = pd.DataFrame(predictions)
    metrics_rows = []
    for model in MODEL_NAMES:
        for split_name in ("train", "holdout"):
            subset = pred.loc[(pred["model"] == model) & (pred["split"] == split_name)]
            if subset.empty: continue
            for scope in ("all", "spring", "fall"):
                scoped = subset if scope == "all" else subset.loc[subset["Term"].eq(scope)]
                if not scoped.empty:
                    metrics_rows.append(metric_row(model, split_name, scope, scoped["actual_w_flag"], scoped["predicted_probability"], scoped["predicted_w_flag"], recall_applicable=model not in {"constant_baseline", "persistence_baseline"}))
    coefficient_rows = coefficient_table(models.get("logistic_regression"), train)
    coverage = {str(year): {term: {"all_rows": int((work["Year"].eq(year) & work["Term"].eq(term)).sum()), "eligible_rows": int((work["Year"].eq(year) & work["Term"].eq(term) & work["eligible_target"]).sum())} for term in TERMS} for year in TARGET_YEARS}
    continuity_distribution = (
        continuity.groupby("observed_period_count", as_index=False)
        .agg(course_count=("Subject", "size"))
        .sort_values("observed_period_count")
    )
    continuity_distribution["share"] = continuity_distribution["course_count"].div(len(continuity))
    primary_year_distribution = (
        continuity.groupby("primary_2021_2023_observed_year_count", as_index=False)
        .agg(course_count=("Subject", "size"))
        .sort_values("primary_2021_2023_observed_year_count")
    )
    primary_year_distribution["share"] = primary_year_distribution["course_count"].div(len(continuity))
    annual_w = work.groupby(["Year", "Term"], as_index=False).agg(course_term_rows=("w_flag", "size"), w_positive_rows=("w_flag", "sum"), w_proxy_mean=("W_proxy", "mean"), w_total=("W", "sum"))
    report = {"status": "generated_pending_supervisor_review", "extension": "extended_2024_backtest", "source_years": list(YEARS), "lag_initialization_years": [2019, 2020, 2021], "training_target_years": list(TRAIN_YEARS), "holdout_year": HOLDOUT_YEAR, "target_definition": "w_flag = 1 when W > 0; W is the observed Withdraw mark count, not an official withdrawal-rate label", "same_course_same_term_lags": False, "adaptive_term_matching": True, "course_identity": "Subject + Number; Course Title is display-only and course_variant is always base", "required_history": {"2022": [2019, 2020, 2021], "2023": [2020, 2021, 2022], "2024": [2021, 2022, 2023]}, "minimum_history_years": MIN_HISTORY_YEARS, "current_2024_outcome_values_used_as_features": False, "current_2024_feature_isolation_note": "2024 W, Students, grade counts, W mark share, and demand proxy are truth/output values only; 2024 model features use prior-year history plus course level, Subject, and current Term. Historical grade_point_mean is an estimate from grade counts, not an official GPA.", "training_rows": int(len(train)), "holdout_rows": int(len(holdout)), "coverage_by_target_year_term": coverage, "excluded_for_incomplete_history": int(work["Year"].isin(TARGET_YEARS).sum() - work["eligible_target"].sum()), "continuity_rows": int(len(continuity)), "continuity_class_counts": {str(key): int(value) for key, value in continuity["continuity_class"].value_counts().items()}, "continuity_observed_period_distribution": json.loads(continuity_distribution.to_json(orient="records")), "continuity_primary_2021_2023_year_distribution": json.loads(primary_year_distribution.to_json(orient="records")), "backtest_eligible_course_count": int(continuity["backtest_2024_eligible"].sum()), "excluded_course_count": int((~continuity["backtest_2024_eligible"]).sum()), "w_year_term_summary": json.loads(annual_w.to_json(orient="records")), "baseline_recall_at_20pct_policy": "not_applicable for constant/persistence because tied or discrete scores make row-level top-20% selection arbitrary", "model_names": list(MODEL_NAMES), "prediction_error": "predicted_probability - actual_w_flag; absolute_prediction_error is its absolute value", "uncertainty_interval_status": "not calculated because this is binary screening, not a calibrated interval forecast", "model_matrix": list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES), "metrics_definition": {"average_precision_ap": "average_precision_score; displayed as Average Precision (AP), not PR-AUC", "brier_score": "mean squared probability error; lower is better, not accuracy", "recall_at_20pct": "fraction of actual positives in top 20% by probability"}, "metrics_2024": [row for row in metrics_rows if row["split"] == "holdout"], "metadata": dict(metadata)}
    report["prediction_unique_key"] = "Year + Term + Subject + Number + course_variant + model"
    report["title_variant_limitation"] = "Course Title is not used as identity; title changes are audited under Subject + Number. Recognisable rotating special-topic rows are excluded before aggregation."
    report["w_semantics"] = "W means Withdraw and is counted from final grade records; W=0 means no W mark was observed, not proof of no earlier drop or adaptation."
    report["gpa_semantics"] = "No numeric GPA field exists. The generated grade_point_mean is an estimated 4.0-style weighted mean from A+ through F counts and should not be called official GPA."
    return {"trajectory": work, "predictions": pred, "metrics": pd.DataFrame(metrics_rows), "coefficients": coefficient_rows, "continuity": continuity, "report": report, "models": models}


def _prediction_records(model: str, split: str, frame: pd.DataFrame, probabilities: np.ndarray, labels: np.ndarray) -> list[dict[str, Any]]:
    out = frame.loc[:, ["Year", "Term", "Subject", "Number", "course_variant", "Course Title", "W", "Students", "grade_point_mean", "W_proxy", "w_mark_share", "demand_proxy", "w_flag", "term_match_mode"]].copy()
    for column in ("instructor_count", "instructors_observed"):
        if column in frame:
            out[column] = frame[column]
    out["model"] = model; out["split"] = split; out["predicted_probability"] = probabilities; out["predicted_w_flag"] = labels; out = out.rename(columns={"w_flag": "actual_w_flag"})
    out["prediction_error"] = out["predicted_probability"] - out["actual_w_flag"]
    out["absolute_prediction_error"] = out["prediction_error"].abs()
    out["uncertainty_interval_status"] = "not_calculated_for_binary_screening"
    return out.to_dict("records")


def coefficient_table(model: Pipeline | None, train: pd.DataFrame | None = None) -> pd.DataFrame:
    columns = ["feature", "coefficient", "abs_coefficient", "odds_ratio", "direction", "feature_type", "reference_category", "sample_support", "reference_support", "support_threshold", "low_support_warning"]
    if model is None: return pd.DataFrame(columns=columns)
    pre = model.named_steps["preprocess"]; estimator = model.named_steps["model"]
    names = pre.get_feature_names_out(); coefs = estimator.coef_[0]
    encoder = pre.named_transformers_["categorical"].named_steps["onehot"]
    categories = encoder.categories_
    drop_indices = encoder.drop_idx_
    refs = {feature: str(values[int(drop_indices[index])]) for index, (feature, values) in enumerate(zip(CATEGORICAL_FEATURES, categories)) if drop_indices[index] is not None}
    rows = []
    for name, coef in zip(names, coefs):
        clean = name.split("__", 1)[-1]; kind = "categorical" if clean.startswith("Subject_") or clean.startswith("Term_") else "numeric"
        parent = "Subject" if clean.startswith("Subject_") else "Term" if clean.startswith("Term_") else ""
        ref = refs.get(parent, "")
        value = clean.split("_", 1)[1] if parent else None
        support = int(train[clean].notna().sum()) if train is not None and kind == "numeric" and clean in train else (int(train[parent].eq(value).sum()) if train is not None and parent and value is not None else None)
        ref_support = int(train[parent].eq(ref).sum()) if train is not None and parent else None
        rows.append({"feature": clean, "coefficient": float(coef), "abs_coefficient": float(abs(coef)), "odds_ratio": float(np.exp(np.clip(coef, -50, 50))), "direction": "higher odds" if coef > 0 else "lower odds" if coef < 0 else "neutral", "feature_type": kind, "reference_category": ref, "sample_support": support, "reference_support": ref_support, "support_threshold": 20 if kind == "categorical" else None, "low_support_warning": bool(kind == "categorical" and support is not None and support < 20)})
    return pd.DataFrame(rows, columns=columns).sort_values("abs_coefficient", ascending=False, kind="mergesort").reset_index(drop=True)


def write_course_trajectory_outputs(outputs: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
    target = Path(output_dir); target.mkdir(parents=True, exist_ok=True)
    paths = {"trajectory": target / f"{OUTPUT_PREFIX}table.csv", "predictions": target / f"{OUTPUT_PREFIX}predictions.csv", "metrics": target / f"{OUTPUT_PREFIX}metrics.csv", "coefficients": target / f"{OUTPUT_PREFIX}logistic_coefficients.csv", "title_audit": target / f"{OUTPUT_PREFIX}title_audit.csv", "continuity": target / f"{OUTPUT_PREFIX}continuity.csv", "special_topic_audit": target / f"{OUTPUT_PREFIX}special_topic_audit.csv", "instructor_audit": target / f"{OUTPUT_PREFIX}instructor_audit.csv", "eda_report": target / f"{OUTPUT_PREFIX}eda_report.json", "eda_inventory": target / f"{OUTPUT_PREFIX}eda_inventory.csv", "eda_coverage": target / f"{OUTPUT_PREFIX}eda_year_term_coverage.csv", "eda_subject_distribution": target / f"{OUTPUT_PREFIX}eda_subject_distribution.csv", "eda_numeric_summary": target / f"{OUTPUT_PREFIX}eda_numeric_summary.csv", "eda_join_audit": target / f"{OUTPUT_PREFIX}eda_join_audit.csv", "report": target / f"{OUTPUT_PREFIX}report.json"}
    title_audit = outputs.get("title_audit")
    if title_audit is None:
        raise KeyError("outputs must include the raw-source title_audit table")
    outputs["trajectory"].to_csv(paths["trajectory"], index=False); outputs["predictions"].to_csv(paths["predictions"], index=False); outputs["metrics"].to_csv(paths["metrics"], index=False); outputs["coefficients"].to_csv(paths["coefficients"], index=False); title_audit.to_csv(paths["title_audit"], index=False); outputs["continuity"].to_csv(paths["continuity"], index=False)
    outputs.get("special_topic_audit", pd.DataFrame()).to_csv(paths["special_topic_audit"], index=False)
    outputs.get("instructor_audit", pd.DataFrame()).to_csv(paths["instructor_audit"], index=False)
    eda = outputs.get("eda")
    if eda:
        eda["report"] and paths["eda_report"].write_text(json.dumps(eda["report"], indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        eda["inventory"].to_csv(paths["eda_inventory"], index=False); eda["coverage"].to_csv(paths["eda_coverage"], index=False); eda["subject_distribution"].to_csv(paths["eda_subject_distribution"], index=False); eda["numeric_summary"].to_csv(paths["eda_numeric_summary"], index=False); eda["join_audit"].to_csv(paths["eda_join_audit"], index=False)
    paths["report"].write_text(json.dumps(outputs["report"], indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return paths


def build_course_trajectory_outputs(raw: pd.DataFrame) -> dict[str, Any]:
    metrics, metadata = aggregate_stable_course_terms(raw)
    instructor_audit = build_instructor_audit(raw)
    if not instructor_audit.empty:
        metrics = metrics.merge(instructor_audit.drop(columns=["source_rows"]), on=["Year", "Term", "Subject", "Number"], how="left", validate="one_to_one", sort=False)
    outputs = fit_course_trajectory(metrics, metadata)
    outputs["special_topic_audit"] = build_special_topic_audit(raw)
    outputs["title_audit"] = build_title_audit(metrics, raw=raw)
    outputs["instructor_audit"] = instructor_audit
    outputs["eda"] = build_trajectory_eda(raw, metrics)
    outputs["metadata"] = metadata
    outputs["report"]["special_topic_audit_rows"] = int(len(outputs["special_topic_audit"]))
    outputs["report"]["instructor_audit_rows"] = int(len(instructor_audit))
    outputs["report"]["instructor_missing_source_rows_in_scope"] = int(raw.loc[raw["Year"].isin(YEARS) & raw["Term"].astype(str).str.lower().isin(TERMS), "Primary Instructor"].isna().sum()) if "Primary Instructor" in raw.columns else None
    return outputs
