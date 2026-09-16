r"""Local Streamlit dashboard for reproducible course-retention outputs.

Run from the repository root with ``python -m streamlit run dashboard/app.py``.
The data layer is deliberately unchanged by the language switch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

from i18n import LANGUAGES, keys_match, t


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

st.set_page_config(page_title=t("page_title"), page_icon="📘", layout="wide")


@st.cache_data(show_spinner=False)
def _load_csv_cached(name: str, modified_ns: int) -> pd.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def load_csv(name: str) -> pd.DataFrame:
    path = PROCESSED / name
    return _load_csv_cached(name, path.stat().st_mtime_ns)


@st.cache_data(show_spinner=False)
def _load_json_cached(name: str, modified_ns: int) -> dict:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_json(name: str) -> dict:
    path = PROCESSED / name
    return _load_json_cached(name, path.stat().st_mtime_ns)


def fmt_int(value: object) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def fmt_score(value: object) -> str:
    try:
        number = float(value)
        return "—" if pd.isna(number) else f"{number:.3f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def metric_value(metrics: pd.DataFrame, model: str, field: str, split: str = "holdout") -> object:
    if metrics.empty or not {"model", "split"}.issubset(metrics.columns):
        return None
    row = metrics.loc[(metrics["model"] == model) & (metrics["split"] == split)]
    return None if row.empty else row.iloc[0].get(field)


def aggregate_course_demand(data: pd.DataFrame) -> pd.DataFrame:
    cols = ["Subject", "Number", "Course Title", "demand_proxy_total", "course_term_count", "W_total", "W_proxy_weighted"]
    if data.empty:
        return pd.DataFrame(columns=cols)
    def representative_title(values: pd.Series) -> str:
        titles = values.dropna().astype(str).str.strip()
        titles = titles.loc[titles.ne("")]
        return titles.iloc[0] if not titles.empty else ""

    grouped = data.groupby(["Subject", "Number"], dropna=False, as_index=False).agg(
        **{
            "Course Title": pd.NamedAgg(column="Course Title", aggfunc=representative_title),
            "demand_proxy_total": pd.NamedAgg(column="demand_proxy", aggfunc="sum"),
            "course_term_count": pd.NamedAgg(column="demand_proxy", aggfunc="size"),
            "W_total": pd.NamedAgg(column="W", aggfunc="sum"),
        }
    )
    grouped["W_proxy_weighted"] = grouped["W_total"].div(grouped["demand_proxy_total"].where(grouped["demand_proxy_total"] > 0))
    return grouped


def course_label(data: pd.DataFrame) -> pd.Series:
    return data["Subject"].astype(str) + " " + data["Number"].astype(str) + " · " + data["Course Title"].astype(str)


def model_label(model: object, lang: str) -> str:
    labels = {
        "majority_baseline": {"zh": "多数类基线", "en": "Majority baseline"},
        "constant_baseline": {"zh": "常数基线", "en": "Constant baseline"},
        "persistence_baseline": {"zh": "持续性基线", "en": "Persistence baseline"},
        "logistic_regression": {"zh": "Logistic 回归", "en": "Logistic regression"},
        "random_forest": {"zh": "随机森林", "en": "Random forest"},
    }
    return labels.get(str(model), {"zh": str(model), "en": str(model)})[lang]


def term_label(value: object, lang: str) -> str:
    mapping = {"spring": {"zh": "春季", "en": "Spring"}, "fall": {"zh": "秋季", "en": "Fall"}}
    return mapping.get(str(value).lower(), {"zh": str(value), "en": str(value)})[lang]


def translated_model_columns(lang: str) -> dict[str, str]:
    return {
        "model": "模型" if lang == "zh" else "Model",
        "status": "状态" if lang == "zh" else "Status",
        "rows": "行数" if lang == "zh" else "Rows",
        "positive_count": "正类数" if lang == "zh" else "Positive count",
        "negative_count": "负类数" if lang == "zh" else "Negative count",
        "pr_auc": "AP" if lang == "zh" else "AP",
        "roc_auc": "ROC-AUC",
        "f1": "F1",
        "precision": "Precision",
        "recall": "Recall",
        "balanced_accuracy": "Balanced accuracy" if lang == "en" else "Balanced accuracy",
        "brier_score": "Brier score",
        "recall_at_k": "Recall@20%",
        "tn": "TN",
        "fp": "FP",
        "fn": "FN",
        "tp": "TP",
    }


def find_column(frame: pd.DataFrame, names: Iterable[str]) -> str | None:
    for name in names:
        if name in frame.columns:
            return name
    return None


def load_trajectory_outputs() -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame] | None:
    names = ["course_trajectory_metrics.csv", "course_trajectory_predictions.csv", "course_trajectory_report.json", "course_trajectory_logistic_coefficients.csv"]
    if not all((PROCESSED / name).exists() for name in names):
        return None
    return load_csv(names[0]), load_csv(names[1]), load_json(names[2]), load_csv(names[3])


def load_trajectory_continuity() -> pd.DataFrame | None:
    path = PROCESSED / "course_trajectory_continuity.csv"
    return load_csv(path.name) if path.exists() else None


def load_special_topic_audit() -> pd.DataFrame | None:
    path = PROCESSED / "course_trajectory_special_topic_audit.csv"
    return load_csv(path.name) if path.exists() else None


def resolve_special_topic_breakdown(meta: dict, continuity: pd.DataFrame | None, special_topic_audit: pd.DataFrame | None) -> dict[str, int] | None:
    """Prefer explicit metadata; derive the same stable-key split from audit rows when needed."""
    def metadata_int(names: tuple[str, ...]) -> int | None:
        for name in names:
            value = meta.get(name)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    keys = metadata_int(("special_topic_course_keys_with_rows", "special_topic_course_keys_involved"))
    only = metadata_int(("special_topic_only_course_keys_excluded", "special_topic_only_course_keys"))
    overlap = metadata_int(("special_topic_overlap_course_keys_retained", "special_topic_overlap_retained_course_keys", "special_topic_overlap_retained"))
    if keys is not None and only is not None and overlap is None and 0 <= only <= keys:
        overlap = keys - only
    if keys is not None and only is not None and overlap is not None:
        return {"keys": keys, "overlap": overlap, "only": only}

    required = {"Subject", "Number"}
    if special_topic_audit is None or continuity is None or not required.issubset(special_topic_audit.columns) or not required.issubset(continuity.columns):
        return None
    topic_keys = set(zip(special_topic_audit["Subject"].astype(str), special_topic_audit["Number"].astype(str)))
    retained_keys = set(zip(continuity["Subject"].astype(str), continuity["Number"].astype(str)))
    overlap_keys = topic_keys & retained_keys
    return {"keys": len(topic_keys), "overlap": len(overlap_keys), "only": len(topic_keys - retained_keys)}


def load_trajectory_eda() -> dict | None:
    path = PROCESSED / "course_trajectory_eda_report.json"
    return load_json(path.name) if path.exists() else None


def canonical_trajectory_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Adapt trajectory output column aliases without changing its values."""
    aliases = {
        "Year": ["Year", "year", "target_year", "prediction_year"],
        "Term": ["Term", "term", "season"],
        "Subject": ["Subject", "subject", "subject_code"],
        "Number": ["Number", "number", "course_number"],
        "Course Title": ["Course Title", "course_title", "title"],
        "course_variant": ["course_variant", "variant", "title_variant"],
        "term_match_mode": ["term_match_mode", "history_term_rule"],
        "grade_point_mean": ["grade_point_mean", "estimated_grade_point_mean"],
        "instructor_count": ["instructor_count"],
        "instructors_observed": ["instructors_observed", "primary_instructors"],
        "actual_w": ["actual_w", "actual_w_mark", "actual_w_flag", "actual_high_w_risk", "actual", "y_true"],
        "predicted_probability": ["predicted_probability", "predicted_prob", "probability", "score", "prediction_score"],
        "predicted_w": ["predicted_w", "predicted_w_flag", "predicted_high_w_risk", "predicted", "y_pred"],
    }
    out = pd.DataFrame(index=predictions.index)
    for target, candidates in aliases.items():
        source = find_column(predictions, candidates)
        if source:
            out[target] = predictions[source]
    for key in ["Year", "Term", "Subject", "Number", "Course Title"]:
        if key not in out:
            out[key] = ""
    for key in ["model", "split"]:
        source = find_column(predictions, [key])
        if source:
            out[key] = predictions[source]
    out["course"] = out["Subject"].astype(str) + " " + out["Number"].astype(str)
    return out


