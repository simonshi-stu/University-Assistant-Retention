# Phase 6：时间感知高 W 风险建模与课程画像

## 状态

Phase 6 使用 Phase 5 生成的 `course_term_demand_metrics.csv`，默认窗口为
2021–2023，学期为 spring/fall；2021–2022 是训练期，2023 是时间留出期。
运行时不调用网络或 LLM。

## 分析单位与标签

- 分析单位是课程-学期（`Year + Term + Subject + Number + Course Title`），不是学生、注册事件或 section。
- `W_proxy = W / (Students + W)` 是退课代理，不是官方 withdrawal/drop rate。
- 高 W 风险阈值只用训练期有效 `W_proxy` 的第 75 百分位计算，随后固定应用到 holdout。
- 若第 75 百分位为训练样本最小值，且使用 `>=` 会把所有训练行标成正类，程序改用严格 `>`，并在报告中记录 `tie_policy`。这不是另造分位数，而是为保留可识别的二分类标签处理大量 0 值并列。

## 预测特征与防泄漏

预测特征包括：

- `course_level`：由课程号按百位划分的粗课程等级；
- `Subject`、`Term`：分类特征；`Year_offset` 是相对于选定窗口第一年的数值年份偏移；
- 当前行的 `Students`、`grade_total` 和可用成绩份额只保留在特征表审计区，不进入预测模型，因为它们是期末结果；
- 严格早于当前年份的课程历史均值：历史 W proxy、历史需求代理、历史 Students、历史成绩总数、历史成绩份额和 `historical_term_count`（历史学期观测次数）。

当前行的 `Students`、成绩总数和成绩份额，以及 `W`、`W_proxy`、`demand_proxy`、高需求标记、需求/W 排名和目标标签，均被排除在模型特征之外。缺失历史只由训练集拟合的中位数填补；分类缺失只由训练集拟合的众数填补。数值特征标准化，分类特征 one-hot，所有预处理都封装在模型 Pipeline 中。

历史特征按“课程-日历年”聚合，再在课程层面跨先前年份取均值；因此 prior-year 均值会混合该年度可用的 spring/fall 观测，而不是 prior-same-term 特征。这个口径在报告的 `historical_aggregation_level` 中明确记录。

## 模型与指标

- Logistic Regression 是主模型：数据量中等时稳定、快速、系数方向可解释，并使用 balanced class weight。
- Random Forest 是非线性对照：检查潜在非线性与交互，但解释性较弱；固定随机种子，不用 holdout 调参。
- majority baseline 使用训练期正类比例作为恒定概率。
- 输出 AP（Average Precision）、ROC-AUC、F1、precision、recall、balanced accuracy、Brier score、混淆矩阵，以及每个 split 前 20% 概率排序中的 Recall@20%；报告中的 `recall_at_k_rows` 明确记录每个 split 的实际 K。AP 是排序指标，不是官方退课率；Brier 是概率校准误差，越低越好。类别缺失时指标保留空值并记录 `one_class`，程序不伪造分数。

## K-Means 课程画像

K-Means 只使用训练期课程汇总后的描述性数值特征，包含训练期 W proxy 均值和历史 W proxy 等代理字段；这些特征与预测模型完全分离，并在报告中显式标注 `target_proxy_included_in_profiles`。程序在候选 K=2–5 中选 silhouette 最高且达到质量下限的 K；样本不足、特征不足、silhouette 不可用或过低时明确跳过。聚类只能表示相似课程组，不能证明退课原因或因果关系。

## 输出文件

- `phase6_feature_table.csv`：每个课程-学期的原始追踪键、训练/留出标记、W proxy 标签、可用特征和历史特征；其中部分原始 W 字段仅用于审计，不进入模型。
- `phase6_model_metrics.csv`：每个模型和 split 的行数、类别计数、指标、混淆矩阵和 Recall@K。
- `phase6_predictions.csv`：模型、课程-学期、真实标签、预测概率和 0.5 分类结果。
- `phase6_feature_importance.csv`：Logistic 回归系数绝对值/方向或 Random Forest 特征重要性。
- `phase6_course_profiles.csv`：课程画像聚类及规模；若跳过则为空表，原因在报告中。
- `phase6_report.json`：窗口、阈值、标签计数、特征控制、模型状态、holdout 指标、画像状态和限制。

## 运行与限制

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase6.py
```

源数据没有 section id、student id、attendance、capacity 或 waitlist；因此 Phase 6 不能回答排课冲突问题，也不能把模型结果解释为真实留存因果效果。该平台是从 2026-09-10 开始的独立项目，结果不能回写为 2024 ATLAS 实习成果。

## 本次真实运行结果

主窗口生成 8,973 行特征表：训练 5,933 行，2023 留出 3,040 行。训练期 W proxy 第 75 百分位是 0；为避免 `>= 0` 把训练集全部标成正类，实际标签规则为 `W_proxy > 0`，训练正类/负类为 1,152/4,781，留出正类/负类为 608/2,432。

| 模型 | AP | ROC-AUC | F1 | Precision | Recall | Balanced accuracy | Brier | Recall@20% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Majority baseline | 0.2000 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.1600 | 0.2319 |
| Logistic Regression | 0.5029 | 0.7357 | 0.4154 | 0.2851 | 0.7648 | 0.6427 | 0.2742 | 0.4786 |
| Random Forest | 0.5293 | 0.7538 | 0.4971 | 0.4505 | 0.5543 | 0.6926 | 0.1712 | 0.4836 |

Random Forest 在该次留出集的排序、F1 和 balanced accuracy 上优于 Logistic Regression；Logistic Regression 的 recall 更高，而 Brier score 也更高（概率校准更差）。按项目策略，Logistic Regression 仍是解释性主模型，Random Forest 是非线性对照，不能因为单次 holdout 的差异就声称部署或因果收益。页面和后续报告使用 AP 这一名称，避免把 Average Precision 写成 PR-AUC。

K-Means 在 2,895 个训练课程键上运行，选择 K=2，silhouette 为 0.4982，簇规模为 2,784 和 111。画像使用训练期 W proxy 均值等描述性字段，但与预测特征矩阵严格分离。
