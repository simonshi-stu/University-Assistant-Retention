"""Phase 5 demand and W-based withdrawal-proxy analysis.

The accepted input is the normalized UIUC GPA table at course-term grain.
Demand is represented by ``Students + W`` because the source documents
``Students`` as excluding W.  The W-based proxy is recomputed from the
aggregated counts as ``W / (Students + W)`` and is never presented as an
official withdrawal or drop rate.

This module is deterministic and has no runtime LLM or network dependency.
It deliberately does not infer sections, registrations, attendance, or
student-level outcomes from the GPA source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from .config import DATA_PROCESSED_DIR, PRIMARY_TERMS, validate_window
from .normalization import GROUP_KEYS


COURSE_KEYS = ("Subject", "Number", "Course Title")
COUNT_COLUMNS = ("Students", "W")
DEFAULT_WINDOW = (2021, 2022, 2023)
DEFAULT_TERMS = ("spring", "fall")
DEFAULT_HIGH_DEMAND_QUANTILE = 0.75
DEFAULT_MIN_DEMAND_PROXY = 20

COURSE_TERM_OUTPUT = "course_term_demand_metrics.csv"
COURSE_SUMMARY_OUTPUT = "course_demand_summary.csv"
REPORT_OUTPUT = "phase5_report.json"


def _validate_window(window: Sequence[int]) -> tuple[int, int, int]:
    if not isinstance(window, tuple) or len(window) != 3:
        raise TypeError("window must be a tuple of three years")
    for year in window:
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError("window years must be integers")
    validate_window(window)
    return window


def _validate_terms(terms: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(terms, tuple) or not terms:
        raise TypeError("terms must be a non-empty tuple")
    normalized = tuple(term.strip().lower() if isinstance(term, str) else term for term in terms)
    if any(not isinstance(term, str) for term in normalized):
        raise TypeError("terms must contain strings")
    if any(term not in PRIMARY_TERMS for term in normalized):
        raise ValueError("terms must be spring or fall")
    if len(set(normalized)) != len(normalized):
        raise ValueError("terms must not contain duplicates")
    return normalized


def _check_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")


def _validate_quantile(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("high_demand_quantile must be numeric")
    value = float(value)
    if not 0 < value < 1:
        raise ValueError("high_demand_quantile must be between 0 and 1")
    return value


def _validate_min_demand(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("min_demand_proxy must be a non-negative integer")
    if value < 0:
        raise ValueError("min_demand_proxy must be non-negative")
    return value


def _numeric_counts(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    students = pd.to_numeric(frame["Students"], errors="coerce")
    withdrawals = pd.to_numeric(frame["W"], errors="coerce")
    return students, withdrawals


def _build_proxy_columns(
    frame: pd.DataFrame,
    high_demand_quantile: float,
    min_demand_proxy: int,
) -> tuple[pd.DataFrame, float, dict[str, int]]:
    """Add demand/proxy/rank fields to a course-term table without mutation."""
    work = frame.copy()
    students, withdrawals = _numeric_counts(work)

    nonnegative = (students >= 0) & (withdrawals >= 0)
    valid_counts = students.notna() & withdrawals.notna() & nonnegative

    demand = pd.Series(pd.NA, index=work.index, dtype="Float64")
    demand.loc[valid_counts] = students.loc[valid_counts] + withdrawals.loc[valid_counts]
    work["Students"] = students
    work["W"] = withdrawals
    work["demand_proxy"] = demand

    w_proxy = pd.Series(pd.NA, index=work.index, dtype="Float64")
    valid_proxy = valid_counts & demand.gt(0)
    w_proxy.loc[valid_proxy] = withdrawals.loc[valid_proxy] / demand.loc[valid_proxy]
    work["W_proxy"] = w_proxy

    demand_values = demand.dropna()
    if demand_values.empty:
        raise ValueError("no valid Students and W counts remain after filtering")
    threshold = float(demand_values.quantile(high_demand_quantile))
    work["is_high_demand"] = (demand.ge(threshold) & demand.notna()).astype(bool)

    demand_rank = demand.rank(method="min", ascending=False)
    work["demand_rank"] = demand_rank.round().astype("Int64")
    rankable = valid_proxy & demand.ge(min_demand_proxy)
    work["w_proxy_rankable"] = rankable.astype(bool)
    w_rank = w_proxy.where(rankable).rank(method="min", ascending=False)
    work["w_proxy_rank"] = w_rank.round().astype("Int64")

    quality = {
        "rows_with_missing_or_negative_counts": int((~valid_counts).sum()),
        "rows_with_valid_demand_proxy": int(demand.notna().sum()),
        "rows_with_valid_w_proxy": int(w_proxy.notna().sum()),
        "rows_rankable_for_w_proxy": int(rankable.sum()),
    }
    return work, threshold, quality


def _sort_course_terms(frame: pd.DataFrame, terms: tuple[str, ...]) -> pd.DataFrame:
    work = frame.copy()
    work["_term_order"] = pd.Categorical(work["Term"], categories=list(terms), ordered=True)
    sort_columns = ["Year", "_term_order", "Subject", "Number", "Course Title"]
    work = work.sort_values(sort_columns, kind="mergesort", na_position="last")
    return work.drop(columns=["_term_order"]).reset_index(drop=True)


def build_course_term_demand_metrics(
    metrics: pd.DataFrame,
    window: tuple[int, int, int] = DEFAULT_WINDOW,
    terms: tuple[str, ...] = DEFAULT_TERMS,
    high_demand_quantile: float = DEFAULT_HIGH_DEMAND_QUANTILE,
    min_demand_proxy: int = DEFAULT_MIN_DEMAND_PROXY,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create the traceable course-term Phase 5 table.

    The input is filtered again by the approved window and terms before any
    Phase 5 ranking or summary is calculated.  Duplicate course-term keys are
    rejected because the accepted normalized table is already aggregated.
    """
    window = _validate_window(window)
    terms = _validate_terms(terms)
    high_demand_quantile = _validate_quantile(high_demand_quantile)
    min_demand_proxy = _validate_min_demand(min_demand_proxy)
    if not isinstance(metrics, pd.DataFrame):
        raise TypeError("metrics must be a pandas DataFrame")
    _check_columns(metrics, list(GROUP_KEYS) + list(COUNT_COLUMNS))

    work = metrics.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    work = work[work["Year"].isin(window) & work["Term"].isin(terms)].copy()
    if work.empty:
        raise ValueError("no course-term rows remain in the selected window and terms")
    if work.duplicated(subset=list(GROUP_KEYS)).any():
        raise ValueError("metrics must have unique course-term GROUP_KEYS")

    work, threshold, quality = _build_proxy_columns(
        work, high_demand_quantile, min_demand_proxy
    )
    work = _sort_course_terms(work, terms)

    # Keep the accepted metric columns first and append the Phase 5 fields in
    # a stable order. Existing W_proxy is deliberately overwritten above.
    phase5_columns = [
        "demand_proxy", "is_high_demand", "demand_rank", "w_proxy_rankable", "w_proxy_rank",
    ]
    columns = list(metrics.columns)
    if "W_proxy" not in columns:
        columns.append("W_proxy")
    columns.extend(column for column in phase5_columns if column not in columns)
    columns = [column for column in columns if column in work.columns]
    output = work[columns].copy()
    metadata = {
        "window": list(window),
        "terms": list(terms),
        "high_demand_quantile": high_demand_quantile,
        "high_demand_threshold": threshold,
        "min_demand_proxy_for_w_ranking": min_demand_proxy,
        **quality,
    }
    return output, metadata