def render_dashboard_guide(lang: str, top_n: int, profile_meta: dict) -> None:
    with st.expander("看板说明：每个页面看什么，以及结论如何使用" if lang == "zh" else "Guide: what to look at and how to use conclusions", expanded=False):
        guide = pd.DataFrame([
            [t("overview", lang), "看筛选范围、规模代理榜和时间留出集表现。" if lang == "zh" else "Review scope, volume rankings, and time-holdout performance.", "榜单是描述性筛查，不是注册量或容量排名。" if lang == "zh" else "Rankings are descriptive screens, not enrollment or capacity rankings."],
            [t("demand", lang), "看课程规模、W 标记和派生占比。" if lang == "zh" else "Review course volume, W marks, and the derived share.", "可见关联，不证明退课原因。" if lang == "zh" else "Associations are visible; causes are not established."],
            [t("prediction", lang), "看 W 标记筛查的留出表现和排序。" if lang == "zh" else "Review holdout performance and W-mark ranking.", "模型是复核优先级工具，不是官方概率。" if lang == "zh" else "Models prioritise review; they are not official probabilities."],
            [t("profiles", lang), "看相似课程的规模画像。" if lang == "zh" else "Review similar-course volume profiles.", "K-Means 是探索性附录，不是学生群体或原因分组。" if lang == "zh" else "K-Means is an exploratory appendix, not student or cause groups."],
            [t("data_limits", lang), "查字段、数据边界和五个排课问题。" if lang == "zh" else "Check fields, boundaries, and five scheduling questions.", "数据不足时显示缺失字段和可行路径。" if lang == "zh" else "When data is insufficient, missing fields and practical paths are shown."],
        ], columns=["页面" if lang == "zh" else "Page", "看什么" if lang == "zh" else "Look at", "结论边界" if lang == "zh" else "Boundary"])
        st.dataframe(guide, use_container_width=True, hide_index=True)
        st.caption((f"当前 Top-N = {top_n}；只影响标题明确标注的榜单。" if lang == "zh" else f"Current Top N = {top_n}; it affects only rankings explicitly labelled as Top N."))
        if profile_meta.get("status") == "ok":
            st.caption("画像用于相似性观察，不用于预测或因果解释。" if lang == "zh" else "Profiles are for similarity exploration, not prediction or causal interpretation.")


def render_field_table(lang: str, analysis_window: list[int]) -> None:
    fields = pd.DataFrame([
        ["Year / Term", (f"课程开设年份与学期；当前窗口为 {analysis_window} 的 spring/fall。" if lang == "zh" else f"Offering year and term; current window is {analysis_window}, spring/fall."), "时间过滤与留出切分" if lang == "zh" else "Time filters and holdout split"],
        ["Subject / Number / variant", "课程身份固定为 Subject+Number；variant 保留为兼容字段并固定为 base。标题变化只进审计；特殊主题行按行暂放，special-only 键不入普通轨迹，重叠键的普通行保留。" if lang == "zh" else "Course identity is Subject+Number; variant is a compatibility field fixed to base. Title changes go to audit; special-topic rows are set aside at row level, special-only keys are excluded from the ordinary trajectory, and ordinary rows for overlapping keys are retained.", "同课程追踪，不代表 section" if lang == "zh" else "Same-course tracking, not sections"],
        ["Course Title", "源表标题；只用于展示和改名审计，不决定课程身份。" if lang == "zh" else "Source title; used for display and rename audit, not course identity.", "辅助解释" if lang == "zh" else "Supporting context"],
        ["Students", t("students_definition", lang), "课程规模的观测组成部分" if lang == "zh" else "Observed course-volume component"],
        ["W", t("w_semantics_note", lang), "观测结果，不是事件时间线" if lang == "zh" else "Observed outcome, not an event timeline"],
        ["demand_proxy", t("observed_proxy_formula", lang), "描述性规模代理，不是注册请求、容量或 waitlist。" if lang == "zh" else "Descriptive volume proxy, not registration requests, capacity, or waitlist."],
        ["w_mark_share", t("w_formula", lang), "派生占比；W 本身仍是计数，不是官方退课率。" if lang == "zh" else "Derived share; W itself remains a count, not an official withdrawal rate."],
        ["grade_point_mean", "由 A+–F 计数按 4.0 风格换算的估算平均绩点，不是源表官方 GPA。" if lang == "zh" else "Estimated 4.0-style mean from A+–F counts, not an official GPA field.", "同课程历史反馈参考" if lang == "zh" else "Historical course-feedback reference"],
        ["Primary Instructor", t("instructor_limit_note", lang), "课程-学期审计上下文" if lang == "zh" else "Course-term audit context"],
        ["high_w_risk", "是否出现 W 标记的二分类筛查目标。" if lang == "zh" else "Binary screening target for whether a W mark appears.", "不是高退课概率" if lang == "zh" else "Not a high-withdrawal probability"],
        ["historical_*", "严格早于当前年份的历史聚合，避免未来信息进入特征。" if lang == "zh" else "Aggregates strictly earlier than the current year to avoid future information.", "时间感知特征" if lang == "zh" else "Time-aware feature"],
        ["AP / ROC-AUC", "AP 是 Average Precision；二者衡量排序/区分表现。" if lang == "zh" else "AP is Average Precision; both measure ranking/discrimination.", "不代表退课率" if lang == "zh" else "Not a withdrawal rate"],
        ["Recall@20%", "预测分数最高 20% 行覆盖的真实正类比例。" if lang == "zh" else "Share of true positives covered by the top 20% scored rows.", "复核优先级排序" if lang == "zh" else "Review-priority ranking"],
    ], columns=["字段 / 指标" if lang == "zh" else "Field / metric", "数据含义" if lang == "zh" else "Meaning", "用途与限制" if lang == "zh" else "Use and limit"])
    st.dataframe(fields, use_container_width=True, hide_index=True)


