# Project outline / 项目大纲

## Purpose / 目的

This is an independent, reproducible local analysis platform for observing UIUC course volume, grade structure, formal W marks and their derived share, and same-course temporal screening. It is not an official withdrawal system, a student-retention causal study, an attendance system, or a capacity planner.

这是独立的本地可复现分析项目，用于观察 UIUC 课程规模、成绩结构、正式 W 标记及其派生占比和同课程时间筛查。它不是官方退课系统、学生留存因果研究、考勤系统或容量规划系统。

## Data boundaries / 数据边界

- Source: public UIUC GPA CSV at course-term-instructor grade-distribution grain.
- Continuity focus: 2021–2023 Spring/Fall; 2024 is a bridge year and truth-only holdout. The independent six-year extension covers 2019–2024 Spring/Fall only; no 2026+ data.
- `Students` is the count of course-completion A+–F final-grade records and the source field equals the sum of the A+–F bands. It is not registrations, unique students, or section enrollment. `W` is the formal `Withdraw` mark count; `w_mark_share = W / (Students + W)` is the derived share when the denominator is valid. `W_proxy` is retained only as a compatibility field name. `W=0` only means no W was observed in aggregated final-grade records; it does not by itself prove no earlier drop or student adaptation.
- Course-level source rows may include multiple instructor records for one course-term. They are not independent students or sections.
- There is no student ID, registration/drop event, withdrawal timestamp, section meeting time, capacity, waitlist, attendance, LMS event, pass-rate, or GPA/average-GPA field in the current source.

## Modules and inputs/outputs / 模块与输入输出

| Module | Input | Output | Use |
| --- | --- | --- | --- |
| Normalisation | raw GPA CSV | filtered/interim and course-term metrics | source cleaning and derived-share formulas |
| Demand/W marks | course-term metrics | demand rankings and W-mark summaries | descriptive review only |
| Same-course trajectory | 2019–2024 raw GPA CSV | trajectory table, predictions, metrics, coefficients, title audit, continuity table/report | stable `Subject + Number`; ordinary prior-calendar-year history, same-season history only for genuinely one-season courses; special-only keys excluded, overlapping ordinary rows retained |
| EDA | 2019–2024 raw GPA slice | inventory, coverage, subject distribution, numeric summary, reconciliation, join audit, JSON report | reproducible data evidence |
| Dashboard | processed CSV/JSON outputs | bilingual local Streamlit pages | read-only presentation; no browser retraining |
| Excel | processed tables | not currently generated | explicitly pending scope/implementation |

## Model purpose / 模型用途

The trajectory target is `w_flag = 1 when W > 0`, not a count forecast or official withdrawal probability. `W` is a formal W-mark count, and `w_mark_share` is a derived share. Logistic Regression is the interpretable primary model; Random Forest is a fixed nonlinear comparator; constant and persistence baselines provide context. The prediction table reports score, truth, and score-minus-truth error. A calibrated interval is not calculated for this binary screen. K-Means is exploratory course-volume profiling only; it is not a student grouping, cause model, or core decision label.

课程轨迹目标是 `W > 0` 的二分类标记，不是人数预测或官方退课概率。`W` 是正式 W 标记数，`w_mark_share` 是派生比例。Logistic Regression 是可解释主模型，Random Forest 是固定参数的非线性对照，常数和持续性基线用于参照。预测表提供分数、真实值和分数减真实值误差；二分类筛查不计算校准区间。K-Means 仅用于探索性课程规模画像，不是学生分群、原因模型或核心决策标签。

## Acceptance / 验收

1. Run `python scripts/analyze_course_trajectory.py` for trajectory plus integrated outputs.
2. Run `python scripts/generate_course_trajectory_eda.py` to reproduce EDA without fitting models.
3. Run `python -m pytest -q -p no:cacheprovider` for the lean regression checks.
4. Run the local Streamlit dashboard smoke check when dependencies permit; verify Chinese/English labels, filters, units, coverage, and limitations against processed outputs.
5. Treat the Excel deliverable as pending until a script writes a workbook and its sheets are checked. Do not claim Excel completion from CSV outputs.

## Current status / 当前状态

The six-year same-course/same-term trajectory, continuity diagnostics, bilingual explanations, and reproducible EDA scripts are implemented in this repository. The main limitations remain the aggregate source grain, lack of event-level drop data, lack of GPA/pass fields, and lack of schedule/attendance/LMS data. Excel export, lawful review-text analysis, and schedule-conflict analysis remain uncompleted unless separately implemented and verified.
