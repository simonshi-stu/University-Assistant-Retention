r"""Local Streamlit dashboard for the reproducible course-retention outputs.

Run from the repository root with:
    .\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


st.set_page_config(page_title="高校课程注册与学习留存分析平台", page_icon="📘", layout="wide")


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_json(name: str) -> dict:
    path = PROCESSED / name
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_int(value: object) -> str:
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def metric_value(metrics: pd.DataFrame, model: str, field: str, split: str = "holdout") -> object:
    row = metrics.loc[(metrics["model"] == model) & (metrics["split"] == split)]
    return None if row.empty else row.iloc[0].get(field)


def aggregate_course_demand(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the active filter scope to course level for ranking charts."""
    if data.empty:
        return pd.DataFrame(
            columns=[
                "Subject",
                "Number",
                "Course Title",
                "demand_proxy_total",
                "course_term_count",
                "W_total",
                "W_proxy_weighted",
            ]
        )
    grouped = (
        data.groupby(["Subject", "Number", "Course Title"], dropna=False, as_index=False)
        .agg(
            demand_proxy_total=("demand_proxy", "sum"),
            course_term_count=("demand_proxy", "size"),
            W_total=("W", "sum"),
        )
    )
    grouped["W_proxy_weighted"] = grouped["W_total"].div(grouped["demand_proxy_total"].where(grouped["demand_proxy_total"] > 0))
    return grouped


def course_label(data: pd.DataFrame) -> pd.Series:
    return data["Subject"].astype(str) + " " + data["Number"].astype(str) + " · " + data["Course Title"].astype(str)


def render_dashboard_guide(top_n: int, rf_pr: object, profile_meta: dict) -> None:
    with st.expander("看板说明：每个页面看什么，以及结论如何使用", expanded=False):
        guide = pd.DataFrame(
            [
                ["总览", "看当前筛选范围的覆盖量、需求代理榜和留出集模型表现。", "高需求课程值得优先关注，但榜单不是注册量或容量排名。"],
                ["需求与 W 代理", "看课程需求代理的时间趋势，以及需求代理与 W 代理的分布关系。", "可以发现描述性关联和需要复核的课程，不能证明退课原因。"],
                ["预测风险", "看按历史信息筛选高 W 代理课程的留出集表现和预测排序。", "模型可用于优先级筛查；不能把概率当成官方退课率或因果效果。"],
                ["课程画像", "看具有相似规模、成绩结构和历史代理特征的课程画像。", "当前两类主要体现小规模与大规模课程观察的差异，不是学生群体或原因分组。"],
                ["数据与限制", "查公式、数据源、可回答问题和缺失字段。", "当页面显示“数据不足”时，优先补充 section 时间、容量或事件级数据，而不是猜测。"],
            ],
            columns=["页面", "主要内容", "当前结论"],
        )
        st.dataframe(guide, use_container_width=True, hide_index=True)
        st.caption(f"当前 Top-N = {top_n}；只作用于带有“前 N 名”标识的榜单，不会改变模型训练或留出集指标。")
        if rf_pr is not None and not pd.isna(rf_pr):
            st.caption(f"当前随机森林留出集 PR-AUC 为 {float(rf_pr):.3f}；它衡量排序/区分表现，不是准确率，也不是退课率。")
        if profile_meta.get("status") == "ok":
            st.caption("课程画像的 K 值由训练期画像特征与轮廓系数选择；画像用于相似性观察，不用于因果解释。")


def render_data_inventory() -> None:
    st.subheader("当前可用数据与分析边界")
    inventory = pd.DataFrame(
        [
            [
                "公开 UIUC GPA 成绩分布",
                "已接入",
                "课程-学期-教师成绩分布；含 Year、Term、Subject、Number、Course Title、各成绩档位与 W",
                "需求代理、W 代理、课程画像、历史特征和时间留出集筛查",
                "不是独立学生表、注册事件、section、容量、waitlist 或 attendance",
            ],
            [
                "UIUC Course Explorer",
                "未纳入当前指标",
                "理论上可提供 section、授课时间等课程安排字段；本次请求被访问保护拦截",
                "若取得合法且可复现的数据，可支持时间冲突、容量和排课变更分析",
                "当前不能回答具体 section 冲突、拥挤时段或调课后的学生变化",
            ],
            [
                "Attendance / LMS / 学生参与",
                "当前不可用",
                "没有合法、可识别且带时间标签的学生级出勤或在线活动数据",
                "未来接入后可分析参与度与课程结果的关联；需遵守隐私与授权",
                "当前不能把 GPA 记录解释成出勤、参与人数或独立学生数",
            ],
            [
                "课程评论 / ICES 文本",
                "未启用",
                "缺少可合法使用、可匹配课程且带时间标签的文本",
                "未来可做主题/情绪与 W 代理的描述性关联",
                "当前不展示情绪分数，也不虚构学生体验结论",
            ],
        ],
        columns=["数据类型", "状态", "目前可见内容", "可以支持什么", "不能支持什么"],
    )
    st.dataframe(inventory, use_container_width=True, hide_index=True)