def render_inventory(lang: str) -> None:
    rows = [
        ["公开 UIUC GPA 成绩分布" if lang == "zh" else "Public UIUC GPA grade distribution", t("status_available", lang), "课程-学期-教师成绩分布；含 Year、Term、Subject、Number、Course Title、成绩档位、W 和 Primary Instructor" if lang == "zh" else "Course-term-instructor grade distribution with year, term, course identity, grades, W, and Primary Instructor", "支持课程规模、W 标记、估算成绩反馈和时间留出筛查。" if lang == "zh" else "Supports course volume, W marks, estimated grade feedback, and time-holdout screening.", "不是独立学生表、注册事件、section、容量、waitlist 或 attendance。" if lang == "zh" else "Not a unique-student table, registration events, sections, capacity, waitlist, or attendance."],
        ["课程安排数据" if lang == "zh" else "Course scheduling data", t("status_not_used", lang), "当前没有可复现的 section meeting day/start/end、容量或 waitlist 字段。" if lang == "zh" else "No reproducible section meeting day/start/end, capacity, or waitlist fields are available.", "获得合法数据后可构建冲突图和时段分析。" if lang == "zh" else "Licensed data could support conflict graphs and time-slot analysis.", "当前不能回答具体 section 冲突、拥挤时段或调课后变化。" if lang == "zh" else "Cannot answer section conflicts, crowded time slots, or post-change effects."],
        ["Attendance / LMS / 学生参与" if lang == "zh" else "Attendance / LMS / participation", t("status_unavailable", lang), "没有合法、可识别且带时间标签的学生级活动数据。" if lang == "zh" else "No lawful, identifiable, time-labelled student activity data.", "未来授权接入后可做描述性关联。" if lang == "zh" else "Could support descriptive associations after authorised access.", "不能把 GPA 记录解释成出勤、参与人数或独立学生数。" if lang == "zh" else "GPA records cannot be interpreted as attendance, participants, or unique students."],
        ["课程评论 / ICES 文本" if lang == "zh" else "Course reviews / ICES text", t("status_not_enabled", lang), "缺少可合法使用、可匹配课程且带时间标签的文本。" if lang == "zh" else "No lawful, course-matchable, time-labelled text is available.", "未来可做主题与 W 标记占比的描述性关联。" if lang == "zh" else "Could support descriptive topic associations with W-mark share.", "当前不展示情绪分数或体验结论。" if lang == "zh" else "No sentiment score or experience conclusion is shown."],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["数据类型" if lang == "zh" else "Data", "状态" if lang == "zh" else "Status", "目前可见内容" if lang == "zh" else "Available now", "可以支持什么" if lang == "zh" else "Can support", "不能支持什么" if lang == "zh" else "Cannot support"]), use_container_width=True, hide_index=True)


