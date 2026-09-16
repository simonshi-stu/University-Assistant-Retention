"""Small, dependency-free bilingual vocabulary for the local dashboard.

The dashboard keeps one data layer and swaps only presentation strings.  Keeping
the vocabulary in one module also makes it possible to check that the Chinese
and English surfaces stay in sync as pages evolve.
"""

from __future__ import annotations

from typing import Mapping


LANGUAGES = {"中文": "zh", "English": "en"}


TEXT: Mapping[str, Mapping[str, str]] = {
    "page_title": {"zh": "高校课程注册与学习留存分析平台", "en": "Course Enrollment and Learning Retention Explorer"},
    "language": {"zh": "语言 / Language", "en": "语言 / Language"},
    "zh": {"zh": "中文", "en": "Chinese"},
    "en": {"zh": "English", "en": "English"},
    "subtitle": {"zh": "公开 UIUC GPA 成绩分布数据｜课程规模与 W 标记｜时间感知筛查｜本地可复现", "en": "Public UIUC GPA grade-distribution data | course volume and W marks | time-aware screening | reproducible locally"},
    "filter": {"zh": "筛选器", "en": "Filters"},
    "years": {"zh": "年份", "en": "Years"},
    "terms": {"zh": "学期", "en": "Terms"},
    "subjects": {"zh": "院系 / Subject（可选）", "en": "Department / Subject (optional)"},
    "top_n": {"zh": "图表显示前 N 名", "en": "Top N shown in charts"},
    "filter_note": {"zh": "年份、学期和院系筛选作用于描述性图表与榜单；模型结果不会在浏览器中重训。", "en": "Year, term, and department filters affect descriptive charts and rankings; models are not retrained in the browser."},
    "top_note": {"zh": "Top-N 只作用于标题明确标注的榜单。", "en": "Top N only changes rankings whose titles say so."},
    "overview": {"zh": "总览", "en": "Overview"},
    "demand": {"zh": "课程规模与 W 标记", "en": "Course volume & W marks"},
    "prediction": {"zh": "预测筛查", "en": "Prediction screening"},
    "profiles": {"zh": "课程画像", "en": "Course profiles"},
    "data_limits": {"zh": "数据与限制", "en": "Data & limits"},
    "rows": {"zh": "课程-学期行", "en": "course-term rows"},
    "course_keys": {"zh": "稳定课程键（Subject+Number）", "en": "Stable course keys (Subject+Number)"},
    "students": {"zh": "Students（结课后 A+–F 最终成绩记录）", "en": "Students (post-course A+–F final-grade records)"},
    "students_definition": {"zh": "Students 表示课程结课后 A+–F 最终成绩记录规模（不含 W）；不是去重学生数、报名人数或 section 人数。", "en": "Students is the post-course A+–F final-grade record count excluding W; it is not a unique-student count, sign-up count, or section headcount."},
    "w_count": {"zh": "W 标记数", "en": "W marks"},
    "threshold": {"zh": "W 标签阈值", "en": "W-label threshold"},
    "rf_ap": {"zh": "模型 AP（留出集）", "en": "Model AP (holdout)"},
    "observed_proxy": {"zh": "已观察课程规模代理", "en": "observed course-volume proxy"},
    "observed_proxy_formula": {"zh": "已观察课程规模代理 = Students + W", "en": "observed course-volume proxy = Students + W"},
    "w_formula": {"zh": "W 标记占比（派生）= W / (Students + W)", "en": "W-mark share (derived) = W / (Students + W)"},
    "no_data": {"zh": "当前筛选没有可用数据。", "en": "No data is available for the current filters."},
    "no_rank": {"zh": "当前筛选没有可用于排名的课程。", "en": "No courses can be ranked for the current filters."},
    "window": {"zh": "当前数据窗口", "en": "Current data window"},
    "primary_window_note": {"zh": "主分析重点窗口为 2021–2023：左侧年份筛选、课程规模图表和旧三年模型均限于这三年。2019–2024 的同课程轨迹是独立延伸；2024 仅作连接与真值留出，不替换主窗口。", "en": "The primary analysis focus window is 2021–2023: the year filter, course-volume charts, and legacy three-year model are limited to these years. The 2019–2024 same-course trajectory is a separate extension; 2024 is used only as a bridge and truth-only holdout, not as a replacement for the primary window."},
    "year": {"zh": "年份", "en": "Year"},
    "term": {"zh": "学期", "en": "Term"},
    "year_term": {"zh": "年-学期", "en": "Year-term"},
    "course": {"zh": "课程", "en": "Course"},
    "demand_total": {"zh": "已观察课程规模代理合计", "en": "Observed course-volume proxy total"},
    "demand_sum_caption": {"zh": "合计 = 当前筛选范围内各课程-学期的 Students + W 之和；榜单按稳定 Subject+Number 课程键汇总，每个键只保留一个代表性标题，标题变体不另计课程键；该榜单受左侧筛选和 Top-N 控制。", "en": "Total is the sum of Students + W across course-term rows in the selected scope. Rankings aggregate by stable Subject+Number course key, keep one representative title per key, and do not count title variants as separate keys; the ranking follows the filters and Top N."},
    "holdout_metrics": {"zh": "时间留出集指标", "en": "Time holdout metrics"},
    "trajectory_overview_metrics": {"zh": "2024 六年扩展留出指标（全部范围）", "en": "2024 six-year extension holdout metrics (all scope)"},
    "legacy_overview_metrics": {"zh": "旧三年实验留出指标（历史对照）", "en": "Legacy three-year holdout metrics (historical comparison)"},
    "trajectory_metrics_note": {"zh": "来自 2019–2024 独立课程轨迹扩展；指标只纳入完整历史 lag1–3 的 2024 观察，普通课程按前一日历年任一学期匹配，单季课程按同季匹配。", "en": "From the independent 2019–2024 course-trajectory extension; metrics include only 2024 observations with complete lag1–3 history, using any prior term for ordinary courses and same-season history for one-season courses."},
    "legacy_metrics_note": {"zh": "这是旧三年实验的历史对照，不是六年扩展的最终指标。", "en": "This is the legacy three-year experiment for historical comparison, not the final six-year extension metrics."},
    "w_anomaly_warning": {"zh": "数据复核提示：{periods} 的 W 观察量异常偏低（来自报告汇总）；不要自动解释为政策、教学或学生行为变化。", "en": "Data-review note: W observations are unusually low in {periods} according to the report summary; do not automatically interpret this as a policy, teaching, or student-behaviour change."},
    "metrics_note": {"zh": "指标来自预先生成的时间留出集；筛选器不会改变训练数据、标签阈值或模型参数。", "en": "Metrics come from a pre-generated time holdout; filters do not change training data, label thresholds, or model parameters."},
    "demand_trend": {"zh": "已观察课程规模代理趋势与课程分布", "en": "Observed course-volume proxy trend and course distribution"},
    "top_courses": {"zh": "筛选范围内已观察课程规模代理前 {n} 名", "en": "Top {n} observed course-volume proxy in the selected scope"},
    "rank_course_term": {"zh": "这里按课程-学期行排名；Top-N 只改变显示数量，不改变趋势图。", "en": "This ranks course-term rows; Top N changes only the number shown, not the trend chart."},
    "demand_w_scatter": {"zh": "已观察课程规模代理与 W 标记占比", "en": "Observed course-volume proxy and W-mark share"},
    "stable_w_top": {"zh": "分母稳定性筛选后的 W 标记占比前 {n} 名", "en": "Top {n} W-mark share after denominator-stability filtering"},
    "stable_w_note": {"zh": "仅保留已观察课程规模代理 ≥ 20 的课程-学期行，以减少小分母导致的极端派生占比；W 本身仍是 W 标记计数。", "en": "Only course-term rows with observed course-volume proxy ≥ 20 are kept to reduce extreme derived shares from small denominators; W itself remains a count of W marks."},
    "prediction_title": {"zh": "时间感知 W 标记筛查", "en": "Time-aware screening for W marks"},
    "training_rows": {"zh": "训练行", "en": "Training rows"},
    "training_positive": {"zh": "训练正类", "en": "Training positives"},
    "holdout_rows": {"zh": "留出行", "en": "Holdout rows"},
    "holdout_positive": {"zh": "留出正类", "en": "Holdout positives"},
    "label_rule": {"zh": "标签规则：训练期 W 代理第 {q}% 百分位为 {threshold}，实际使用 {operator}；训练年份为 {train}，留出年份为 {holdout}。目标是是否出现 W 标记，不是高退课概率。", "en": "Label rule: the training-period W proxy {q}th percentile is {threshold}; the applied operator is {operator}. Training years: {train}; holdout year: {holdout}. The target is whether a W mark appears, not a high withdrawal probability."},
    "tie_warning": {"zh": "训练期 W 代理的第 75 百分位为 0，因大量 0 值并列，标签采用严格 W 代理 > 0，以保留正类与负类。", "en": "The training-period 75th percentile of W proxy is 0. Because many zeros are tied, the strict W proxy > 0 rule preserves both classes."},
    "prediction_explain": {"zh": "模型用于复核优先级筛查，不是官方退课率、部署保证或因果效果。Average Precision（AP）衡量排序质量；Brier score 越低越好，表示概率校准误差更小。", "en": "Models support review prioritisation, not an official withdrawal rate, deployment guarantee, or causal effect. Average Precision (AP) measures ranking quality; lower Brier score is better because probability error is smaller."},
    "confusion_explain": {"zh": "混淆矩阵：TP=正确识别有 W，FP=误报有 W，FN=漏掉有 W，TN=正确识别无 W。Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1=2PR/(P+R)，balanced accuracy=(Recall+Specificity)/2，ROC-AUC 衡量排序区分度，Recall@20% 是预测最高 20% 行覆盖的真实正类比例。", "en": "Confusion matrix: TP correctly identifies a W, FP is a false W alert, FN misses a W, and TN correctly identifies no W. Precision=TP/(TP+FP), Recall=TP/(TP+FN), F1=2PR/(P+R), balanced accuracy=(Recall+Specificity)/2, ROC-AUC measures ranking discrimination, and Recall@20% is the share of true positives covered by the top 20% of scored rows."},
    "trajectory_title": {"zh": "2024 同课程历史匹配预测与实际", "en": "2024 stable-course history prediction vs actual"},
    "trajectory_note": {"zh": "这是独立的 2019–2024 同课程轨迹延伸，不替换主分析的 2021–2023 窗口；2024 结果只作连接和真值留出比较。课程身份固定为 Subject + Number；Course Title 只用于展示和改名审计，不再把标题变化拆成新课程。普通课程按前一日历年的任一 Spring/Fall 记录取历史；只在单一季节开设的课程才按同季匹配。可识别的 Special/Selected Topics 在连续性和模型前先单独放置并保留审计表。表中目标是是否出现 W 标记，不是官方退课概率。", "en": "This is a separate 2019–2024 same-course trajectory extension, not a replacement for the primary 2021–2023 window; 2024 is shown only as a bridge and truth-only holdout. Course identity is fixed as Subject + Number; Course Title is display-only and audited, so title changes do not split a new course. Ordinary courses use either Spring/Fall from each prior calendar year; genuinely one-season courses use the same season. Recognisable Special/Selected Topics are set aside before continuity/modeling and retained in an audit table. The target is whether a W mark appears, not an official withdrawal probability."},
    "continuity_title": {"zh": "课程开设连续性与季节性诊断", "en": "Course offering continuity and seasonality"},
    "continuity_note": {"zh": "这里的 12 个格子是 2019–2024 × Spring/Fall 的实际观测格，不存在的学期不填 0。课程按 Subject + Number 统计；标题改名只进入审计。普通课程的历史资格按前一日历年任一学期判断，真正单季课程才按同季判断。Special/Selected Topics 按行暂放：special-only 键不入普通连续性，和普通行重叠的键保留普通行；涉及键总数不等于完全排除键数，具体分解见下一行。", "en": "The 12 cells are actual 2019–2024 × Spring/Fall observations; absent terms are not filled with zero. Courses are counted by Subject + Number and title changes go to audit only. Ordinary-course history uses either term in a prior calendar year; genuinely one-season courses use the same term. Special/Selected Topics are set aside at row level: special-only keys are excluded from ordinary continuity, overlapping keys retain their ordinary rows, and involved keys are not all fully excluded; see the next line for the count breakdown."},
    "continuity_scope_note": {"zh": "连续性是该公开源中“观察到课程-学期行”的覆盖诊断，不是课程实际开设、取消或学生留存的证明；缺失格表示源中没有该观测行，不能当作 0。2021–2023 的分布按课程号计算这三个年份中实际出现了几个年份；出现 3 年不表示三个年份都同时有 Spring 和 Fall。", "en": "Continuity diagnoses coverage of observed course-term rows in this public source; it does not prove that a course was offered, cancelled, or retained students. A missing cell means no such observed row in the source and must not be treated as zero. The 2021–2023 distribution counts how many of the three calendar years have at least one observed row per course key; appearing in all three years does not mean both Spring and Fall were observed in every year."},
    "continuity_evidence_title": {"zh": "间断课程的可核验观察分布", "en": "Auditable observation distribution for intermittent courses"},
    "continuity_evidence_note": {"zh": "每一行是一个稳定课程号；观察学期数和 observed_periods 直接来自生成表，可逐行复核“间断”计数。", "en": "Each row is one stable course number; observed-period counts and observed_periods come directly from the generated table and can be checked row by row."},
    "primary_window_evidence": {"zh": "重点窗口 2021–2023：按课程号统计三个年份中实际出现了几个年份；2024 作为连接/留出年份单独显示。这个分布是观察覆盖证据，不是课程容量、注册量或每年双学期开设证明。", "en": "Focus window 2021–2023: count how many of the three years actually have an observed row for each course key; 2024 is shown separately as the bridge/holdout year. This distribution is evidence of observed coverage, not course capacity, registration volume, or proof of both terms being offered each year."},
    "special_topic_note": {"zh": "Special/Selected Topics 已按行暂放：{rows} 条原始记录涉及 {keys} 个稳定键；其中 {overlap} 个与普通标题重叠并保留普通标题记录，{only} 个为 special-only 键并完全排除。只有 special-only 键不参与连续性比例或模型。", "en": "Special/Selected Topics are set aside at row level: {rows} source records involve {keys} stable keys; {overlap} overlap with ordinary-title records and those ordinary rows are retained, while {only} are special-only keys and fully excluded. Only special-only keys are excluded from continuity shares and models."},
    "special_topic_metadata_unavailable": {"zh": "Special/Selected Topics 已按行暂放：{rows} 条原始记录。当前 metadata 未提供“涉及稳定键 / overlap 保留 / special-only 完全排除”的分解，因此不把旧字段解读为完整键排除数。", "en": "Special/Selected Topics are set aside at row level: {rows} source records. Current metadata does not provide the breakdown of involved stable keys, retained overlaps, and fully excluded special-only keys, so legacy fields are not interpreted as whole-key exclusions."},
    "w_semantics_note": {"zh": "W = Withdraw 的正式 W 标记计数。业务口径仅适用于标准 16 周本科课程的一般解释：正式 W 通常是在课程过半、约第 8 周之后留下；W=0 与当前期末成绩记录中未观察到该类 W 一致，不应解释为课程突然变难。源表没有周次、退课事件或日期字段，因此不能从 W=0 证明学生适应，也不能排除更早 drop。", "en": "W is the count of formal Withdraw marks. As a business interpretation for a standard 16-week undergraduate course only, a formal W is generally recorded after the midpoint, roughly after week 8. W=0 is consistent with no such W observed in the final-grade records and should not be interpreted as a sudden increase in difficulty. The source has no week, withdrawal-event, or date fields, so W=0 cannot prove student adaptation or rule out an earlier drop."},
    "gpa_estimate_note": {"zh": "源数据没有数值 GPA，也不是学生级 GPA 表；页面可用的 grade_point_mean 是由 A+–F 计数按 4.0 风格换算的估算平均绩点，仅用于同课程历史反馈参考，不是官方 GPA。", "en": "The source has no numeric GPA and is not a student-level GPA table; grade_point_mean is a 4.0-style estimate from A+–F counts for historical course feedback, not an official GPA."},
    "instructor_limit_note": {"zh": "Primary Instructor 来自课程-学期-教师成绩分布；同一课程-学期可能有多名教师，且源表没有 section id。因此教师数量和姓名只作课程-学期审计上下文，不能代表某个 section、比较教师教学难度，或把 W 归因给教师。", "en": "Primary Instructor comes from the course-term-instructor grade distribution; one course-term may have multiple instructors and the source has no section id. Instructor counts and names are audit context only: they do not identify a section, support teacher-difficulty comparisons, or attribute W to an instructor."},
    "continuity_class": {"zh": "连续性分类", "en": "Continuity class"},
    "backtest_eligible": {"zh": "2024 可回测", "en": "2024 backtest eligible"},
    "excluded_reason": {"zh": "排除原因", "en": "Exclusion reason"},
    "prediction_error_note": {"zh": "误差 = 模型分数 − 实际 W 标记（0/1）；这是二分类筛查误差。本模块不计算校准区间，因此不要把分数当作官方退课概率。", "en": "Error = model score − actual W mark (0/1); this is binary-screening error. No calibrated interval is computed here, so the score must not be read as an official withdrawal probability."},
    "eda_title": {"zh": "可复现 EDA 摘要", "en": "Reproducible EDA summary"},
    "eda_note": {"zh": "EDA 使用 2019–2024 Spring/Fall 原始切片，并记录规模、字段、缺失、重复、覆盖、分布、汇总核对和连接基数。", "en": "EDA uses the 2019–2024 Spring/Fall source slice and records size, fields, missingness, duplicates, coverage, distributions, reconciliation, and join cardinality."},
    "prediction_ranking": {"zh": "模型预测排序前 {n} 名", "en": "Top {n} model predictions"},
    "feature_importance": {"zh": "模型特征排序前 {n} 名", "en": "Top {n} model features"},
    "coefficients": {"zh": "Logistic 系数", "en": "Logistic coefficients"},
    "coverage": {"zh": "2024 覆盖", "en": "2024 coverage"},
    "metrics_scope": {"zh": "指标范围", "en": "Metric scope"},
    "logistic_explain": {"zh": "数值特征已标准化；一个系数单位表示该特征增加一个标准差时，在其他特征固定的条件下，W 标签 log-odds 的方向变化。正负号只表示模型内方向，abs(coef) 只用于同一模型内排序；odds ratio=exp(coef)。分类变量以明确的 reference 类别比较。系数是关联，不是因果。", "en": "Numeric features are standardised. One coefficient unit describes the direction of change in W-label log-odds for a one-standard-deviation increase, holding other features fixed. Sign gives model-internal direction; abs(coef) ranks features only within this model; odds ratio=exp(coef). Categorical variables are compared with an explicit reference category. Coefficients are associations, not causal effects."},
    "profiles_title": {"zh": "K-Means 课程规模画像（探索性附录）", "en": "K-Means course-volume profiles (exploratory appendix)"},
    "profile_explain": {"zh": "K-Means 只做探索性课程规模画像，不用于预测，也没有强决策价值。数值先标准化并以中位数填补；候选 K=2..5，n_init=20，以 silhouette 选 K；距离是标准化欧氏距离，中心是均值向量，不是人工定义的课程。当前差异主要是普通规模与超大规模，因为 Students=grade_total，历史 demand≈Students 的重复加权，W 中心接近。", "en": "K-Means is an exploratory course-volume appendix, not a predictor and not a strong decision tool. Numeric inputs are median-imputed and standardised; K=2..5 with n_init=20, selecting K by silhouette. Distance is standardised Euclidean distance and each centre is a mean vector, not a manually defined course. The current separation is mainly ordinary versus very large volume because Students=grade_total and historical demand≈Students is repeatedly weighted; W centres are close."},
    "cluster": {"zh": "画像簇", "en": "Profile cluster"},
    "silhouette": {"zh": "Silhouette", "en": "Silhouette"},
    "profile_courses": {"zh": "训练课程键", "en": "Training course keys"},
    "profile_similarity_note": {"zh": "画像只描述相似性，不代表学生群体、退课原因或因果类别。", "en": "Profiles describe similarity only; they are not student groups, withdrawal causes, or causal categories."},
    "data_boundaries": {"zh": "数据口径、来源与不能回答的问题", "en": "Data definitions, sources, and unanswered questions"},
    "inventory_title": {"zh": "当前可用数据与分析边界", "en": "Available data and analytical boundaries"},
    "field_title": {"zh": "字段与指标含义", "en": "Fields and metric meanings"},
    "source_title": {"zh": "数据来源", "en": "Data sources"},
    "schedule_title": {"zh": "五个排课问题的当前状态", "en": "Current status of five scheduling questions"},
    "resolution_title": {"zh": "当前不足的解决路径", "en": "Practical paths to address gaps"},
    "reproduce_title": {"zh": "复现提示", "en": "Reproduction"},
    "download_guide": {"zh": "下载当前语言的模型与代理说明", "en": "Download model and proxy guide in the current language"},
    "download_label": {"zh": "下载说明文档", "en": "Download guide"},
    "data_unavailable": {"zh": "缺少数据产物，看板暂时无法加载。请先生成分析输出后重新打开。", "en": "Required data outputs are missing, so the dashboard cannot load. Generate the analysis outputs and reopen it."},
    "status_available": {"zh": "可用", "en": "Available"},
    "status_unavailable": {"zh": "不可用", "en": "Unavailable"},
    "status_not_used": {"zh": "未纳入当前指标", "en": "Not used in current metrics"},
    "status_not_enabled": {"zh": "未启用", "en": "Not enabled"},
    "cannot_answer": {"zh": "数据不足", "en": "Insufficient data"},
    "reference": {"zh": "reference", "en": "reference"},
}


def t(key: str, lang: str = "zh", **kwargs: object) -> str:
    """Return a translated string and fail loudly for an incomplete key."""
    values = TEXT[key]
    value = values[lang]
    return value.format(**kwargs) if kwargs else value


def keys_match() -> bool:
    return all(set(values) == {"zh", "en"} for values in TEXT.values())