def render_field_table() -> None:
    st.subheader("字段与指标含义")
    fields = pd.DataFrame(
        [
            ["Year / Term", "课程开设年份与学期；本看板只展示 2021–2023 spring/fall。", "时间过滤与训练/留出切分"],
            ["Subject / Number / Course Title", "课程身份键；标题变化会形成不同课程键。", "课程-学期追踪，不代表 section"],
            ["Students", "源数据中不含 W 的成绩人数。", "需求代理组成部分；不是注册事件数或独立学生数"],
            ["W", "源数据中记录为 W 的人数。", "W proxy 分子；不是官方退课记录时点"],
            ["demand_proxy", "Students + W。", "描述性需求代理，不是 enrollment/capacity/waitlist"],
            ["W_proxy", "W / (Students + W)，仅在计数有效且分母大于 0 时计算。", "退课代理，不是官方 withdrawal/drop rate"],
            ["high_w_risk", "用训练期 W_proxy 阈值定义的高代理风险标签；阈值固定应用于 2023 留出集。", "二分类筛查目标，不是官方退课标签"],
            ["historical_*", "严格早于当前年份的课程历史均值/观察次数。", "可用于预测特征，避免使用未来行"],
            ["PR-AUC / ROC-AUC", "留出集上的排序/区分能力指标。", "类别不平衡时优先关注 PR-AUC"],
            ["Recall@K", "按预测概率排序的留出集前 20% 行覆盖了多少真实高代理风险行。", "检验优先复核排序，不等于总体召回"],
        ],
        columns=["字段/指标", "数据含义", "本项目用途与限制"],
    )
    st.dataframe(fields, use_container_width=True, hide_index=True)