def render_trajectory(lang: str, trajectory: tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame], top_n: int, continuity: pd.DataFrame | None = None) -> None:
    metrics, raw_predictions, report, coefficients = trajectory
    predictions = canonical_trajectory_predictions(raw_predictions)
    years = pd.to_numeric(predictions["Year"], errors="coerce")
    terms = predictions["Term"].astype(str).str.lower()
    view = predictions.loc[(years == 2024) & terms.isin(["spring", "fall"]) & (predictions.get("split", "holdout") == "holdout")].copy()
    st.subheader(t("trajectory_title", lang))
    st.caption(t("trajectory_note", lang))
    st.markdown(t("prediction_error_note", lang))
    st.info(t("w_semantics_note", lang))
    st.caption(t("gpa_estimate_note", lang))
    st.caption(t("instructor_limit_note", lang))
    summary = report.get("w_year_term_summary", []) if isinstance(report, dict) else []
    anomaly_periods = []
    for item in summary:
        if int(item.get("Year", 0)) == 2020 and str(item.get("Term", "")).lower() == "fall":
            anomaly_periods.append(f"2020 {term_label('fall', lang)} ({int(item.get('w_total', 0))} W)")
        if int(item.get("Year", 0)) == 2021 and str(item.get("Term", "")).lower() == "spring":
            anomaly_periods.append(f"2021 {term_label('spring', lang)} ({int(item.get('w_total', 0))} W)")
    if anomaly_periods:
        separator = "、" if lang == "zh" else ", "
        st.warning(t("w_anomaly_warning", lang, periods=separator.join(anomaly_periods)))
    model_choices = sorted(view["model"].dropna().unique().tolist()) if "model" in view else []
    model_default = model_choices.index("logistic_regression") if "logistic_regression" in model_choices else (model_choices.index("random_forest") if "random_forest" in model_choices else 0)
    model_pick = st.selectbox("查看课程轨迹模型" if lang == "zh" else "Trajectory model", model_choices, index=model_default, format_func=lambda x: model_label(x, lang)) if model_choices else None
    if model_pick:
        view = view.loc[view["model"] == model_pick].copy()
    if view.empty:
        st.info("当前课程轨迹输出没有 2024 Spring/Fall 同课程同学期记录。" if lang == "zh" else "The course-trajectory outputs contain no 2024 Spring/Fall same-course, same-term rows.")
    else:
        view["学期" if lang == "zh" else "Term"] = view["Term"].map(lambda x: term_label(x, lang))
        view = view.sort_values("predicted_probability", ascending=False).head(top_n)
        rename = {"Year": "年份" if lang == "zh" else "Year", "Subject": "Subject", "Number": "Number", "Course Title": "课程标题" if lang == "zh" else "Course title", "actual_w": "实际 W 标记" if lang == "zh" else "Actual W mark", "predicted_probability": "模型分数" if lang == "zh" else "Model score", "predicted_w": "预测 W 标记" if lang == "zh" else "Predicted W mark", "term_match_mode": "历史匹配" if lang == "zh" else "History match", "grade_point_mean": "估算平均绩点" if lang == "zh" else "Estimated grade-point mean", "instructor_count": "教师数" if lang == "zh" else "Instructor count", "instructors_observed": "观察到的教师" if lang == "zh" else "Instructors observed"}
        keep = [c for c in ["Year", "学期" if lang == "zh" else "Term", "Subject", "Number", "Course Title", "term_match_mode", "instructor_count", "instructors_observed", "grade_point_mean", "actual_w", "predicted_probability", "predicted_w"] if c in view]
        if "course_variant" in keep and view["course_variant"].astype(str).str.lower().isin(["", "base", "nan", "none"]).all():
            keep.remove("course_variant")
        rename["course_variant"] = "课程标题变体" if lang == "zh" else "Course title variant"
        st.dataframe(view[keep].rename(columns=rename), use_container_width=True, hide_index=True)
    if continuity is not None and not continuity.empty:
        meta = report.get("metadata", {}) if isinstance(report, dict) else {}
        special_topic_audit = load_special_topic_audit()
        special_breakdown = resolve_special_topic_breakdown(meta, continuity, special_topic_audit)
        st.subheader(t("continuity_title", lang))
        st.caption(t("continuity_note", lang))
        st.caption(t("continuity_scope_note", lang))
        class_counts = continuity.groupby("continuity_class", as_index=False).agg(course_count=("Subject", "size"), share=("Subject", lambda values: len(values) / len(continuity)), median_observed_periods=("observed_period_count", "median"))
        class_counts["continuity_class"] = class_counts["continuity_class"].map({
            "continuous_both_terms": "全年双学期连续" if lang == "zh" else "Continuous both terms",
            "seasonal_spring": "春季季节性" if lang == "zh" else "Spring-seasonal",
            "seasonal_fall": "秋季季节性" if lang == "zh" else "Fall-seasonal",
            "intermittent": "间歇" if lang == "zh" else "Intermittent",
        }).fillna(class_counts["continuity_class"])
        class_counts = class_counts.rename(columns={"continuity_class": t("continuity_class", lang), "course_count": t("course_keys", lang), "share": "占全部课程键比例" if lang == "zh" else "Share of course keys", "median_observed_periods": "观察学期数中位数" if lang == "zh" else "Median observed periods"})
        st.dataframe(class_counts, use_container_width=True, hide_index=True)
        special_rows = int(meta.get("special_topic_raw_rows_excluded", 0) or 0)
        if special_rows:
            if special_breakdown is not None:
                st.caption(t("special_topic_note", lang, rows=special_rows, **special_breakdown))
            else:
                st.caption(t("special_topic_metadata_unavailable", lang, rows=special_rows))
        st.subheader(t("continuity_evidence_title", lang))
        st.caption(t("continuity_evidence_note", lang))
        period_distribution = continuity.groupby("observed_period_count", as_index=False).agg(course_count=("Subject", "size"))
        period_distribution["share"] = period_distribution["course_count"].div(len(continuity))
        period_distribution = period_distribution.rename(columns={"observed_period_count": "实际观察学期数" if lang == "zh" else "Observed periods", "course_count": t("course_keys", lang), "share": "占全部课程键比例" if lang == "zh" else "Share of course keys"})
        st.dataframe(period_distribution, use_container_width=True, hide_index=True)
        st.caption(t("primary_window_evidence", lang))
        primary_distribution = report.get("continuity_primary_2021_2023_year_distribution", []) if isinstance(report, dict) else []
        if primary_distribution:
            primary_view = pd.DataFrame(primary_distribution).rename(columns={"primary_2021_2023_observed_year_count": "2021–2023 实际出现年份数" if lang == "zh" else "Observed 2021–2023 years", "course_count": t("course_keys", lang), "share": "占全部课程键比例" if lang == "zh" else "Share of course keys"})
            st.dataframe(primary_view, use_container_width=True, hide_index=True)
        shown_columns = [c for c in ["Subject", "Number", "observed_period_count", "observed_year_count", "spring_count", "fall_count", "term_match_mode", "observed_periods", "continuity_class", "backtest_2024_eligible", "excluded_reason"] if c in continuity.columns]
        shown = continuity.loc[:, shown_columns].copy()
        if "backtest_2024_eligible" in shown:
            shown = shown.loc[~shown["backtest_2024_eligible"] & shown["continuity_class"].eq("intermittent")].head(100)
        if not shown.empty:
            shown = shown.rename(columns={"observed_period_count": "实际观察学期数" if lang == "zh" else "Observed periods", "observed_year_count": "实际观察年份数" if lang == "zh" else "Observed years", "spring_count": "Spring 次数" if lang == "zh" else "Spring count", "fall_count": "Fall 次数" if lang == "zh" else "Fall count", "term_match_mode": "历史匹配" if lang == "zh" else "History match", "observed_periods": "实际观察格" if lang == "zh" else "Observed cells", "continuity_class": t("continuity_class", lang), "backtest_2024_eligible": t("backtest_eligible", lang), "excluded_reason": t("excluded_reason", lang)})
            st.dataframe(shown, use_container_width=True, hide_index=True)
    # The report owns coverage numbers; this view never embeds a stale literal.
    coverage = report.get("coverage_by_target_year_term", {}).get("2024", {}) if isinstance(report, dict) else {}
    coverage_rows = []
    for term in ["spring", "fall"]:
        item = coverage.get(term, {})
        coverage_rows.append([term_label(term, lang), item.get("eligible_rows"), item.get("all_rows")])
    if coverage_rows:
        eligible = sum(int(r[1]) for r in coverage_rows if r[1] is not None)
        all_rows = sum(int(r[2]) for r in coverage_rows if r[2] is not None)
        coverage_rows.insert(0, ["全部" if lang == "zh" else "All", eligible, all_rows])
        st.caption((f"{t('coverage', lang)}：主指标纳入 eligible 行 {eligible:,} / 2024 全部观察 {all_rows:,}；历史不足的行排除。" if lang == "zh" else f"{t('coverage', lang)}: {eligible:,} eligible rows / {all_rows:,} total 2024 observations; incomplete-history rows are excluded."))
        st.dataframe(pd.DataFrame(coverage_rows, columns=[t("term", lang), "主指标行" if lang == "zh" else "Eligible rows", "全部观察" if lang == "zh" else "All observations"]), use_container_width=True, hide_index=True)
    metric_view = metrics.copy()
    if model_pick and "model" in metric_view:
        metric_view = metric_view.loc[(metric_view["model"] == model_pick) & (metric_view.get("split", "holdout") == "holdout") & metric_view.get("scope", "all").isin(["all", "spring", "fall"])].copy()
    if not metric_view.empty:
        metric_columns = ["scope", "rows", "status", "average_precision_ap", "roc_auc", "brier_score", "precision", "recall", "f1", "balanced_accuracy", "recall_at_20pct", "tn", "fp", "fn", "tp"]
        metric_columns = [c for c in metric_columns if c in metric_view]
        metric_view = metric_view[metric_columns].rename(columns={"scope": t("metrics_scope", lang), "rows": "行数" if lang == "zh" else "Rows", "status": "状态" if lang == "zh" else "Status", "average_precision_ap": "AP", "recall_at_20pct": "Recall@20%", "brier_score": "Brier"})
        if t("metrics_scope", lang) in metric_view:
            metric_view[t("metrics_scope", lang)] = metric_view[t("metrics_scope", lang)].map(lambda x: "全部" if x == "all" and lang == "zh" else ("All" if x == "all" else term_label(x, lang)))
        status_column = "状态" if lang == "zh" else "Status"
        if status_column in metric_view:
            metric_view[status_column] = metric_view[status_column].replace({"ok": "可用" if lang == "zh" else "Available", "one_class": "单一类别" if lang == "zh" else "One class"})
        st.subheader(("2024 真实留出指标" if lang == "zh" else "2024 truth-only holdout metrics") + (f" · {model_label(model_pick, lang)}" if model_pick else ""))
        st.dataframe(metric_view.map(lambda x: fmt_score(x) if isinstance(x, float) else x), use_container_width=True, hide_index=True)
    if not coefficients.empty:
        st.subheader(t("coefficients", lang))
        st.markdown(t("logistic_explain", lang))
        coeff_view = coefficients.head(top_n).copy()
        coeff_view = coeff_view.rename(columns={"feature": "特征" if lang == "zh" else "Feature", "coefficient": "系数" if lang == "zh" else "Coefficient", "abs_coefficient": "|系数|" if lang == "zh" else "|Coefficient|", "odds_ratio": "优势比" if lang == "zh" else "Odds ratio", "direction": "方向" if lang == "zh" else "Direction", "feature_type": "特征类型" if lang == "zh" else "Feature type", "reference_category": "参考类别" if lang == "zh" else "Reference category", "sample_support": "样本支持" if lang == "zh" else "Sample support", "reference_support": "参考支持" if lang == "zh" else "Reference support", "support_threshold": "支持阈值" if lang == "zh" else "Support threshold", "low_support_warning": "低支持警示" if lang == "zh" else "Low-support warning"})
        type_column = "特征类型" if lang == "zh" else "Feature type"
        if type_column in coeff_view:
            coeff_view[type_column] = coeff_view[type_column].replace({"categorical": "分类" if lang == "zh" else "Categorical", "numeric": "数值" if lang == "zh" else "Numeric"})
        for column in [c for c in coeff_view.columns if str(c) in {"方向", "Direction"}]:
            coeff_view[column] = coeff_view[column].replace({"higher_odds": "更高 odds" if lang == "zh" else "Higher odds", "lower_odds": "更低 odds" if lang == "zh" else "Lower odds", "higher odds": "更高 odds" if lang == "zh" else "Higher odds", "lower odds": "更低 odds" if lang == "zh" else "Lower odds"})
        st.dataframe(coeff_view, use_container_width=True, hide_index=True)
        st.caption("低样本支持的系数不稳定，应结合 reference 和支持量谨慎阅读。" if lang == "zh" else "Coefficients with low sample support are unstable; read them with their reference and support counts.")
    if isinstance(report, dict):
        st.caption(("课程轨迹评估产物按报告记录的 Subject+Number 自适应历史规则读取；页面不在浏览器中重新训练。" if lang == "zh" else "Trajectory evaluation uses the report's adaptive Subject+Number history rule; the browser does not retrain models."))


