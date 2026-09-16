"""Phase 6: time-aware high-W-risk modelling and course profiles.

The predictive unit is a UIUC GPA course-term row.  The target is a binary
high-W-risk flag derived from ``W_proxy`` using a threshold computed from the
training years only.  Current-row W, W_proxy, demand_proxy, and rank/label
fields are deliberately excluded from predictive features.  Historical
course aggregates are built from strictly earlier years in the selected
window.  This module is deterministic and has no runtime LLM or network
dependency.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    silhouette_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier

from .config import DATA_PROCESSED_DIR, PRIMARY_TERMS, validate_window, window_train_holdout


DEFAULT_WINDOW = (2021, 2022, 2023)
DEFAULT_TERMS = ("spring", "fall")
DEFAULT_HIGH_RISK_QUANTILE = 0.75
DEFAULT_RANDOM_STATE = 42
DEFAULT_RECALL_AT_K = 0.20
DEFAULT_PROFILE_MIN_ROWS = 12
DEFAULT_PROFILE_MAX_K = 5
DEFAULT_PROFILE_MIN_SILHOUETTE = 0.05

COURSE_KEYS = ("Subject", "Number", "Course Title")
REQUIRED_COLUMNS = COURSE_KEYS + ("Year", "Term", "Students", "W", "W_proxy", "demand_proxy")
GRADE_SHARE_COLUMNS = tuple(
    f"share_{grade}"
    for grade in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F")
)
GRADE_COUNT_COLUMNS = tuple(
    grade for grade in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F")
)
HISTORICAL_GRADE_SHARE_COLUMNS = tuple(f"historical_{column}" for column in GRADE_SHARE_COLUMNS)
LEAKAGE_COLUMNS = frozenset(
    {
        "W",
        "W_proxy",
        "demand_proxy",
        "is_high_demand",
        "demand_rank",
        "w_proxy_rankable",
        "w_proxy_rank",
        "high_w_risk",
        "target",
        "split",
        "row_id",
    }
)

FEATURE_TABLE_OUTPUT = "phase6_feature_table.csv"
MODEL_METRICS_OUTPUT = "phase6_model_metrics.csv"
PREDICTIONS_OUTPUT = "phase6_predictions.csv"
COURSE_PROFILES_OUTPUT = "phase6_course_profiles.csv"
FEATURE_IMPORTANCE_OUTPUT = "phase6_feature_importance.csv"
REPORT_OUTPUT = "phase6_report.json"


def _validate_window(window: Sequence[int]) -> tuple[int, int, int]:
    if not isinstance(window, tuple) or len(window) != 3:
        raise TypeError("window must be a tuple of three years")
    if any(isinstance(year, bool) or not isinstance(year, int) for year in window):
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


def _numeric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _course_level(number: Any) -> float:
    """Parse a catalog number into a broad 100/200/... course-level band."""
    value = _numeric(number)
    if value is None or value < 0:
        return np.nan
    return float(min(900, max(0, int(value) // 100 * 100)))


def _safe_json(value: Any) -> Any:
    if isinstance(value, (np.integer,)):  # pragma: no cover - tiny serializer helper
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (dict, list, tuple)):
        return value
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and missing:
        return None
    return value


def _derive_grade_shares(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    counts = []
    for column in GRADE_COUNT_COLUMNS:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
            counts.append(column)
    if "grade_total" in work.columns:
        work["grade_total"] = pd.to_numeric(work["grade_total"], errors="coerce")
    elif counts:
        work["grade_total"] = work.loc[:, counts].sum(axis=1, min_count=1)
    else:
        work["grade_total"] = np.nan

    total = pd.to_numeric(work["grade_total"], errors="coerce")
    for share, grade in zip(GRADE_SHARE_COLUMNS, GRADE_COUNT_COLUMNS):
        if share in work.columns:
            work[share] = pd.to_numeric(work[share], errors="coerce")
        elif grade in work.columns:
            count = pd.to_numeric(work[grade], errors="coerce")
            work[share] = count.div(total.where(total.gt(0)))
        else:
            work[share] = np.nan
    return work


def _add_historical_features(work: pd.DataFrame) -> pd.DataFrame:
    """Add course aggregates calculated only from years before each row."""
    result = work.copy()
    history = work.loc[:, list(COURSE_KEYS) + ["Year", "Term", "W_proxy", "demand_proxy", "Students", "grade_total", *GRADE_SHARE_COLUMNS]].copy()
    for column in ("W_proxy", "demand_proxy", "Students", "grade_total"):
        history[column] = pd.to_numeric(history[column], errors="coerce")
    annual_aggregations: dict[str, tuple[str, str]] = {
        "historical_w_proxy_year": ("W_proxy", "mean"),
        "historical_demand_year": ("demand_proxy", "mean"),
        "historical_students_year": ("Students", "mean"),
        "historical_grade_total_year": ("grade_total", "mean"),
        "historical_term_count": ("Term", "nunique"),
    }
    annual_aggregations.update({f"historical_{column}_year": (column, "mean") for column in GRADE_SHARE_COLUMNS})
    annual = history.groupby(list(COURSE_KEYS) + ["Year"], dropna=False, sort=True).agg(**annual_aggregations).reset_index()

    feature_names = [
        "historical_w_proxy_mean",
        "historical_demand_proxy_mean",
        "historical_students_mean",
        "historical_grade_total_mean",
        "historical_term_count",
        *HISTORICAL_GRADE_SHARE_COLUMNS,
    ]
    for name in feature_names:
        result[name] = np.nan

    for year in sorted(result["Year"].dropna().unique()):
        prior = annual.loc[annual["Year"] < year]
        if prior.empty:
            continue
        prior_summary = (
            prior.groupby(list(COURSE_KEYS), dropna=False, sort=True)
            .agg(
                historical_w_proxy_mean=("historical_w_proxy_year", "mean"),
                historical_demand_proxy_mean=("historical_demand_year", "mean"),
                historical_students_mean=("historical_students_year", "mean"),
                historical_grade_total_mean=("historical_grade_total_year", "mean"),
                historical_term_count=("historical_term_count", "sum"),
                **{f"historical_{column}": (f"historical_{column}_year", "mean") for column in GRADE_SHARE_COLUMNS},
            )
            .reset_index()
        )
        mask = result["Year"].eq(year)
        current_keys = result.loc[mask, list(COURSE_KEYS)].copy()
        current_keys["_phase6_index"] = current_keys.index
        joined = current_keys.merge(
            prior_summary,
            on=list(COURSE_KEYS),
            how="left",
            sort=False,
            validate="many_to_one",
        )
        if not joined["_phase6_index"].tolist() == current_keys["_phase6_index"].tolist():
            raise AssertionError("historical feature join changed current row order")
        joined = joined.set_index("_phase6_index").reindex(current_keys["_phase6_index"])
        result.loc[mask, feature_names] = joined.loc[:, feature_names].to_numpy()
    return result


def _label_training_risk(
    work: pd.DataFrame, quantile: float
) -> tuple[pd.Series, float, dict[str, Any]]:
    train_values = pd.to_numeric(work.loc[work["split"].eq("train"), "W_proxy"], errors="coerce")
    train_values = train_values.loc[np.isfinite(train_values)]
    if train_values.empty:
        raise ValueError("training rows contain no valid W_proxy values")
    threshold = float(train_values.quantile(quantile))
    use_strict = bool((train_values >= threshold).sum() == len(train_values) and threshold == train_values.min())
    operator = ">" if use_strict else ">="
    proxy = pd.to_numeric(work["W_proxy"], errors="coerce")
    labels = pd.Series(pd.NA, index=work.index, dtype="Int64")
    valid = proxy.notna() & np.isfinite(proxy)
    labels.loc[valid] = (proxy.loc[valid] > threshold if use_strict else proxy.loc[valid] >= threshold).astype(int)
    train_labels = labels.loc[work["split"].eq("train")].dropna().astype(int)
    holdout_labels = labels.loc[work["split"].eq("holdout")].dropna().astype(int)
    meta = {
        "quantile": float(quantile),
        "threshold": threshold,
        "operator": operator,
        "tie_policy": "strict_gt_when_quantile_equals_training_minimum_and_ge_would_label_all" if use_strict else "inclusive_ge",
        "training_valid_proxy_rows": int(len(train_values)),
        "training_positive_count": int(train_labels.sum()),
        "training_negative_count": int((1 - train_labels).sum()),
        "holdout_valid_proxy_rows": int(len(holdout_labels)),
        "holdout_positive_count": int(holdout_labels.sum()),
        "holdout_negative_count": int((1 - holdout_labels).sum()),
        "training_class_status": "two_class" if train_labels.nunique() == 2 else "one_class",
        "holdout_class_status": "two_class" if holdout_labels.nunique() == 2 else "one_class",
    }
    return labels, threshold, meta


def _feature_columns(frame: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    numeric = [
        "course_level",
        "historical_w_proxy_mean",
        "historical_demand_proxy_mean",
        "historical_students_mean",
        "historical_grade_total_mean",
        "historical_term_count",
        *HISTORICAL_GRADE_SHARE_COLUMNS,
    ]
    numeric = ["Year_offset", *numeric]
    categorical = ["Subject", "Term"]
    numeric = [column for column in numeric if column in frame.columns and frame[column].notna().any()]
    categorical = [column for column in categorical if column in frame.columns]
    features = numeric + categorical
    forbidden = sorted(set(features).intersection(LEAKAGE_COLUMNS))
    if forbidden:
        raise AssertionError(f"leakage columns selected as features: {forbidden}")
    return features, numeric, categorical


def build_phase6_feature_table(
    metrics: pd.DataFrame,
    window: tuple[int, int, int] = DEFAULT_WINDOW,
    terms: tuple[str, ...] = DEFAULT_TERMS,
    high_risk_quantile: float = DEFAULT_HIGH_RISK_QUANTILE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Filter input, create labels and leakage-safe predictive features."""
    window = _validate_window(window)
    terms = _validate_terms(terms)
    if isinstance(high_risk_quantile, bool) or not isinstance(high_risk_quantile, (int, float)):
        raise TypeError("high_risk_quantile must be numeric")
    if not 0 < float(high_risk_quantile) < 1:
        raise ValueError("high_risk_quantile must be between 0 and 1")
    if not isinstance(metrics, pd.DataFrame):
        raise TypeError("metrics must be a pandas DataFrame")
    _check_columns(metrics, REQUIRED_COLUMNS)

    work = _derive_grade_shares(metrics.copy())
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Term"] = work["Term"].astype("string").str.strip().str.lower()
    work = work.loc[work["Year"].isin(window) & work["Term"].isin(terms)].copy()
    if work.empty:
        raise ValueError("no rows remain after Phase 6 window and term filtering")
    if work.duplicated(subset=["Year", "Term", *COURSE_KEYS]).any():
        raise ValueError("input must have unique course-term rows")

    train_years, holdout_year = window_train_holdout(window)
    work["split"] = np.where(work["Year"].isin(train_years), "train", "holdout")
    work["row_id"] = (
        work["Year"].astype(int).astype(str)
        + "|" + work["Term"].astype(str)
        + "|" + work["Subject"].astype(str)
        + "|" + work["Number"].astype(str)
        + "|" + work["Course Title"].astype(str)
    )
    work["course_level"] = work["Number"].map(_course_level)
    work["Year_offset"] = work["Year"] - int(window[0])
    work = _add_historical_features(work)
    labels, threshold, label_meta = _label_training_risk(work, float(high_risk_quantile))
    work["high_w_risk"] = labels

    features, numeric, categorical = _feature_columns(work)
    ordered = [
        "row_id", *COURSE_KEYS, "Year", "Term", "split", "W", "Students", "W_proxy", "demand_proxy",
        "high_w_risk", "course_level", "grade_total", *GRADE_SHARE_COLUMNS,
        "historical_w_proxy_mean", "historical_demand_proxy_mean", "historical_students_mean",
        "historical_grade_total_mean", "historical_term_count", *HISTORICAL_GRADE_SHARE_COLUMNS, "Year_offset",
    ]
    ordered = [column for column in ordered if column in work.columns]
    output = work.loc[:, ordered].sort_values(
        ["Year", "Term", "Subject", "Number", "Course Title"], kind="mergesort"
    ).reset_index(drop=True)
    history_columns = [
        "historical_w_proxy_mean", "historical_demand_proxy_mean", "historical_students_mean",
        "historical_grade_total_mean", "historical_term_count", *HISTORICAL_GRADE_SHARE_COLUMNS,
    ]
    history_coverage = {}
    for split_name in ("train", "holdout"):
        split_frame = output.loc[output["split"].eq(split_name)]
        available = split_frame.loc[:, history_columns].notna() if history_columns else pd.DataFrame(index=split_frame.index)
        history_coverage[split_name] = {
            "rows": int(len(split_frame)),
            "rows_with_any_history": int(available.any(axis=1).sum()) if not available.empty else 0,
            "rows_with_all_history_missing": int((~available.any(axis=1)).sum()) if not available.empty else int(len(split_frame)),
            "non_null_by_feature": {column: int(available[column].sum()) for column in history_columns},
        }
    metadata = {
        "window": list(window),
        "terms": list(terms),
        "train_years": list(train_years),
        "holdout_year": int(holdout_year),
        "input_rows_after_filter": int(len(output)),
        "feature_columns": features,
        "numeric_feature_columns": numeric,
        "categorical_feature_columns": categorical,
        # Subject is an intentionally used categorical feature; only Number
        # and Course Title are excluded identity/display fields here.
        "excluded_predictive_columns": sorted(LEAKAGE_COLUMNS | {"Number", "Course Title"}),
        "historical_features_are_strictly_prior_years": True,
        "historical_aggregation_level": "prior calendar-year means across the selected spring/fall terms; not prior-same-term history",
        "historical_feature_coverage": history_coverage,
        "current_students_included": False,
        "current_grade_features_included": False,
        "current_students_limitation": "Current Students and current grade fields are retained for audit but excluded from predictive features because they are end-of-term outcomes; historical versions are used when available.",
        "label": label_meta,
        "threshold": threshold,
        "window_selection": {
            "selected_window": list(window),
            "approval_status": "approved_governance_window",
            "policy": "primary_2021_2023_then_module_level_fallbacks_only_if_insufficient",
        },
    }
    return output, metadata