def _sum_min_count(series: pd.Series) -> float | int | None:
    result = series.sum(min_count=1)
    return None if pd.isna(result) else result


def _mean_or_na(series: pd.Series) -> float | None:
    result = series.mean()
    return None if pd.isna(result) else float(result)


def build_course_demand_summary(
    course_terms: pd.DataFrame,
    min_demand_proxy: int = DEFAULT_MIN_DEMAND_PROXY,
) -> pd.DataFrame:
    """Aggregate the course-term table into a course-level demand summary."""
    min_demand_proxy = _validate_min_demand(min_demand_proxy)
    if not isinstance(course_terms, pd.DataFrame):
        raise TypeError("course_terms must be a pandas DataFrame")
    _check_columns(
        course_terms,
        list(COURSE_KEYS)
        + ["Year", "Term", "Students", "W", "demand_proxy", "W_proxy", "is_high_demand"],
    )
    if course_terms.empty:
        raise ValueError("course_terms must be non-empty")

    work = course_terms.copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Students"] = pd.to_numeric(work["Students"], errors="coerce")
    work["W"] = pd.to_numeric(work["W"], errors="coerce")
    work["demand_proxy"] = pd.to_numeric(work["demand_proxy"], errors="coerce")
    work["W_proxy"] = pd.to_numeric(work["W_proxy"], errors="coerce")
    work["is_high_demand"] = work["is_high_demand"].astype(bool)
    work["_w_valid_for_demand"] = work["W"].where(work["demand_proxy"].notna())

    grouped = work.groupby(list(COURSE_KEYS), dropna=False, sort=True)
    summary = grouped.agg(
        course_term_count=("Year", "size"),
        year_count=("Year", "nunique"),
        term_count=("Term", "nunique"),
        first_year=("Year", "min"),
        last_year=("Year", "max"),
        students_total=("Students", _sum_min_count),
        w_total=("W", _sum_min_count),
        demand_proxy_total=("demand_proxy", _sum_min_count),
        demand_proxy_mean=("demand_proxy", _mean_or_na),
        demand_proxy_median=("demand_proxy", "median"),
        demand_proxy_max=("demand_proxy", "max"),
        w_proxy_course_term_mean=("W_proxy", _mean_or_na),
        w_proxy_course_term_max=("W_proxy", "max"),
        demand_valid_term_count=("demand_proxy", "count"),
        high_demand_term_count=("is_high_demand", "sum"),
        w_valid_total=("_w_valid_for_demand", _sum_min_count),
    ).reset_index()

    years_observed = (
        grouped["Year"]
        .agg(lambda values: ",".join(str(int(year)) for year in sorted(values.dropna().unique())))
        .rename("years_observed")
        .reset_index()
    )
    summary = summary.merge(years_observed, on=list(COURSE_KEYS), how="left", validate="one_to_one")

    high_years = (
        work.loc[work["is_high_demand"]]
        .groupby(list(COURSE_KEYS), dropna=False)["Year"]
        .nunique()
        .rename("high_demand_year_count")
        .reset_index()
    )
    summary = summary.merge(high_years, on=list(COURSE_KEYS), how="left", validate="one_to_one")
    summary["high_demand_year_count"] = summary["high_demand_year_count"].fillna(0).astype(int)

    valid_weighted = summary["demand_proxy_total"].notna() & summary["w_valid_total"].notna()
    valid_weighted &= summary["demand_proxy_total"] > 0
    summary["w_proxy_weighted"] = pd.Series(pd.NA, index=summary.index, dtype="Float64")
    summary.loc[valid_weighted, "w_proxy_weighted"] = (
        summary.loc[valid_weighted, "w_valid_total"]
        / summary.loc[valid_weighted, "demand_proxy_total"]
    )
    valid_share = summary["demand_valid_term_count"] > 0
    summary["high_demand_share"] = pd.Series(pd.NA, index=summary.index, dtype="Float64")
    summary.loc[valid_share, "high_demand_share"] = (
        summary.loc[valid_share, "high_demand_term_count"]
        / summary.loc[valid_share, "demand_valid_term_count"]
    )

    summary["demand_total_rank"] = summary["demand_proxy_total"].rank(
        method="min", ascending=False
    ).round().astype("Int64")
    summary["demand_mean_rank"] = summary["demand_proxy_mean"].rank(
        method="min", ascending=False
    ).round().astype("Int64")
    rankable = valid_weighted & summary["demand_proxy_total"].ge(min_demand_proxy)
    summary["w_proxy_rankable"] = rankable.astype(bool)
    summary["w_proxy_weighted_rank"] = summary["w_proxy_weighted"].where(rankable).rank(
        method="min", ascending=False
    ).round().astype("Int64")

    summary = summary.drop(columns=["w_valid_total"])
    ordered = list(COURSE_KEYS) + [
        "course_term_count", "year_count", "term_count", "years_observed", "first_year", "last_year",
        "students_total", "w_total", "demand_proxy_total", "demand_proxy_mean",
        "demand_proxy_median", "demand_proxy_max", "w_proxy_weighted",
        "w_proxy_course_term_mean", "w_proxy_course_term_max", "demand_valid_term_count",
        "high_demand_term_count", "high_demand_year_count", "high_demand_share",
        "demand_total_rank", "demand_mean_rank", "w_proxy_rankable", "w_proxy_weighted_rank",
    ]
    summary = summary[ordered]
    return summary.sort_values(
        ["demand_total_rank", "Subject", "Number", "Course Title"],
        kind="mergesort", na_position="last",
    ).reset_index(drop=True)