def render_schedule_questions(lang: str) -> None:
    rows = [
        ["冲突权重最高的课程组合" if lang == "zh" else "Course pairs with the highest conflict weight", t("cannot_answer", lang), "缺少 section meeting day/start/end 时间字段；路径：取得合法课表后构建课程-时段冲突图。" if lang == "zh" else "Missing section meeting day/start/end; path: obtain licensed schedule data and build a course-slot conflict graph."],
        ["高需求课程最拥挤的时间段" if lang == "zh" else "Most crowded time slots for high-volume courses", t("cannot_answer", lang), "缺少 section 时间与容量；路径：合并可复现时段、容量和 waitlist 快照。" if lang == "zh" else "Missing section times and capacity; path: join reproducible time, capacity, and waitlist snapshots."],
        ["核心课冲突最集中的院系" if lang == "zh" else "Department with the most core-course conflicts", t("cannot_answer", lang), "缺少冲突图与 core-course 标识；路径：补充课程目录/培养方案并验证课程键。" if lang == "zh" else "Missing conflict graph and core-course flag; path: add catalogue/curriculum labels and validate course keys."],
        ["只能进入低需求时间段的课程" if lang == "zh" else "Courses confined to low-volume time slots", t("cannot_answer", lang), "缺少课程可行时间槽与实际安排变化；路径：保存多学期 section 快照后比较。" if lang == "zh" else "Missing feasible slots and schedule changes; path: retain multi-term section snapshots and compare them."],
        ["改时间后后续学生数/需求变化" if lang == "zh" else "Subsequent student/volume change after a time change", t("cannot_answer", lang), "缺少 section 安排变更历史与可比后续观测；路径：使用事件级或课程-学期面板并仅报告关联。" if lang == "zh" else "Missing schedule-change history and comparable follow-up observations; path: use event-level or course-term panels and report associations only."],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["问题" if lang == "zh" else "Question", "结论" if lang == "zh" else "Conclusion", "缺失字段与可行路径" if lang == "zh" else "Missing fields and practical path"]), use_container_width=True, hide_index=True)