def main() -> None:
    st.title("📘 高校课程注册与学习留存分析平台")
    st.caption("公开 UIUC GPA 数据｜需求与 W 代理｜时间感知风险筛查｜本地可复现看板")

    required = [
        "course_term_demand_metrics.csv",
        "course_demand_summary.csv",
        "phase5_report.json",
        "phase6_feature_table.csv",
        "phase6_model_metrics.csv",
        "phase6_predictions.csv",
        "phase6_course_profiles.csv",
        "phase6_report.json",
    ]
    missing = [name for name in required if not (PROCESSED / name).exists()]
    if missing:
        st.error("缺少分析输出，当前看板无法加载。")
        st.info("请先运行项目分析脚本生成数据产物，再重新打开看板。")
        st.stop()

    course_terms = load_csv("course_term_demand_metrics.csv")
    course_summary = load_csv("course_demand_summary.csv")
    demand_report = load_json("phase5_report.json")
    model_report = load_json("phase6_report.json")
    model_metrics = load_csv("phase6_model_metrics.csv")
    predictions = load_csv("phase6_predictions.csv")
    profiles = load_csv("phase6_course_profiles.csv")
    analysis_window = [int(year) for year in model_report.get("window", [2021, 2022, 2023])]
    course_terms = course_terms.loc[
        course_terms["Year"].isin(analysis_window) & course_terms["Term"].isin(["spring", "fall"])
    ].copy()
    course_summary = course_summary.merge(
        course_terms[["Subject", "Number", "Course Title"]].drop_duplicates(),
        on=["Subject", "Number", "Course Title"],
        how="inner",
        validate="many_to_one",
    )

    st.sidebar.header("筛选器")
    years = sorted(course_terms["Year"].dropna().astype(int).unique().tolist())
    selected_years = st.sidebar.multiselect("年份", years, default=years)
    selected_terms = st.sidebar.multiselect("学期", ["spring", "fall"], default=["spring", "fall"])
    subjects = sorted(course_terms["Subject"].dropna().astype(str).unique().tolist())
    selected_subjects = st.sidebar.multiselect("院系/Subject（可选）", subjects)
    top_n = st.sidebar.slider("图表显示前 N 名", 5, 25, 10)
    st.sidebar.caption("年份、学期和院系筛选作用于数据图表与榜单；模型指标和预测不在看板内重新训练。")
    st.sidebar.caption("Top-N 只作用于总览需求榜、需求榜、W 代理榜、预测排序和特征重要性榜。")

    filtered = course_terms.loc[course_terms["Year"].isin(selected_years) & course_terms["Term"].isin(selected_terms)].copy()
    if selected_subjects:
        filtered = filtered.loc[filtered["Subject"].isin(selected_subjects)].copy()
    filtered_course_summary = aggregate_course_demand(filtered)
    holdout_metrics = model_metrics.loc[model_metrics["split"] == "holdout"].copy()
    threshold = model_report.get("label", {}).get("threshold")
    threshold_operator = model_report.get("label", {}).get("operator", ">=")
    rf_pr = metric_value(model_metrics, "random_forest", "pr_auc")
    lr_pr = metric_value(model_metrics, "logistic_regression", "pr_auc")

    kpi = st.columns(6)
    kpi[0].metric("筛选后课程-学期行", fmt_int(len(filtered)))
    kpi[1].metric("筛选后课程键", fmt_int(filtered[["Subject", "Number", "Course Title"]].drop_duplicates().shape[0]))
    kpi[2].metric("筛选后 Students", fmt_int(filtered["Students"].sum()))
    kpi[3].metric("筛选后 W", fmt_int(filtered["W"].sum()))
    threshold_text = "—" if threshold is None or pd.isna(threshold) else f"{threshold_operator} {float(threshold):.4f}"
    kpi[4].metric("风险标签阈值", threshold_text)
    kpi[5].metric("RF holdout PR-AUC", fmt_pct(rf_pr, 1))

    if threshold_operator == ">":
        st.warning("训练期 W 代理的第 75 百分位为 0，因大量 0 值并列，标签采用严格 W 代理 > 0；这样才能保留正类与负类。")
    st.info("本看板使用公开的课程-学期聚合成绩分布，展示需求代理与 W 代理的描述性关联。它不代表官方退课率、注册事件、出勤或因果留存效果。")
    render_dashboard_guide(top_n, rf_pr, model_report.get("profile", {}))

    tabs = st.tabs(["总览", "需求与 W 代理", "预测风险", "课程画像", "数据与限制"])

    with tabs[0]:
        st.subheader("当前数据窗口")
        coverage = filtered.groupby(["Year", "Term"], as_index=False).size().rename(columns={"size": "course_term_rows"})
        if not coverage.empty:
            fig = px.bar(coverage, x="Year", y="course_term_rows", color="Term", barmode="group", text_auto=True, labels={"Year": "年份", "course_term_rows": "课程-学期行", "Term": "学期"})
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
        left, right = st.columns(2)
        with left:
            st.subheader(f"当前筛选范围内需求代理前 {top_n} 名")
            top = filtered_course_summary.nlargest(top_n, "demand_proxy_total").copy()
            if top.empty:
                st.info("当前筛选没有可用于排名的课程。")
            else:
                top["course"] = course_label(top)
                fig = px.bar(top.sort_values("demand_proxy_total"), x="demand_proxy_total", y="course", orientation="h", labels={"demand_proxy_total": "需求代理合计", "course": "课程"}, text_auto=".0f")
                fig.update_layout(height=430, margin=dict(l=10, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            st.caption("需求代理合计 = 当前筛选范围内各课程-学期的 Students + W 之和；榜单受左侧筛选和 Top-N 共同控制。")
        with right:
            st.subheader("留出集指标")
            show = holdout_metrics[["model", "pr_auc", "roc_auc", "f1", "precision", "recall", "balanced_accuracy", "recall_at_k"]].copy()
            show.columns = ["模型", "PR-AUC", "ROC-AUC", "F1", "Precision", "Recall", "Balanced accuracy", "Recall@K"]
            for col in show.columns[1:]:
                show[col] = show[col].map(lambda x: "—" if pd.isna(x) else f"{float(x):.3f}")
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.caption("留出集为 2023；阈值、预处理和模型参数在分析前固定，筛选器不会重新训练模型。")

    with tabs[1]:
        st.subheader("需求代理趋势与课程分布")
        if filtered.empty:
            st.warning("当前筛选没有数据。")
        else:
            trend = filtered.groupby(["Year", "Term"], as_index=False).agg(demand_proxy=("demand_proxy", "sum"), w_proxy=("W_proxy", "mean"), course_terms=("Subject", "size"))
            trend["year_term"] = trend["Year"].astype(str) + " " + trend["Term"]
            fig = px.line(trend, x="year_term", y="demand_proxy", markers=True, color="Term", labels={"year_term": "年-学期", "demand_proxy": "需求代理总和", "Term": "学期"})
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            left, right = st.columns(2)
            with left:
                st.subheader(f"筛选范围内需求代理前 {top_n} 名")
                top_rows = filtered.nlargest(top_n, "demand_proxy")[["Year", "Term", "Subject", "Number", "Course Title", "Students", "W", "demand_proxy", "W_proxy"]].copy()
                st.dataframe(top_rows, use_container_width=True, hide_index=True)
                st.caption("这里按课程-学期行排名；Top-N 只改变显示数量，不改变趋势图。")
            with right:
                st.subheader("需求与 W proxy")
                scatter = filtered.sample(min(len(filtered), 5000), random_state=42) if len(filtered) > 5000 else filtered
                fig = px.scatter(scatter, x="demand_proxy", y="W_proxy", color="Term", hover_data=["Year", "Subject", "Number", "Course Title"], labels={"demand_proxy": "需求代理 = Students + W", "W_proxy": "W proxy", "Term": "学期"}, opacity=0.55)
                fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            w_top = filtered.loc[filtered["demand_proxy"] >= 20].nlargest(top_n, "W_proxy")[["Year", "Term", "Subject", "Number", "Course Title", "demand_proxy", "W_proxy"]]
            st.subheader(f"分母稳定性筛选后的 W 代理前 {top_n} 名")
            st.dataframe(w_top, use_container_width=True, hide_index=True)
            st.caption("仅保留需求代理 ≥ 20 的课程-学期行，以减少小分母导致的极端比例；Top-N 只改变显示数量。")

    with tabs[2]:
        st.subheader("时间感知高 W 代理风险筛查")
        label = model_report.get("label", {})
        a, b, c, d = st.columns(4)
        a.metric("训练行", fmt_int(label.get("training_valid_proxy_rows")))
        b.metric("训练正类", fmt_int(label.get("training_positive_count")))
        c.metric("留出行", fmt_int(label.get("holdout_valid_proxy_rows")))
        d.metric("留出正类", fmt_int(label.get("holdout_positive_count")))
        st.write(f"标签规则：训练期 W 代理第 {float(label.get('quantile', .75)) * 100:.0f} 百分位为 `{float(threshold):.4f}`，实际使用 `{threshold_operator}`；训练年份为 {model_report.get('train_years')}，留出年为 {model_report.get('holdout_year')}。")
        chart_metrics = holdout_metrics.loc[holdout_metrics["model"] != "majority_baseline", ["model", "pr_auc", "roc_auc", "f1", "recall", "recall_at_k"]].melt(id_vars="model", var_name="metric", value_name="value")
        if not chart_metrics.empty:
            fig = px.bar(chart_metrics, x="metric", y="value", color="model", barmode="group", text_auto=".3f", labels={"metric": "指标", "value": "分数", "model": "模型"})
            fig.update_yaxes(range=[0, 1])
            fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        show = holdout_metrics[["model", "status", "rows", "positive_count", "negative_count", "pr_auc", "roc_auc", "f1", "precision", "recall", "balanced_accuracy", "brier_score", "recall_at_k", "tn", "fp", "fn", "tp"]].copy()
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption("PR-AUC 比 accuracy 更适合这个不平衡标签；Logistic Regression 用于解释方向，Random Forest 用于比较非线性排序表现。")

        if not predictions.empty:
            fitted = [m for m in ["random_forest", "logistic_regression"] if m in predictions["model"].unique()]
            default_model = "random_forest" if "random_forest" in fitted else (fitted[0] if fitted else None)
            if default_model:
                model_pick = st.selectbox("查看预测排序", fitted, index=fitted.index(default_model))
                pred = predictions.loc[(predictions["split"] == "holdout") & (predictions["model"] == model_pick)].copy()
                pred = pred.sort_values("predicted_probability", ascending=False).head(top_n)
                st.subheader(f"{model_pick}：2023 留出集预测概率最高课程")
                st.dataframe(pred[["Year", "Term", "Subject", "Number", "Course Title", "actual_high_w_risk", "predicted_probability", "predicted_high_w_risk", "W_proxy"]], use_container_width=True, hide_index=True)

        importance_path = PROCESSED / "phase6_feature_importance.csv"
        if importance_path.exists():
            importance = load_csv("phase6_feature_importance.csv")
            importance_models = sorted(importance["model"].dropna().unique().tolist())
            if importance_models:
                model_pick = st.selectbox("查看特征重要性", importance_models, key="importance_model")
                imp = importance.loc[importance["model"] == model_pick].nlargest(top_n, "importance").sort_values("importance")
                if not imp.empty:
                    fig = px.bar(imp, x="importance", y="feature", orientation="h", color="direction" if model_pick == "logistic_regression" else None, labels={"importance": "重要性/系数绝对值", "feature": "编码后特征", "direction": "Logistic 系数方向"})
                    fig.update_layout(height=500, margin=dict(l=10, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(f"特征重要性图显示当前模型的前 {top_n} 个特征；Top-N 只改变显示数量，不改变模型。")
            else:
                st.info("没有可用的模型特征重要性（例如训练目标只有一个类别）。")

    with tabs[3]:
        st.subheader("K-Means 课程画像（仅描述相似性）")
        profile_meta = model_report.get("profile", {})
        if profile_meta.get("status") != "ok":
            st.warning(f"画像未启用：{profile_meta.get('reason', '未提供原因')}")
        else:
            p1, p2, p3 = st.columns(3)
            p1.metric("聚类数 K", fmt_int(profile_meta.get("best_k")))
            p2.metric("Silhouette", f"{float(profile_meta.get('silhouette', 0)):.3f}")
            p3.metric("训练课程键", fmt_int(profile_meta.get("train_course_rows")))
            cluster_size = profiles.groupby("cluster", as_index=False).agg(course_count=("Subject", "size"))
            fig = px.bar(cluster_size, x="cluster", y="course_count", text_auto=True, labels={"cluster": "画像簇", "course_count": "课程键数"})
            fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            centers = pd.DataFrame(profile_meta.get("cluster_centers", []))
            if not centers.empty and "cluster" in centers:
                centers = centers.copy()
                centers["画像含义"] = centers.apply(
                    lambda row: "相对较小规模课程：训练期 Students / 历史需求代理均较低"
                    if float(row.get("Students", 0)) < float(centers["Students"].median())
                    else "相对较大规模课程：训练期 Students / 历史需求代理均较高",
                    axis=1,
                )
                center_view = centers[["cluster", "画像含义", "Students", "historical_demand_proxy_mean", "W_proxy", "historical_w_proxy_mean"]].copy()
                center_view.columns = ["画像簇", "画像含义", "典型 Students", "历史需求代理均值", "当期 W 代理", "历史 W 代理均值"]
                st.dataframe(center_view, use_container_width=True, hide_index=True)
                st.caption("当前 K=2 的主要差异是规模与历史观测量：画像簇 0 约有 2,784 个课程键，画像簇 1 约有 111 个课程键。两类的 W 代理中心相近，不能据此说某一类更容易退课。")
            with st.expander("为什么使用 K-Means，而不是其他无监督方法？"):
                st.markdown(
                    "K-Means 适合本项目的第一版课程画像：它对标准化后的数值特征运行快、实现简单，"
                    "并且可以用聚类中心解释每类课程的典型规模、成绩结构和历史代理水平。这里的目标是发现相似观察，不是预测原因。"
                )
                st.markdown(
                    "当前不优先使用层次聚类、DBSCAN 或高维文本聚类：层次聚类在课程数量扩大后更难维护，"
                    "DBSCAN 对密度和参数敏感且会产生噪声点，而评论文本数据尚未合法、稳定接入。若未来出现明显非球形结构、"
                    "大量异常点或文本特征，应再用这些方法做稳定性对照，而不是直接替换当前画像。"
                )
            chosen_cluster = st.selectbox("查看画像簇", sorted(profiles["cluster"].unique().tolist()))
            st.dataframe(profiles.loc[profiles["cluster"] == chosen_cluster].head(100), use_container_width=True, hide_index=True)
            st.caption("聚类特征来自训练期课程汇总，包含成绩结构、课程规模、历史需求和 W 代理；它只描述相似性，不能解释退课原因，也不是因果分组。")

    with tabs[4]:
        st.subheader("数据口径、来源与不能回答的问题")
        render_field_table()
        render_data_inventory()
        st.markdown("### 数据来源")
        st.markdown("- GPA 数据：公开 UIUC GPA 数据集；源粒度为课程-学期-教师成绩分布，本看板聚合到课程-学期。")
        st.markdown("- Course Explorer：六次 2021–2023 请求被 WAF challenge 阻断，因此没有 section 课表。")
        st.markdown("- 评论/ICES：无合法、可识别课程且带时间标签的文本，评论情感分析未启用。")
        st.markdown("### 右上角 Deploy 是什么？")
        st.write("Deploy 是 Streamlit 宿主界面提供的发布入口。当前项目本身仍是本地运行：点击它不会把文件自动部署到你的电脑，也不会替看板创建服务器。若选择 Community Cloud，需要把仓库和依赖交给云端运行；选择其他平台则需要自行准备运行环境、访问控制和成本预算。")
        st.markdown("### 未来拓展与价值")
        st.write("从单校扩展到多校有意义：高校管理者、课程负责人、教务规划团队和教育研究者都可能需要跨学期比较课程需求、风险代理和数据质量。但跨校比较前必须统一课程身份、学期定义、成绩口径、隐私授权和数据许可；更稳妥的路径是先接入少量数据字典清晰、许可明确的高校，保留校内结果与跨校结果的分层展示，避免把不同学校的代理值直接横比。")
        st.markdown("### 五个排课问题的当前状态")
        scheduling = pd.DataFrame(
            [
                ["冲突权重最高的课程组合", "不能回答", "缺少可复现的 section meeting day/start/end 时间字段"],
                ["高需求课程最拥挤的时间段", "不能回答", "缺少 section 时间与容量；本看板的 year/term 不是时段"],
                ["核心课冲突最集中的院系", "不能回答", "缺少 section 冲突图与 core-course 标识"],
                ["只能进入低需求时间段的课程", "不能回答", "缺少课程可行时间槽与实际安排变化"],
                ["改时间后后续学生数/需求变化", "不能回答", "缺少 section 安排变更历史与可比后续需求观测"],
            ],
            columns=["问题", "结论", "证据/缺失字段"],
        )
        st.dataframe(scheduling, use_container_width=True, hide_index=True)
        st.markdown("### 当前不足的解决路径")
        resolution = pd.DataFrame(
            [
                ["没有出勤/参与人数", "无法从 GPA 表补出；需要学校授权的 LMS/attendance 或公开汇总。", "在获得前，用课程-学期规模、W 代理和历史成绩结构做需求筛查，并明确这是代理。"],
                ["没有 section 时间、容量和 waitlist", "优先使用合法公开课表接口、学期快照或教务导出，并先做键与基数校验。", "暂时只回答课程级需求分布，不把年/学期当作上课时段。"],
                ["W 代理不是官方退课率", "若取得注册/退课事件，可建立事件级分母和时间窗。", "继续使用 W 代理，但把结论限定为描述性关联和复核优先级。"],
                ["模型留出年只有一个年份", "未来累积更多年份后做滚动时间验证。", "当前只把结果作为 2023 的时间留出筛查，不声称部署保证。"],
                ["K-Means 受特征尺度和 K 影响", "增加稳定性、替代算法和跨年份复核。", "当前报告聚类中心、规模和轮廓系数，不把簇当成因果类别。"],
            ],
            columns=["不足", "直接解决渠道", "当前可行的替代方案"],
        )
        st.dataframe(resolution, use_container_width=True, hide_index=True)
        st.markdown("### 复现")
        st.code("1. 运行仓库中的需求与数据分析脚本\n2. 运行仓库中的风险筛查脚本\n3. .\\.venv\\Scripts\\python.exe -m streamlit run dashboard\\app.py", language="text")


if __name__ == "__main__":
    main()