def _records(frame: pd.DataFrame, columns: Sequence[str], limit: int = 10) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return json.loads(frame.loc[:, list(columns)].head(limit).to_json(orient="records"))


def build_phase5_report(
    course_terms: pd.DataFrame,
    course_summary: pd.DataFrame,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a JSON-serializable audit report with traceable top rankings."""
    _check_columns(course_terms, list(GROUP_KEYS) + ["demand_proxy", "W_proxy"])
    _check_columns(course_summary, list(COURSE_KEYS) + ["demand_proxy_total", "w_proxy_weighted"])

    coverage = (
        course_terms.groupby(["Year", "Term"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .sort_values(["Year", "Term"])
    )
    top_columns = [
        "Year", "Term", "Subject", "Number", "Course Title", "Students", "W", "demand_proxy", "W_proxy",
    ]
    w_ranked = course_terms.loc[course_terms["w_proxy_rankable"]].sort_values(
        ["W_proxy", "demand_proxy", "Subject", "Number"],
        ascending=[False, True, True, True],
        kind="mergesort",
    )
    course_ranked = course_summary.sort_values(
        ["demand_proxy_total", "demand_proxy_mean", "Subject", "Number"],
        ascending=[False, False, True, True],
        kind="mergesort",
    )
    report = {
        "analysis": "Phase 5 — UIUC demand and W-based withdrawal proxy",
        "status": "complete",
        "window": metadata["window"],
        "terms": metadata["terms"],
        "source_grain": "course-term-instructor grade distribution",
        "input_metric_grain": "course-term",
        "output_grains": {"course_terms": "course-term", "course_summary": "course"},
        "source_has_section_id": False,
        "source_has_student_id": False,
        "source_has_attendance": False,
        "formulae": {
            "demand_proxy": "Students + W",
            "w_proxy": "W / (Students + W), only when both counts are non-negative and denominator > 0",
            "weighted_course_w_proxy": "sum(W over valid demand rows) / sum(demand_proxy over valid demand rows)",
        },
        "filtering": {
            "applied_before_analysis": True,
            "window": metadata["window"],
            "terms": metadata["terms"],
        },
        "row_counts": {
            "course_term_rows": int(len(course_terms)),
            "course_rows": int(len(course_summary)),
            "subject_rows": int(course_summary["Subject"].nunique(dropna=False)),
            "valid_demand_rows": int(course_terms["demand_proxy"].notna().sum()),
            "valid_w_proxy_rows": int(course_terms["W_proxy"].notna().sum()),
        },
        "coverage_by_year_term": json.loads(coverage.to_json(orient="records")),
        "ranking_parameters": {
            "high_demand_quantile": metadata["high_demand_quantile"],
            "high_demand_threshold": metadata["high_demand_threshold"],
            "min_demand_proxy_for_w_ranking": metadata["min_demand_proxy_for_w_ranking"],
        },
        "top_course_terms_by_demand": _records(course_terms.sort_values(
            ["demand_proxy", "Year", "Term", "Subject", "Number"],
            ascending=[False, True, True, True, True], kind="mergesort"), top_columns),
        "top_course_terms_by_w_proxy": _records(w_ranked, top_columns),
        "top_courses_by_total_demand": _records(course_ranked, [
            "Subject", "Number", "Course Title", "course_term_count", "year_count",
            "demand_proxy_total", "demand_proxy_mean", "w_proxy_weighted",
            "high_demand_year_count",
        ]),
        "limitations": [
            "Demand proxy is Students + W in the source GPA table, not registration or enrollment-event counts.",
            "W_proxy is not an official withdrawal rate and cannot identify when or why a student withdrew.",
            "The source has no section id, student id, capacity, waitlist, attendance, or causal-treatment fields.",
            "Course summary totals are aggregates across source instructor-grain rows at course-term grain.",
            "W-proxy rankings use a minimum demand-proxy screen; small denominators remain less stable.",
            "Results describe associations and distributions; they do not establish causal retention effects.",
        ],
    }
    return report


def build_phase5_outputs(
    metrics: pd.DataFrame,
    window: tuple[int, int, int] = DEFAULT_WINDOW,
    terms: tuple[str, ...] = DEFAULT_TERMS,
    high_demand_quantile: float = DEFAULT_HIGH_DEMAND_QUANTILE,
    min_demand_proxy: int = DEFAULT_MIN_DEMAND_PROXY,
) -> dict[str, Any]:
    """Build both Phase 5 tables and the report in memory."""
    course_terms, metadata = build_course_term_demand_metrics(
        metrics,
        window=window,
        terms=terms,
        high_demand_quantile=high_demand_quantile,
        min_demand_proxy=min_demand_proxy,
    )
    course_summary = build_course_demand_summary(
        course_terms, min_demand_proxy=min_demand_proxy
    )
    report = build_phase5_report(course_terms, course_summary, metadata)
    return {"course_terms": course_terms, "course_summary": course_summary, "report": report}


def write_phase5_outputs(outputs: Mapping[str, Any], output_dir=None) -> dict[str, Path]:
    """Write deterministic Phase 5 CSV and JSON artifacts."""
    target_dir = Path(output_dir) if output_dir is not None else Path(DATA_PROCESSED_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    course_terms_path = target_dir / COURSE_TERM_OUTPUT
    course_summary_path = target_dir / COURSE_SUMMARY_OUTPUT
    report_path = target_dir / REPORT_OUTPUT

    outputs["course_terms"].to_csv(course_terms_path, index=False)
    outputs["course_summary"].to_csv(course_summary_path, index=False)
    report_path.write_text(
        json.dumps(outputs["report"], indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "course_terms": course_terms_path,
        "course_summary": course_summary_path,
        "report": report_path,
    }