def render_legacy_prediction(lang: str, label: dict, threshold: object, operator: str, model_report: dict, holdout_metrics: pd.DataFrame, predictions: pd.DataFrame, top_n: int) -> None:
    """Render the original three-year experiment only when trajectory outputs are absent."""
    a, b, c, d = st.columns(4)
    a.metric(t("training_rows", lang), fmt_int(label.get("training_valid_proxy_rows")))
    b.metric(t("training_positive", lang), fmt_int(label.get("training_positive_count")))
    c.metric(t("holdout_rows", lang), fmt_int(label.get("holdout_valid_proxy_rows")))
    d.metric(t("holdout_positive", lang), fmt_int(label.get("holdout_positive_count")))
    if threshold is not None:
        st.write(t("label_rule", lang, q=float(label.get("quantile", .75)) * 100, threshold=f"{float(threshold):.4f}", operator=operator, train=model_report.get("train_years", "—"), holdout=model_report.get("holdout_year", "—")))
    st.markdown(t("prediction_explain", lang))
    st.markdown(t("confusion_explain", lang))
    chart_metrics = holdout_metrics.loc[holdout_metrics["model"] != "majority_baseline", [c for c in ["model", "pr_auc", "roc_auc", "f1", "recall", "recall_at_k"] if c in holdout_metrics]].melt(id_vars="model", var_name="metric", value_name="value") if not holdout_metrics.empty else pd.DataFrame()
    if not chart_metrics.empty:
        chart_metrics["model"] = chart_metrics["model"].map(lambda x: model_label(x, lang))
        chart_metrics["metric"] = chart_metrics["metric"].replace({"pr_auc": "AP", "recall_at_k": "Recall@20%"})
        fig = px.bar(chart_metrics, x="metric", y="value", color="model", barmode="group", text_auto=".3f", labels={"metric": "指标" if lang == "zh" else "Metric", "value": "分数" if lang == "zh" else "Score", "model": "模型" if lang == "zh" else "Model"})
        fig.update_yaxes(range=[0, 1])
        st.plotly_chart(fig, use_container_width=True)
    if not holdout_metrics.empty:
        show = holdout_metrics[[c for c in ["model", "status", "rows", "positive_count", "negative_count", "pr_auc", "roc_auc", "f1", "precision", "recall", "balanced_accuracy", "brier_score", "recall_at_k", "tn", "fp", "fn", "tp"] if c in holdout_metrics]].copy()
        show["model"] = show["model"].map(lambda x: model_label(x, lang))
        show = show.rename(columns=translated_model_columns(lang))
        st.dataframe(show, use_container_width=True, hide_index=True)
    if not predictions.empty and "model" in predictions:
        fitted = [m for m in ["random_forest", "logistic_regression"] if m in predictions["model"].unique()]
        if fitted:
            default = "random_forest" if "random_forest" in fitted else fitted[0]
            picked = st.selectbox("查看模型预测排序" if lang == "zh" else "View model prediction ranking", fitted, index=fitted.index(default), format_func=lambda x: model_label(x, lang))
            pred = predictions.loc[(predictions["split"] == "holdout") & (predictions["model"] == picked)].sort_values("predicted_probability", ascending=False).head(top_n).copy()
            st.subheader(t("prediction_ranking", lang, n=top_n))
            if "Term" in pred:
                pred["Term"] = pred["Term"].map(lambda x: term_label(x, lang))
            st.dataframe(pred, use_container_width=True, hide_index=True)
    importance_path = PROCESSED / "phase6_feature_importance.csv"
    if importance_path.exists():
        importance = load_csv("phase6_feature_importance.csv")
        if not importance.empty and "model" in importance:
            models = sorted(importance["model"].dropna().unique().tolist())
            picked = st.selectbox("查看特征重要性" if lang == "zh" else "View feature importance", models, format_func=lambda x: model_label(x, lang), key="importance_model")
            imp = importance.loc[importance["model"] == picked].nlargest(top_n, "importance").sort_values("importance")
            if not imp.empty:
                fig = px.bar(imp, x="importance", y="feature", orientation="h", color="direction" if picked == "logistic_regression" and "direction" in imp else None, labels={"importance": "重要性 / 系数绝对值" if lang == "zh" else "Importance / absolute coefficient", "feature": "编码后特征" if lang == "zh" else "Encoded feature", "direction": "系数方向" if lang == "zh" else "Coefficient direction"})
                st.plotly_chart(fig, use_container_width=True)
                st.caption(t("feature_importance", lang, n=top_n))
                if picked == "logistic_regression":
                    st.markdown(t("logistic_explain", lang))