def _preprocessor(numeric: Sequence[str], categorical: Sequence[str]) -> ColumnTransformer:
    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric:
        transformers.append(
            ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), list(numeric))
        )
    if categorical:
        transformers.append(
            ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), list(categorical))
        )
    if not transformers:
        raise ValueError("no predictive features are available")
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _safe_metric(fn, *args, **kwargs) -> float | None:
    try:
        value = float(fn(*args, **kwargs))
    except (ValueError, TypeError):
        return None
    return value if np.isfinite(value) else None


def _metrics_row(
    model: str,
    split: str,
    y_true: pd.Series,
    probability: np.ndarray,
    prediction: np.ndarray,
    recall_at_k: float,
) -> dict[str, Any]:
    y = pd.to_numeric(pd.Series(y_true), errors="coerce").dropna().astype(int).to_numpy()
    probability = np.asarray(probability, dtype=float)
    prediction = np.asarray(prediction, dtype=int)
    classes = sorted(set(y.tolist()))
    row: dict[str, Any] = {
        "model": model,
        "split": split,
        "status": "ok" if len(classes) == 2 else "one_class",
        "rows": int(len(y)),
        "positive_count": int(y.sum()) if len(y) else 0,
        "negative_count": int((1 - y).sum()) if len(y) else 0,
        "pr_auc": None,
        "roc_auc": None,
        "f1": _safe_metric(f1_score, y, prediction, zero_division=0) if len(y) else None,
        "precision": _safe_metric(precision_score, y, prediction, zero_division=0) if len(y) else None,
        "recall": _safe_metric(recall_score, y, prediction, zero_division=0) if len(y) else None,
        "balanced_accuracy": _safe_metric(balanced_accuracy_score, y, prediction) if len(y) and len(classes) == 2 else None,
        "brier_score": _safe_metric(brier_score_loss, y, probability) if len(y) else None,
        "recall_at_k": None,
        "recall_at_k_fraction": float(recall_at_k),
        "recall_at_k_rows": None,
        "positive_in_top_k": None,
        "tn": None,
        "fp": None,
        "fn": None,
        "tp": None,
    }
    if len(classes) == 2:
        row["pr_auc"] = _safe_metric(average_precision_score, y, probability)
        row["roc_auc"] = _safe_metric(roc_auc_score, y, probability)
        matrix = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
        row["tn"], row["fp"], row["fn"], row["tp"] = (int(value) for value in matrix)
        k = max(1, int(np.ceil(len(y) * recall_at_k)))
        order = np.argsort(-probability, kind="mergesort")[:k]
        positives = int(y[order].sum())
        row["recall_at_k"] = positives / int(y.sum()) if y.sum() else None
        row["recall_at_k_rows"] = k
        row["positive_in_top_k"] = positives
    return row


