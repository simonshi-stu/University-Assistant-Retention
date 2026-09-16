from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from course_retention.course_trajectory import (  # noqa: E402
    aggregate_stable_course_terms,
    build_course_continuity_diagnostics,
    build_course_trajectory_outputs,
    build_trajectory_eda,
    build_same_term_lags,
    build_special_topic_audit,
    metric_row,
    write_course_trajectory_outputs,
)


def _raw_rows():
    rows = []
    for year in range(2019, 2025):
        for term in ("Spring", "Fall"):
            rows.append({"Year": year, "Term": term, "Subject": "CS", "Number": 101, "Course Title": "Intro", "Students": 10 + year - 2019, "W": int(year % 2), "A": 5, "B": 5})
    return pd.DataFrame(rows)


def test_stable_key_and_same_term_lags_ignore_title_change():
    metrics, metadata = aggregate_stable_course_terms(_raw_rows())
    assert metadata["course_keys"] == 1
    table = build_same_term_lags(metrics)
    row = table.loc[(table["Year"] == 2024) & (table["Term"] == "spring")].iloc[0]
    assert row["lag1_w_flag"] == 1
    assert row["lag2_w_flag"] == 0
    assert row["lag3_w_flag"] == 1
    assert row["history_year_count"] == 3
    assert bool(row["eligible_target"])
    assert row["term_match_mode"] == "any_term"
    assert table.loc[table["Year"] == 2019, "eligible_target"].sum() == 0


def test_holdout_history_is_prior_only_and_metric_formula():
    metrics, _ = aggregate_stable_course_terms(_raw_rows())
    table = build_same_term_lags(metrics)
    holdout = table.loc[table["Year"] == 2024]
    assert holdout["lag1_w_proxy"].notna().all()
    assert holdout["W_proxy"].notna().all()
    row = metric_row("x", "holdout", "all", [0, 1, 1, 0, 1], [0.1, 0.7, 0.6, 0.2, 0.9], [0, 1, 1, 0, 1])
    assert row["tn"] == 2 and row["tp"] == 3
    assert row["brier_score"] == pytest.approx(((0.1**2) + (0.3**2) + (0.4**2) + (0.2**2) + (0.1**2)) / 5)


def test_ordinary_course_history_can_cross_terms_and_has_grade_feedback():
    raw = _raw_rows()
    raw["W"] = 0
    raw.loc[(raw["Year"] == 2023) & raw["Term"].eq("Fall"), "W"] = 3
    metrics, _ = aggregate_stable_course_terms(raw)
    table = build_same_term_lags(metrics)
    row = table.loc[(table["Year"] == 2024) & (table["Term"] == "spring")].iloc[0]
    assert row["lag1_w_flag"] == 1
    assert row["grade_point_mean"] > 0
    assert row["lag1_grade_point_mean"] > 0


def test_special_topic_title_is_set_aside_and_does_not_split_course_number():
    frame = _raw_rows()
    extra = frame.loc[(frame["Year"] == 2024) & (frame["Term"] == "Fall")].copy()
    extra["Course Title"] = "Special Topics"
    raw = pd.concat([frame, extra], ignore_index=True)
    metrics, metadata = aggregate_stable_course_terms(raw)
    current = metrics.loc[(metrics["Year"] == 2024) & (metrics["Term"] == "fall")]
    assert len(current) == 1
    assert metadata["collision_base_key_count"] == 0
    assert metadata["special_topic_raw_rows_excluded"] == 1
    assert metadata["special_topic_course_keys_with_rows"] == 1
    assert metadata["special_topic_only_course_keys_excluded"] == 0
    assert metadata["special_topic_overlap_course_keys_retained"] == 1
    assert "special_topic_course_keys_excluded" not in metadata
    assert current["course_variant"].eq("base").all()
    audit = build_special_topic_audit(raw)
    assert len(audit) == 1 and audit.iloc[0]["Course Title"] == "Special Topics"


def test_special_topic_key_audit_separates_overlap_from_special_only():
    frame = _raw_rows()
    overlapping_special = frame.loc[(frame["Year"] == 2024) & (frame["Term"] == "Fall")].copy()
    overlapping_special["Course Title"] = "Selected Topics"
    overlapping_special["Students"] = 999
    overlapping_special["W"] = 9
    special_only = overlapping_special.copy()
    special_only["Subject"] = "MATH"
    special_only["Number"] = 201
    raw = pd.concat([frame, overlapping_special, special_only], ignore_index=True)

    metrics, metadata = aggregate_stable_course_terms(raw)
    current = metrics.loc[
        (metrics["Subject"] == "CS")
        & (metrics["Year"] == 2024)
        & (metrics["Term"] == "fall")
    ].iloc[0]
    assert current["Students"] == 15
    assert current["W"] == 0
    assert metadata["special_topic_course_keys_with_rows"] == 2
    assert metadata["special_topic_only_course_keys_excluded"] == 1
    assert metadata["special_topic_overlap_course_keys_retained"] == 1

    eda = build_trajectory_eda(raw, metrics)
    assert eda["report"]["special_topic_course_keys_with_rows"] == 2
    assert eda["report"]["special_topic_only_course_keys_excluded"] == 1
    assert eda["report"]["special_topic_overlap_course_keys_retained"] == 1
    assert "special_topic_course_keys_excluded" not in eda["report"]