def main() -> None:
    # Keep this assertion close to the selector: adding a language must update every key.
    if not keys_match():
        st.error("语言资源不完整，请检查翻译词汇。" if st.session_state.get("lang", "zh") == "zh" else "A translation key is incomplete.")
        st.stop()
    lang = st.sidebar.selectbox(t("language", "zh"), list(LANGUAGES.values()), format_func=lambda x: "中文" if x == "zh" else "English", key="lang")
    st.title("📘 " + t("page_title", lang))
    st.caption(t("subtitle", lang))
    required = ["course_term_demand_metrics.csv", "course_demand_summary.csv", "phase5_report.json", "phase6_model_metrics.csv", "phase6_predictions.csv", "phase6_course_profiles.csv", "phase6_report.json"]
    missing = [name for name in required if not (PROCESSED / name).exists()]
    if missing:
        st.error(t("data_unavailable", lang))
        st.stop()
    course_terms = load_csv("course_term_demand_metrics.csv")
    course_summary = load_csv("course_demand_summary.csv")
    demand_report = load_json("phase5_report.json")
    model_report = load_json("phase6_report.json")
    model_metrics = load_csv("phase6_model_metrics.csv")
    predictions = load_csv("phase6_predictions.csv")
    profiles = load_csv("phase6_course_profiles.csv")
    analysis_window = [int(year) for year in model_report.get("window", sorted(course_terms["Year"].dropna().unique())[:3])]
    course_terms = course_terms.loc[course_terms["Year"].isin(analysis_window) & course_terms["Term"].astype(str).str.lower().isin(["spring", "fall"])].copy()
    course_summary = course_summary.merge(course_terms[["Subject", "Number", "Course Title"]].drop_duplicates(), on=["Subject", "Number", "Course Title"], how="inner", validate="many_to_one")
    st.sidebar.header(t("filter", lang))
    years = sorted(course_terms["Year"].dropna().astype(int).unique().tolist())
    selected_years = st.sidebar.multiselect(t("years", lang), years, default=years)
    selected_terms = st.sidebar.multiselect(t("terms", lang), ["spring", "fall"], default=["spring", "fall"], format_func=lambda x: term_label(x, lang))
    subjects = sorted(course_terms["Subject"].dropna().astype(str).unique().tolist())
    selected_subjects = st.sidebar.multiselect(t("subjects", lang), subjects)
    top_n = st.sidebar.slider(t("top_n", lang), 5, 25, 10)
    st.sidebar.caption(t("filter_note", lang))
    st.sidebar.caption(t("top_note", lang))
    filtered = course_terms.loc[course_terms["Year"].isin(selected_years) & course_terms["Term"].astype(str).str.lower().isin(selected_terms)].copy()
    if selected_subjects:
        filtered = filtered.loc[filtered["Subject"].isin(selected_subjects)].copy()
    if "w_mark_share" not in filtered.columns and "W_proxy" in filtered.columns:
        filtered["w_mark_share"] = filtered["W_proxy"]
    filtered_summary = aggregate_course_demand(filtered)
    holdout_metrics = model_metrics.loc[model_metrics["split"] == "holdout"].copy() if "split" in model_metrics else model_metrics
    label = model_report.get("label", {})
    threshold = label.get("threshold")
    operator = label.get("operator", ">=")
    trajectory_outputs = load_trajectory_outputs()
    continuity = load_trajectory_continuity()
    if trajectory_outputs is not None:
        trajectory_metrics = trajectory_outputs[0]
        trajectory_rf = trajectory_metrics.loc[(trajectory_metrics.get("model") == "random_forest") & (trajectory_metrics.get("scope", "all") == "all") & (trajectory_metrics.get("split") == "holdout")]
        rf_pr = None if trajectory_rf.empty else trajectory_rf.iloc[0].get("average_precision_ap")
    else:
        rf_pr = metric_value(model_metrics, "random_forest", "pr_auc")
    kpi = st.columns(6)
    kpi[0].metric(t("rows", lang), fmt_int(len(filtered)))
    kpi[1].metric(t("course_keys", lang), fmt_int(filtered[["Subject", "Number"]].drop_duplicates().shape[0]))
    kpi[2].metric(t("students", lang), fmt_int(filtered["Students"].sum()))
    kpi[3].metric(t("w_count", lang), fmt_int(filtered["W"].sum()))
    threshold_display = "W > 0" if trajectory_outputs is not None else ("—" if threshold is None or pd.isna(threshold) else f"{operator} {float(threshold):.4f}")
    kpi[4].metric(t("threshold", lang), threshold_display)
    kpi[5].metric(t("rf_ap", lang), fmt_score(rf_pr))
    if trajectory_outputs is None and operator == ">":
        st.warning(t("tie_warning", lang))
    st.info(("本看板使用公开 UIUC GPA 课程-学期聚合：W 是 Withdraw 正式标记计数，Students 是期末 A+–F 成绩记录数（不含 W）；demand_proxy=Students+W 是观测规模，w_mark_share=W/(Students+W) 是派生占比。它们不能替代注册事件、独立学生数、出勤或因果效果。" if lang == "zh" else "This dashboard uses public UIUC GPA course-term aggregates: W is the count of formal Withdraw marks, Students is the final A+–F grade-record count excluding W, demand_proxy=Students+W is observed volume, and w_mark_share=W/(Students+W) is a derived share. They are not registration events, unique students, attendance, or causal effects."))
    st.caption(t("primary_window_note", lang))
    render_dashboard_guide(lang, top_n, model_report.get("profile", {}))
    tabs = st.tabs([t("overview", lang), t("demand", lang), t("prediction", lang), t("profiles", lang), t("data_limits", lang)])
    with tabs[0]:
        st.subheader(t("window", lang))
        coverage = filtered.groupby(["Year", "Term"], as_index=False).size().rename(columns={"size": "course_term_rows"})
        if not coverage.empty:
            coverage["Term"] = coverage["Term"].map(lambda x: term_label(x, lang))
            fig = px.bar(coverage, x="Year", y="course_term_rows", color="Term", barmode="group", text_auto=True, labels={"Year": t("year", lang), "course_term_rows": t("rows", lang), "Term": t("term", lang)})
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
        left, right = st.columns(2)
        with left:
            st.subheader(t("top_courses", lang, n=top_n))
            top = filtered_summary.nlargest(top_n, "demand_proxy_total").copy()
            if top.empty:
                st.info(t("no_rank", lang))
            else:
                top["course"] = course_label(top)
                fig = px.bar(top.sort_values("demand_proxy_total"), x="demand_proxy_total", y="course", orientation="h", labels={"demand_proxy_total": t("demand_total", lang), "course": t("course", lang)}, text_auto=".0f")
                fig.update_layout(height=430, margin=dict(l=10, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            st.caption(t("demand_sum_caption", lang))
        with right:
            overview_source = trajectory_outputs[0] if trajectory_outputs is not None else holdout_metrics
            if trajectory_outputs is not None:
                overview_source = overview_source.loc[(overview_source["split"] == "holdout") & (overview_source["scope"] == "all")].copy()
                st.subheader(t("trajectory_overview_metrics", lang))
                cols = [c for c in ["model", "average_precision_ap", "roc_auc", "f1", "precision", "recall", "balanced_accuracy", "recall_at_20pct"] if c in overview_source.columns]
                show = overview_source[cols].copy().rename(columns={"model": "模型" if lang == "zh" else "Model", "average_precision_ap": "AP", "roc_auc": "ROC-AUC", "recall_at_20pct": "Recall@20%"})
            else:
                st.subheader(t("legacy_overview_metrics", lang))
                cols = [c for c in ["model", "pr_auc", "roc_auc", "f1", "precision", "recall", "balanced_accuracy", "recall_at_k"] if c in overview_source.columns]
                show = overview_source[cols].copy().rename(columns={"model": "模型" if lang == "zh" else "Model", "pr_auc": "AP", "roc_auc": "ROC-AUC", "recall_at_k": "Recall@20%"})
            if not show.empty:
                show.iloc[:, 0] = show.iloc[:, 0].map(lambda x: model_label(x, lang))
                for col in show.columns[1:]:
                    show[col] = show[col].map(fmt_score)
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.caption(t("trajectory_metrics_note" if trajectory_outputs is not None else "legacy_metrics_note", lang))
    with tabs[1]:
        st.subheader(t("demand_trend", lang))
        if filtered.empty:
            st.warning(t("no_data", lang))
        else:
            trend = filtered.groupby(["Year", "Term"], as_index=False).agg(demand_proxy=("demand_proxy", "sum"), w_mark_share=("w_mark_share", "mean"), course_terms=("Subject", "size"))
            trend["Term_label"] = trend["Term"].map(lambda x: term_label(x, lang))
            trend["year_term"] = trend["Year"].astype(str) + " " + trend["Term_label"]
            fig = px.line(trend, x="year_term", y="demand_proxy", markers=True, color="Term_label", labels={"year_term": t("year_term", lang), "demand_proxy": t("demand_total", lang), "Term_label": t("term", lang)})
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            left, right = st.columns(2)
            with left:
                st.subheader(t("top_courses", lang, n=top_n))
                top_rows = filtered.nlargest(top_n, "demand_proxy")[["Year", "Term", "Subject", "Number", "Course Title", "Students", "W", "demand_proxy", "w_mark_share"]].copy()
                top_rows["Term"] = top_rows["Term"].map(lambda x: term_label(x, lang))
                st.dataframe(top_rows, use_container_width=True, hide_index=True)
                st.caption(t("rank_course_term", lang))
            with right:
                st.subheader(t("demand_w_scatter", lang))
                scatter = filtered.sample(min(len(filtered), 5000), random_state=42) if len(filtered) > 5000 else filtered
                scatter = scatter.copy()
                scatter["Term_label"] = scatter["Term"].map(lambda x: term_label(x, lang))
                fig = px.scatter(scatter, x="demand_proxy", y="w_mark_share", color="Term_label", hover_data=["Year", "Subject", "Number", "Course Title", "W"], labels={"demand_proxy": t("observed_proxy_formula", lang), "w_mark_share": t("w_formula", lang), "Term_label": t("term", lang)}, opacity=0.55)
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            w_top = filtered.loc[filtered["demand_proxy"] >= 20].nlargest(top_n, "w_mark_share")[["Year", "Term", "Subject", "Number", "Course Title", "W", "demand_proxy", "w_mark_share"]].copy()
            w_top["Term"] = w_top["Term"].map(lambda x: term_label(x, lang))
            st.subheader(t("stable_w_top", lang, n=top_n))
            st.dataframe(w_top, use_container_width=True, hide_index=True)
            st.caption(t("stable_w_note", lang))
    with tabs[2]:
        st.subheader(t("prediction_title", lang))
        trajectory = load_trajectory_outputs()
        if trajectory is not None:
            render_trajectory(lang, trajectory, top_n, continuity)
        else:
            render_legacy_prediction(lang, label, threshold, operator, model_report, holdout_metrics, predictions, top_n)
    with tabs[3]:
        st.subheader(t("profiles_title", lang))
        profile_meta = model_report.get("profile", {})
        st.markdown(t("profile_explain", lang))
        if profile_meta.get("status") != "ok":
            st.warning(("画像未启用：" + str(profile_meta.get("reason", "未提供原因"))) if lang == "zh" else ("Profiles unavailable: " + str(profile_meta.get("reason", "no reason provided"))))
        else:
            p1, p2, p3 = st.columns(3)
            p1.metric("聚类数 K" if lang == "zh" else "Number of clusters K", fmt_int(profile_meta.get("best_k")))
            p2.metric(t("silhouette", lang), fmt_score(profile_meta.get("silhouette")))
            p3.metric(t("profile_courses", lang), fmt_int(profile_meta.get("train_course_rows")))
            if not profiles.empty and "cluster" in profiles:
                cluster_size = profiles.groupby("cluster", as_index=False).agg(course_count=("Subject", "size"))
                fig = px.bar(cluster_size, x="cluster", y="course_count", text_auto=True, labels={"cluster": t("cluster", lang), "course_count": t("course_keys", lang)})
                st.plotly_chart(fig, use_container_width=True)
                centers = pd.DataFrame(profile_meta.get("cluster_centers", []))
                if not centers.empty and "cluster" in centers:
                    st.dataframe(centers, use_container_width=True, hide_index=True)
                choices = sorted(profiles["cluster"].dropna().unique().tolist())
                chosen = st.selectbox("查看画像簇" if lang == "zh" else "View profile cluster", choices)
                st.dataframe(profiles.loc[profiles["cluster"] == chosen].head(100), use_container_width=True, hide_index=True)
                st.caption(t("profile_similarity_note", lang))
    with tabs[4]:
        st.subheader(t("data_boundaries", lang))
        st.markdown(t("field_title", lang))
        render_field_table(lang, analysis_window)
        st.markdown(t("inventory_title", lang))
        render_inventory(lang)
        st.markdown("### " + t("source_title", lang))
        st.markdown("- GPA：公开 UIUC GPA 成绩分布数据，源粒度为课程-学期-教师成绩分布，本看板聚合到课程-学期；W 是 Withdraw 标记计数，grade_point_mean 是由 A+–F 计数换算的估算平均绩点。" if lang == "zh" else "- GPA: public UIUC GPA grade-distribution data; source grain is course-term-instructor grade distribution, aggregated here to course-term. W is a Withdraw-mark count and grade_point_mean is an estimated mean from A+–F counts.")
        st.markdown("- " + t("instructor_limit_note", lang))
        st.markdown("- 课程安排：当前没有可复现的 section 时间、容量或 waitlist 字段；因此不展示具体冲突值。" if lang == "zh" else "- Scheduling: no reproducible section times, capacity, or waitlist fields are available; no specific conflict values are shown.")
        st.markdown("- 评论文本：没有合法且可匹配的带时间标签文本，情绪/主题结果未启用。" if lang == "zh" else "- Review text: no lawful, matchable time-labelled text is available, so sentiment/topics are not enabled.")
        st.markdown("### " + t("schedule_title", lang))
        render_schedule_questions(lang)
        st.markdown("### " + t("resolution_title", lang))
        st.write("优先补充合法的 section 时间、容量、waitlist、注册/退课事件和授权的 LMS 汇总；每次接入先验证课程键与 join 基数，再做滚动时间验证。" if lang == "zh" else "Prioritise licensed section times, capacity, waitlist, registration/withdrawal events, and authorised LMS aggregates; validate course keys and join cardinality before rolling time validation.")
        st.markdown("### " + t("reproduce_title", lang))
        reproduce = ("1. 生成标准化与指标表\n2. 生成模型和课程画像\n3. python -m streamlit run dashboard/app.py" if lang == "zh" else "1. Run the data-normalisation and metric scripts\n2. Run the model and course-profile scripts\n3. python -m streamlit run dashboard/app.py")
        st.code(reproduce, language="text")
        guide_name = "MODEL_AND_PROXY_GUIDE_ZH.md" if lang == "zh" else "MODEL_AND_PROXY_GUIDE_EN.md"
        guide_path = ROOT / "docs" / guide_name
        if guide_path.exists():
            st.download_button(t("download_label", lang), guide_path.read_bytes(), file_name=guide_name, mime="text/markdown", help=t("download_guide", lang))
        eda = load_trajectory_eda()
        if eda:
            st.markdown("### " + t("eda_title", lang))
            st.caption(t("eda_note", lang))
            eda_view = {key: eda.get(key) for key in ["filtered_rows", "filtered_columns", "reconciliation_all_zero", "pass_rate_or_gpa_available", "drop_semantics"] if key in eda}
            st.json(eda_view)


if __name__ == "__main__":
    main()
