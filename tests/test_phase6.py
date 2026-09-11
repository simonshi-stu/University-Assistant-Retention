"""Offline tests for the Phase 6 modelling contract."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from course_retention.phase6 import (  # noqa: E402
    build_course_profiles,
    build_phase6_feature_table,
    build_phase6_outputs,
    fit_phase6_models,
)


def _frame(years=(2021, 2022, 2023), risk_values=None):
    rows = []
    risk_values = risk_values or {2021: [0.0, 0.02, 0.04, 0.06], 2022: [0.0, 0.03, 0.05, 0.08], 2023: [0.0, 0.01, 0.07, 0.09]}
    for year in years:
        for i, value in enumerate(risk_values[year]):
            students = 20 + i
            w = round(value * students / max(1 - value, 1e-9))
            rows.append({
                "Year": year, "Term": "spring" if i % 2 == 0 else "fall", "Subject": "CS",
                "Number": str(100 + i * 100), "Course Title": f"Course {i}", "Students": students,
                "W": w, "W_proxy": value, "demand_proxy": students + w, "grade_total": 20,
                "share_A": 0.5, "share_B": 0.3, "share_C": 0.1, "share_F": 0.1,
            })
    return pd.DataFrame(rows)


def test_temporal_split_and_training_only_threshold():
    table, metadata = build_phase6_feature_table(_frame())
    assert set(table.loc[table.split == "train", "Year"]) == {2021, 2022}
    assert set(table.loc[table.split == "holdout", "Year"]) == {2023}
    assert metadata["label"]["threshold"] == pytest.approx(pd.Series([0, .02, .04, .06, 0, .03, .05, .08]).quantile(.75))
    assert metadata["label"]["threshold"] != pytest.approx(pd.Series([0, .02, .04, .06, 0, .03, .05, .08, 0, .01, .07, .09]).quantile(.75))


def test_leakage_columns_are_not_predictive_features():
    _, metadata = build_phase6_feature_table(_frame())
    forbidden = {"W", "W_proxy", "demand_proxy", "high_w_risk", "demand_rank", "w_proxy_rank"}
    assert not forbidden.intersection(metadata["feature_columns"])
    assert "Students" not in metadata["feature_columns"]
    assert "share_A" not in metadata["feature_columns"]
    assert "historical_w_proxy_mean" in metadata["feature_columns"]
    assert "historical_share_A" in metadata["feature_columns"]


def test_historical_features_use_only_prior_years():
    table, _ = build_phase6_feature_table(_frame())
    first_year = table.loc[table["Year"] == 2021]
    assert first_year["historical_w_proxy_mean"].isna().all()
    later = table.loc[(table["Year"] == 2023) & (table["Number"].astype(str) == "100")].iloc[0]
    assert later["historical_w_proxy_mean"] == pytest.approx(0.0)
    assert later["historical_term_count"] == pytest.approx(2.0)


def test_models_are_deterministic_and_predict_only_holdout_with_two_classes():
    table, metadata = build_phase6_feature_table(_frame())
    result = fit_phase6_models(table, metadata, random_state=7)
    assert set(result["metrics"]["model"]) >= {"majority_baseline"}
    assert set(result["predictions"]["split"]) == {"train", "holdout"}
    assert set(result["predictions"]["model"]) <= {"logistic_regression", "random_forest"}
    again = fit_phase6_models(table, metadata, random_state=7)
    pd.testing.assert_frame_equal(result["metrics"], again["metrics"])
    pd.testing.assert_frame_equal(result["predictions"], again["predictions"])


def test_one_class_training_is_reported_not_crashed():
    frame = _frame(risk_values={2021: [0, 0, 0, 0], 2022: [0, 0, 0, 0], 2023: [0, .01, .02, .03]})
    table, metadata = build_phase6_feature_table(frame)
    result = fit_phase6_models(table, metadata)
    assert result["model_status"]["logistic_regression"] == "skipped_one_class_training_target"
    assert result["model_status"]["random_forest"] == "skipped_one_class_training_target"


def test_profiles_have_explicit_skip_or_run_status():
    table, metadata = build_phase6_feature_table(_frame())
    profiles, report = build_course_profiles(table, metadata, min_rows=100)
    assert report["status"] == "skipped"
    assert profiles.empty
    larger = pd.concat([_frame().assign(Subject=lambda x: x.Subject + str(i)) for i in range(5)], ignore_index=True)
    larger_table, larger_metadata = build_phase6_feature_table(larger)
    profile_table, profile_report = build_course_profiles(larger_table, larger_metadata)
    assert profile_report["status"] in {"ok", "skipped"}
    if profile_report["status"] == "ok":
        assert {"cluster", "cluster_size", "silhouette"}.issubset(profile_table.columns)


def test_profiles_are_deterministic_and_disclose_proxy_input():
    table, metadata = build_phase6_feature_table(pd.concat([_frame().assign(Subject=lambda x: x.Subject + str(i)) for i in range(5)], ignore_index=True))
    first, first_meta = build_course_profiles(table, metadata, random_state=9)
    second, second_meta = build_course_profiles(table, metadata, random_state=9)
    pd.testing.assert_frame_equal(first, second)
    assert first_meta == second_meta
    assert first_meta["target_proxy_included_in_profiles"] is True


def test_build_outputs_writes_expected_shapes(tmp_path):
    outputs = build_phase6_outputs(_frame())
    assert outputs["report"]["window"] == [2021, 2022, 2023]
    assert {"pr_auc", "roc_auc", "f1", "recall_at_k"}.issubset(outputs["model_metrics"].columns)
    assert all(item["status"] == "unsupported" for item in outputs["report"]["scheduling_questions"])
    assert outputs["report"]["proxy_definitions"]["W_proxy"].startswith("W /")


def test_dashboard_contains_machine_readable_schedule_limitations():
    dashboard = (PROJECT_ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert dashboard.count("不能回答") >= 5
    assert "W proxy" in dashboard