def test_persisted_title_audit_uses_all_ordinary_source_titles(tmp_path):
    frame = _raw_rows()
    variant = frame.loc[(frame["Year"] == 2024) & (frame["Term"] == "Fall")].copy()
    variant["Course Title"] = "Introductory Course"
    raw = pd.concat([frame, variant], ignore_index=True)

    outputs = build_course_trajectory_outputs(raw)
    paths = write_course_trajectory_outputs(outputs, tmp_path)
    title_audit = pd.read_csv(paths["title_audit"])
    row = title_audit.loc[title_audit["Subject"].eq("CS")].iloc[0]
    assert row["title_count"] == 2
    assert bool(row["title_changed"]) is True
    assert outputs["metadata"]["all_observed_title_change_base_key_count"] == 1


def test_title_normalization_links_light_edits_but_not_substantive_renames():
    light = _raw_rows()
    light.loc[light["Year"] == 2023, "Course Title"] = " intro!  "
    light_metrics, _ = aggregate_stable_course_terms(light)
    light_lags = build_same_term_lags(light_metrics)
    assert light_lags.loc[(light_lags["Year"] == 2024) & (light_lags["Term"] == "spring"), "lag1_w_flag"].notna().all()

    substantive = _raw_rows()
    substantive.loc[substantive["Year"] >= 2024, "Course Title"] = "Advanced Topics"
    substantive_metrics, _ = aggregate_stable_course_terms(substantive)
    substantive_lags = build_same_term_lags(substantive_metrics)
    row = substantive_lags.loc[(substantive_lags["Year"] == 2024) & (substantive_lags["Term"] == "spring")].iloc[0]
    assert pd.notna(row["lag1_w_flag"])
    assert set(substantive_metrics["course_variant"]) == {"base"}


def test_prediction_key_includes_course_variant():
    outputs = build_course_trajectory_outputs(_raw_rows())
    predictions = outputs["predictions"]
    key = ["Year", "Term", "Subject", "Number", "course_variant", "model"]
    assert predictions.duplicated(key).sum() == 0


def test_holdout_outcomes_are_not_used_as_model_features():
    raw = _raw_rows()
    outputs = build_course_trajectory_outputs(raw)
    mutated = raw.copy()
    holdout = mutated["Year"].eq(2024)
    mutated.loc[holdout, "W"] = 999
    mutated.loc[holdout, "Students"] = 1
    mutated.loc[holdout, "A"] = 777
    mutated.loc[holdout, "B"] = 888
    mutated_outputs = build_course_trajectory_outputs(mutated)
    key = ["Year", "Term", "Subject", "Number", "course_variant", "model"]
    left = outputs["predictions"].loc[outputs["predictions"]["Year"].eq(2024), key + ["predicted_probability"]].sort_values(key).reset_index(drop=True)
    right = mutated_outputs["predictions"].loc[mutated_outputs["predictions"]["Year"].eq(2024), key + ["predicted_probability"]].sort_values(key).reset_index(drop=True)
    pd.testing.assert_series_equal(left["predicted_probability"], right["predicted_probability"], check_names=False)
    assert mutated_outputs["report"]["current_2024_outcome_values_used_as_features"] is False


def test_scope_filter_rejects_non_six_year_input():
    with pytest.raises(ValueError):
        aggregate_stable_course_terms(_raw_rows(), years=(2021, 2022, 2023))


def test_continuity_diagnostic_distinguishes_seasonal_and_intermittent_courses():
    full = _raw_rows()
    spring_only = full.loc[full["Term"] == "Spring"].copy()
    intermittent = full.loc[full["Year"].isin([2019, 2020, 2022]) & full["Term"].eq("Fall")].copy()
    raw = pd.concat([full, spring_only.assign(Subject="MATH"), intermittent.assign(Subject="STAT")], ignore_index=True)
    metrics, _ = aggregate_stable_course_terms(raw)
    diagnostic = build_course_continuity_diagnostics(metrics).set_index("Subject")
    assert diagnostic.loc["CS", "continuity_class"] == "continuous_both_terms"
    assert diagnostic.loc["MATH", "continuity_class"] == "seasonal_spring"
    assert diagnostic.loc["MATH", "period_coverage"] == pytest.approx(.5)
    assert diagnostic.loc["STAT", "continuity_class"] == "intermittent"
    assert bool(diagnostic.loc["STAT", "backtest_2024_eligible"]) is False
    assert diagnostic.loc["STAT", "excluded_reason"]


def test_eda_schema_reconciles_instructor_rows_to_course_terms():
    raw = _raw_rows().copy()
    raw = pd.concat([raw, raw.iloc[[0]].assign(**{"Primary Instructor": "second"})], ignore_index=True)
    metrics, _ = aggregate_stable_course_terms(raw)
    eda = build_trajectory_eda(raw, metrics)
    assert {"inventory", "coverage", "subject_distribution", "numeric_summary", "join_audit"}.issubset(eda)
    assert eda["report"]["filtered_rows"] == len(raw)
    assert eda["report"]["reconciliation_all_zero"] is True
    audit = eda["join_audit"].iloc[0]
    assert audit["relationship"] == "many_to_one"
    assert audit["source_groups_with_multiple_rows"] >= 1
    assert "drop event" in eda["report"]["drop_semantics"]
