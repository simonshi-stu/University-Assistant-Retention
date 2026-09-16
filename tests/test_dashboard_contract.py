from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from app import aggregate_course_demand, resolve_special_topic_breakdown  # noqa: E402
from i18n import keys_match, t  # noqa: E402


def test_bilingual_continuity_and_eda_copy_is_present():
    assert keys_match()
    for key in ("continuity_title", "continuity_scope_note", "primary_window_note", "instructor_limit_note", "prediction_error_note", "eda_title"):
        assert t(key, "zh")
        assert t(key, "en")
    english = (ROOT / "docs" / "MODEL_AND_PROXY_GUIDE_EN.md").read_text(encoding="utf-8")
    assert "Same-course panel modelling and continuity" in english
    assert "W, drop, and grade-field boundaries" in english
    assert "Statistical methods that fit the current data" in english


def test_dashboard_copy_separates_windows_and_field_limits():
    primary = t("primary_window_note", "zh")
    trajectory = t("trajectory_note", "zh")
    continuity = t("continuity_scope_note", "zh")
    instructor = t("instructor_limit_note", "zh")
    assert "2021–2023" in primary
    assert "2019–2024" in trajectory
    assert "2024" in trajectory and "真值留出" in trajectory
    assert "出现 3 年不表示" in continuity
    assert "没有 section id" in instructor
    assert "不能" in instructor

    english = t("primary_window_note", "en") + t("continuity_scope_note", "en") + t("instructor_limit_note", "en")
    assert "2021–2023" in english
    assert "does not mean both Spring and Fall" in english
    assert "no section id" in english


def test_descriptive_course_aggregation_uses_stable_course_key():
    data = pd.DataFrame([
        {"Subject": "CS", "Number": 101, "Course Title": "Intro", "demand_proxy": 10, "W": 1},
        {"Subject": "CS", "Number": 101, "Course Title": "Introduction", "demand_proxy": 20, "W": 2},
    ])
    result = aggregate_course_demand(data)
    assert len(result) == 1
    assert result.loc[0, "demand_proxy_total"] == 30
    assert result.loc[0, "course_term_count"] == 2
    assert result.loc[0, "Course Title"] in {"Intro", "Introduction"}


def test_dashboard_field_boundaries_and_special_topic_breakdown_are_locked():
    students = t("students_definition", "zh")
    w = t("w_semantics_note", "zh")
    assert "结课后" in students
    assert "A+–F 最终成绩记录规模" in students
    assert "不是去重学生数" in students
    assert "W=0" in w
    assert "16 周" in w and "第 8 周" in w
    assert "没有周次、退课事件或日期字段" in w
    assert "不能从 W=0 证明学生适应" in w
    assert "不应解释为课程突然变难" in w

    continuity = t("continuity_note", "zh")
    assert "special-only 键不入普通连续性" in continuity
    assert "重叠的键保留普通行" in continuity
    assert "{" not in continuity
    continuity_en = t("continuity_note", "en")
    assert "special-only keys are excluded" in continuity_en
    assert "overlapping keys retain their ordinary rows" in continuity_en
    assert "{" not in continuity_en

    app_text = (ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
    for key in (
        "special_topic_course_keys_with_rows",
        "special_topic_only_course_keys_excluded",
        "special_topic_overlap_course_keys_retained",
    ):
        assert key in app_text
    assert '["W", t("w_semantics_note", lang)' in app_text

    note = t("special_topic_note", "zh", rows=34, keys=11, overlap=8, only=3)
    assert all(value in note for value in ("34", "11", "8", "3"))


def test_special_topic_breakdown_prefers_metadata_and_has_audit_fallback():
    explicit = resolve_special_topic_breakdown(
        {
            "special_topic_course_keys_with_rows": 11,
            "special_topic_only_course_keys_excluded": 3,
            "special_topic_overlap_course_keys_retained": 8,
        },
        None,
        None,
    )
    assert explicit == {"keys": 11, "overlap": 8, "only": 3}

    continuity = pd.DataFrame([{"Subject": "CS", "Number": 101}, {"Subject": "CS", "Number": 102}])
    audit = pd.DataFrame([{"Subject": "CS", "Number": 101}, {"Subject": "CS", "Number": 102}, {"Subject": "CS", "Number": 103}])
    fallback = resolve_special_topic_breakdown({}, continuity, audit)
    assert fallback == {"keys": 3, "overlap": 2, "only": 1}