def _make_model_pipelines(
    numeric: Sequence[str], categorical: Sequence[str], random_state: int
) -> dict[str, Pipeline]:
    prep = _preprocessor(numeric, categorical)
    return {
        "logistic_regression": Pipeline(
            [("preprocess", prep), ("model", LogisticRegression(max_iter=2000, class_weight="balanced", solver="liblinear", random_state=random_state))]
        ),
        "random_forest": Pipeline(
            [("preprocess", clone(prep)), ("model", RandomForestClassifier(n_estimators=250, min_samples_leaf=3, class_weight="balanced_subsample", random_state=random_state, n_jobs=1))]
        ),
    }


def _feature_importance(model_name: str, pipeline: Pipeline) -> pd.DataFrame:
    try:
        names = pipeline.named_steps["preprocess"].get_feature_names_out()
        estimator = pipeline.named_steps["model"]
        if hasattr(estimator, "coef_"):
            values = np.abs(estimator.coef_[0])
            direction = estimator.coef_[0]
        elif hasattr(estimator, "feature_importances_"):
            values = estimator.feature_importances_
            direction = np.nan
        else:
            return pd.DataFrame(columns=["model", "feature", "importance", "direction"])
        output = pd.DataFrame({"model": model_name, "feature": names, "importance": values, "direction": direction})
        return output.sort_values(["importance", "feature"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    except (AttributeError, KeyError, ValueError):
        return pd.DataFrame(columns=["model", "feature", "importance", "direction"])


def fit_phase6_models(
    feature_table: pd.DataFrame,
    metadata: Mapping[str, Any] | None = None,
    random_state: int = DEFAULT_RANDOM_STATE,
    recall_at_k: float = DEFAULT_RECALL_AT_K,
) -> dict[str, Any]:
    """Fit the two supervised models using only the train split."""
    if not isinstance(feature_table, pd.DataFrame):
        raise TypeError("feature_table must be a pandas DataFrame")
    if not 0 < float(recall_at_k) <= 1:
        raise ValueError("recall_at_k must be in (0, 1]")
    if metadata is None:
        _, numeric, categorical = _feature_columns(feature_table)
        feature_columns = numeric + categorical
    else:
        feature_columns = list(metadata["feature_columns"])
        numeric = list(metadata["numeric_feature_columns"])
        categorical = list(metadata["categorical_feature_columns"])
    _check_columns(feature_table, [*feature_columns, "split", "high_w_risk", "row_id"])
    train = feature_table.loc[feature_table["split"].eq("train") & feature_table["high_w_risk"].notna()].copy()
    holdout = feature_table.loc[feature_table["split"].eq("holdout") & feature_table["high_w_risk"].notna()].copy()
    if train.empty or holdout.empty:
        raise ValueError("both train and holdout must have valid labelled rows")
    X_train, y_train = train[feature_columns], train["high_w_risk"].astype(int)
    X_holdout, y_holdout = holdout[feature_columns], holdout["high_w_risk"].astype(int)

    baseline_probability = float(y_train.mean())
    metric_rows = []
    prediction_rows = []
    importance_frames = []
    models: dict[str, Pipeline] = {}
    model_status: dict[str, str] = {}
    threshold_used = float(metadata.get("threshold", np.nan)) if metadata is not None else np.nan

    baseline_pred_train = np.full(len(train), int(baseline_probability >= 0.5), dtype=int)
    baseline_pred_holdout = np.full(len(holdout), int(baseline_probability >= 0.5), dtype=int)
    for split, y, p, pred in (
        ("train", y_train, np.full(len(train), baseline_probability), baseline_pred_train),
        ("holdout", y_holdout, np.full(len(holdout), baseline_probability), baseline_pred_holdout),
    ):
        metric_rows.append(_metrics_row("majority_baseline", split, y, p, pred, recall_at_k))

    for name, pipeline in _make_model_pipelines(numeric, categorical, int(random_state)).items():
        if y_train.nunique() < 2:
            model_status[name] = "skipped_one_class_training_target"
            continue
        try:
            pipeline.fit(X_train, y_train)
            models[name] = pipeline
            model_status[name] = "fit"
        except (ValueError, TypeError) as exc:
            model_status[name] = f"skipped_fit_error:{type(exc).__name__}"
            continue

        for split, frame, y in (("train", train, y_train), ("holdout", holdout, y_holdout)):
            probability = pipeline.predict_proba(frame[feature_columns])[:, 1]
            prediction = (probability >= 0.5).astype(int)
            metric_rows.append(_metrics_row(name, split, y, probability, prediction, recall_at_k))
            prediction_rows.append(
                pd.DataFrame(
                    {
                        "row_id": frame["row_id"].to_numpy(),
                        "Subject": frame["Subject"].to_numpy(),
                        "Number": frame["Number"].to_numpy(),
                        "Course Title": frame["Course Title"].to_numpy(),
                        "Year": frame["Year"].to_numpy(),
                        "Term": frame["Term"].to_numpy(),
                        "split": split,
                        "actual_high_w_risk": y.to_numpy(),
                        "predicted_probability": probability,
                        "predicted_high_w_risk": prediction,
                        "W_proxy": frame["W_proxy"].to_numpy(),
                        "threshold_used": threshold_used,
                        "model": name,
                    }
                )
            )
        importance_frames.append(_feature_importance(name, pipeline))

    predictions = pd.concat(prediction_rows, ignore_index=True) if prediction_rows else pd.DataFrame()
    if not predictions.empty:
        predictions = predictions.sort_values(["model", "Year", "Term", "Subject", "Number"], kind="mergesort").reset_index(drop=True)
    metrics = pd.DataFrame(metric_rows)
    importance = pd.concat(importance_frames, ignore_index=True) if importance_frames else pd.DataFrame(columns=["model", "feature", "importance", "direction"])
    if not importance.empty:
        importance = importance.sort_values(["model", "importance", "feature"], ascending=[True, False, True], kind="mergesort").reset_index(drop=True)
    return {
        "models": models,
        "model_status": model_status,
        "metrics": metrics,
        "predictions": predictions,
        "feature_importance": importance,
        "baseline_positive_rate": baseline_probability,
        "random_state": int(random_state),
        "recall_at_k": float(recall_at_k),
    }


def build_course_profiles(
    feature_table: pd.DataFrame,
    metadata: Mapping[str, Any] | None = None,
    random_state: int = DEFAULT_RANDOM_STATE,
    min_rows: int = DEFAULT_PROFILE_MIN_ROWS,
    max_k: int = DEFAULT_PROFILE_MAX_K,
    min_silhouette: float = DEFAULT_PROFILE_MIN_SILHOUETTE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build descriptive train-only K-Means profiles, or return a skip record."""
    train = feature_table.loc[feature_table["split"].eq("train")].copy()
    profile_numeric = [
        "course_level", "Students", "grade_total", *[c for c in GRADE_SHARE_COLUMNS if c in train.columns],
        "historical_w_proxy_mean", "historical_demand_proxy_mean", "historical_students_mean",
                        "historical_grade_total_mean", "historical_term_count", "W_proxy",
    ]
    profile_numeric = [c for c in profile_numeric if c in train.columns]
    profile = train.groupby(list(COURSE_KEYS), dropna=False, sort=True)[profile_numeric].mean().reset_index()
    usable = profile.loc[:, profile_numeric].replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all")
    profile_features_used = list(usable.columns)
    if len(profile) < int(min_rows):
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "too_few_train_courses", "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "target_proxy_included_in_profiles": True, "descriptive_only": True}
    if usable.shape[1] < 2:
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "fewer_than_two_numeric_profile_features", "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "target_proxy_included_in_profiles": True, "descriptive_only": True}
    usable = usable.fillna(usable.median(numeric_only=True))
    if usable.isna().any().any():
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "profile_features_not_imputable", "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "target_proxy_included_in_profiles": True, "descriptive_only": True}
    scaler = StandardScaler()
    scaled = scaler.fit_transform(usable)
    upper_k = min(int(max_k), len(profile) - 1)
    if upper_k < 2:
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "not_enough_rows_for_two_clusters", "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "target_proxy_included_in_profiles": True, "descriptive_only": True}
    candidates = []
    for k in range(2, upper_k + 1):
        if np.unique(scaled, axis=0).shape[0] <= k:
            continue
        model = KMeans(n_clusters=k, random_state=int(random_state), n_init=20)
        labels = model.fit_predict(scaled)
        score = _safe_metric(silhouette_score, scaled, labels) if len(set(labels)) > 1 else None
        if score is not None:
            candidates.append((score, k, model, labels))
    if not candidates:
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "silhouette_unavailable", "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "target_proxy_included_in_profiles": True, "descriptive_only": True}
    candidates.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_k, best_model, best_labels = candidates[0]
    if best_score < float(min_silhouette):
        return pd.DataFrame(columns=[*COURSE_KEYS, "cluster", "cluster_size", "silhouette", "status"]), {"status": "skipped", "reason": "silhouette_below_quality_floor", "best_silhouette": best_score, "best_k": best_k, "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "min_silhouette": float(min_silhouette), "target_proxy_included_in_profiles": True, "descriptive_only": True}
    output = profile.loc[:, list(COURSE_KEYS)].copy()
    output["cluster"] = best_labels.astype(int)
    sizes = output["cluster"].value_counts().to_dict()
    output["cluster_size"] = output["cluster"].map(sizes).astype(int)
    output["silhouette"] = float(best_score)
    output["status"] = "ok"
    output = output.sort_values(["cluster", "Subject", "Number", "Course Title"], kind="mergesort").reset_index(drop=True)
    centers = pd.DataFrame(scaler.inverse_transform(best_model.cluster_centers_), columns=usable.columns).round(10)
    centers.insert(0, "cluster", range(best_k))
    return output, {"status": "ok", "best_k": int(best_k), "silhouette": float(best_score), "train_course_rows": int(len(profile)), "feature_columns": profile_numeric, "feature_columns_used": profile_features_used, "cluster_sizes": {str(k): int(v) for k, v in sizes.items()}, "cluster_centers": centers.to_dict(orient="records"), "target_proxy_included_in_profiles": True, "descriptive_only": True}


def build_phase6_report(
    feature_table: pd.DataFrame,
    model_output: Mapping[str, Any],
    profile_table: pd.DataFrame,
    profile_metadata: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = model_output["metrics"]
    holdout = metrics.loc[metrics["split"].eq("holdout")].copy() if isinstance(metrics, pd.DataFrame) else pd.DataFrame()
    report = {
        "analysis": "Phase 6 — time-aware high-W-risk modelling and descriptive course profiles",
        "status": "complete",
        "window": metadata["window"],
        "window_selection": metadata.get("window_selection", {"selected_window": metadata["window"], "approval_status": "approved_governance_window"}),
        "terms": metadata["terms"],
        "train_years": metadata["train_years"],
        "holdout_year": metadata["holdout_year"],
        "grain": "course-term",
        "row_counts": {
            "feature_rows": int(len(feature_table)),
            "train_rows": int((feature_table["split"] == "train").sum()),
            "holdout_rows": int((feature_table["split"] == "holdout").sum()),
            "course_keys": int(feature_table.loc[feature_table["split"] == "train", list(COURSE_KEYS)].drop_duplicates().shape[0]),
        },
        "label": metadata["label"],
        "feature_controls": {
            "predictive_features": metadata["feature_columns"],
            "numeric_features": metadata["numeric_feature_columns"],
            "categorical_features": metadata["categorical_feature_columns"],
            "excluded_predictive_columns": metadata["excluded_predictive_columns"],
            "historical_features_are_strictly_prior_years": True,
            "historical_aggregation_level": metadata["historical_aggregation_level"],
            "historical_feature_coverage": metadata["historical_feature_coverage"],
            "current_students_included": metadata["current_students_included"],
            "current_grade_features_included": metadata["current_grade_features_included"],
            "year_encoding": "numeric Year_offset from selected-window first year",
        },
        "models": {
            "logistic_regression": "primary interpretable baseline with train-fitted imputation, scaling and one-hot encoding",
            "random_forest": "nonlinear comparator; fixed random_state and train-only fitting",
            "majority_baseline": "training positive-rate probability, no feature fitting",
            "random_state": model_output["random_state"],
            "recall_at_k_fraction": model_output["recall_at_k"],
            "fit_status": model_output["model_status"],
        },
        "holdout_metrics": json.loads(holdout.to_json(orient="records", double_precision=15)) if not holdout.empty else [],
        "profile": dict(profile_metadata),
        "proxy_definitions": {
            "demand_proxy": "Students + W; descriptive demand proxy, not registration-event or unique-student count",
            "W_proxy": "W / (Students + W); W-based withdrawal proxy, not official withdrawal/drop rate",
        },
        "scheduling_questions": [
            {"id": "conflict_pairs", "status": "unsupported", "question": "Which course combinations have the most severe conflicts?", "reason": "No reproducible section meeting day/start/end fields."},
            {"id": "crowded_time_slots", "status": "unsupported", "question": "Which time slots carry too many high-demand courses?", "reason": "No section time or capacity fields."},
            {"id": "department_core_conflicts", "status": "unsupported", "question": "Which departments have concentrated conflicts among core courses?", "reason": "No section conflict graph or core-course flag."},
            {"id": "low_demand_feasible_slots", "status": "unsupported", "question": "Are some courses feasible only in low-demand time slots?", "reason": "No feasible-slot or realized schedule history."},
            {"id": "schedule_change_association", "status": "unsupported", "question": "Is a schedule change associated with later course-selection volume?", "reason": "No schedule-change history with comparable later demand observations."},
        ],
        "limitations": [
            "The target is a W-based proxy label; it is not an official withdrawal/drop rate and cannot identify timing or reason.",
            "Current Students is retained for audit but excluded from predictive features; it is a count excluding W, not registration-event volume or a unique-student count.",
            "Historical W proxy and demand features are descriptive lag features from strictly earlier selected years; rows in the first selected year have missing history handled by train-fitted imputation.",
            "The source has no section id, student id, attendance, capacity or waitlist; this phase cannot answer scheduling-conflict questions.",
            "Model scores are temporal associations and screening performance, not causal retention effects or deployment guarantees.",
            "K-Means profiles, when present, describe similarity and do not prove why a course has a given W proxy.",
        ],
        "resume_evidence_boundary": "This independent project begins on 2026-09-10 and is not an ATLAS internship result.",
    }
    return report


def build_phase6_outputs(
    metrics: pd.DataFrame,
    window: tuple[int, int, int] = DEFAULT_WINDOW,
    terms: tuple[str, ...] = DEFAULT_TERMS,
    high_risk_quantile: float = DEFAULT_HIGH_RISK_QUANTILE,
    random_state: int = DEFAULT_RANDOM_STATE,
    recall_at_k: float = DEFAULT_RECALL_AT_K,
) -> dict[str, Any]:
    feature_table, metadata = build_phase6_feature_table(metrics, window, terms, high_risk_quantile)
    model_output = fit_phase6_models(feature_table, metadata, random_state, recall_at_k)
    profiles, profile_metadata = build_course_profiles(feature_table, metadata, random_state)
    report = build_phase6_report(feature_table, model_output, profiles, profile_metadata, metadata)
    return {
        "feature_table": feature_table,
        "model_metrics": model_output["metrics"],
        "predictions": model_output["predictions"],
        "course_profiles": profiles,
        "feature_importance": model_output["feature_importance"],
        "report": report,
        "metadata": metadata,
        "profile_metadata": profile_metadata,
    }


def write_phase6_outputs(outputs: Mapping[str, Any], output_dir: str | Path | None = None) -> dict[str, Path]:
    target_dir = Path(output_dir) if output_dir is not None else Path(DATA_PROCESSED_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "feature_table": target_dir / FEATURE_TABLE_OUTPUT,
        "model_metrics": target_dir / MODEL_METRICS_OUTPUT,
        "predictions": target_dir / PREDICTIONS_OUTPUT,
        "course_profiles": target_dir / COURSE_PROFILES_OUTPUT,
        "feature_importance": target_dir / FEATURE_IMPORTANCE_OUTPUT,
        "report": target_dir / REPORT_OUTPUT,
    }
    for key in ("feature_table", "model_metrics", "predictions", "course_profiles", "feature_importance"):
        outputs[key].to_csv(paths[key], index=False)
    paths["report"].write_text(json.dumps(outputs["report"], indent=2, ensure_ascii=False, sort_keys=True, default=_safe_json) + "\n", encoding="utf-8")
    return paths
