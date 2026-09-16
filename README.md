# 高校课程注册与学习留存分析平台

项目大纲：[docs/PROJECT_OUTLINE.md](docs/PROJECT_OUTLINE.md)

English entry: [README_EN.md](README_EN.md). 模型与代理指标的双语说明：[中文](docs/MODEL_AND_PROXY_GUIDE_ZH.md)｜[English](docs/MODEL_AND_PROXY_GUIDE_EN.md)。

这是一个可复现的本地分析看板：用公开的 UIUC GPA 课程数据，帮助课程负责人、教务规划人员和教育研究者观察课程规模、成绩结构、W 标记、估算成绩反馈和历史风险排序。它的价值是把“哪些课程值得优先复核”变成可追溯的证据，而不是把有限的公开数据包装成官方退课率、出勤率或因果结论。

## 先看这里：看板能回答什么

- 哪些课程-学期行或课程键的需求代理较高？
- 需求代理在 2021–2023 春秋学期如何变化？
- 哪些课程的 W 标记较多或派生 W 标记占比相对较高，且分母是否足够稳定？
- 只使用更早年份信息时，模型能否把 2023 年的高 W 代理课程排在前面？
- 哪些课程在规模、成绩结构和历史代理上相似？

当前输出的行数、课程键和 Subject 数量应以本地生成表为准；主线窗口为 2021、2022、2023 年的 spring/fall 数据，前两年训练，第三年时间留出。另有用户批准的独立六年课程轨迹扩展（2019–2024）：按稳定 `Subject + Number` 追踪，普通课程按前一日历年任一 Spring/Fall 取历史，单季课程才按同季取历史，2024 只作真值留出；Special/Selected Topics 先单独放置。上述统计来自课程-学期聚合，不代表独立学生数量。

看板页面依次是：总览、需求与 W 标记、预测风险、课程画像、数据与限制。左侧年份、学期、院系筛选作用于数据图表与榜单；模型指标和预测不在浏览器中重新训练。Top-N 滑杆只作用于带有“前 N 名”标识的需求榜、W 标记占比榜、预测排序和特征重要性榜。

## 核心口径与限制

公开 GPA 数据的源粒度是课程-学期-教师成绩分布，本项目聚合到课程-学期：

- `Students` 是期末 A+–F 成绩记录数（不含 W），不是报名人数、独立学生数或严格意义的结课人数；`W` 是源数据中的正式 Withdraw 标记计数。
- `demand_proxy = Students + W` 是已观察课程规模代理，不是想报名数、注册请求、capacity 或 waitlist。
- `w_mark_share = W / (Students + W)` 是派生 W 标记占比；W 本身仍是计数，不能把该占比称为官方 withdrawal/drop rate。
- `grade_point_mean` 是由 A+–F 计数按 4.0 风格换算的估算平均绩点，用于历史反馈参考，不是官方 GPA。
- `W=0` 只表示期末成绩记录中没有观察到 W 标记；当前数据没有 drop 事件和日期，不能据此证明没有更早 drop、学生已经适应或课程没有突然变难。
- 当前没有合法、可识别且带时间标签的学生级 attendance、LMS 活动、注册事件、section 时间、容量或 waitlist 数据。
- 因此看板不能回答具体出勤人数、真实参与人数、上课时间冲突、拥挤时段、调课后学生变化，也不能证明课程安排造成留存变化。

预测结果是时间留出集上的筛查表现，不是官方退课概率或因果效果。K-Means 当前 K=2，主要体现较小规模与较大规模课程观察的差异；不是学生分群，也不是退课原因分群。

右上角 **Deploy** 是 Streamlit 宿主界面的发布入口，不是本项目的“本地部署按钮”，也不会自动在电脑上创建服务器。选择 Community Cloud 需要把仓库和依赖交给云端运行；选择其他平台则需要自行准备环境、认证、访问控制和成本预算。本项目当前只承诺本地可复现运行。

## 环境要求

- Python 3.11+
- 原始数据存放于 `data/raw`，标准化中间表和指标存放于 `data/interim` 与 `data/processed`。

## 数据窗口规则

按顺序使用以下窗口：

1. 2021–2023
2. 若模块不足，则使用 2022–2024
3. 若仍不足，则使用 2023–2025

**绝不使用 2026 及以后的数据。**

模型训练使用前两年，第三年作为留出集（hold out）。

## 数据源

- **GPA 原始数据**：https://raw.githubusercontent.com/wadefagen/datasets/main/gpa/uiuc-gpa-dataset.csv
- **GPA 文档**：https://github.com/wadefagen/datasets/blob/main/gpa/README.md
- **Course Explorer**：https://courses.illinois.edu/cisapp/explorer
- **Course Explorer 官方文档**：https://answers.uillinois.edu/uic/88215
- **DMI**：https://dmi.illinois.edu/
- **Enrollment Management**：https://enrollmentmanagement.illinois.edu/reports-data/

### 数据源说明

- GPA 数据为公开 FOIA 衍生的成绩分布，粒度为课程-学期-教师（course-term-instructor），无 section id。
- W 是 Withdraw 的正式 W 标记计数；W/(Students+W) 仅为派生标记占比，**绝非官方退课率（official drop rate）**。
- Course Explorer 为官方公开、无需认证的 XML 接口，提供 section 课表。
- 未来 join 可能将课程-学期 GPA 聚合附加到 section，但仅在键与基数（cardinality）验证通过时进行；**绝不假装 GPA 是 section 级别**。
- DMI 与 enrollment 总量仅作上下文参考。
- 评论/ICES 因缺乏合法、可识别课程、带时间标签的文本而禁用；不涉及出勤（attendance）。

## 生成基础标准化数据

在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe scripts\normalize_data.py
```

该命令不联网，固定使用 2021–2023 春秋窗口，写入：

- `data/interim/gpa_filtered.csv`
- `data/processed/course_term_metrics.csv`
- `data/processed/data_quality_report.json`

W 标记占比仅定义为 `W / (Students + W)`，不是官方退课率。GPA 数据没有
section id、student id 或 attendance 字段，不能由此支持 section 冲突分析；它虽有 A+–F 计数，但没有官方数值 GPA。

## 生成需求与 W 代理数据

在基础标准化数据存在时运行：

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase5.py
```

该命令固定使用 2021–2023 春秋窗口，写入：

- `data/processed/course_term_demand_metrics.csv`
- `data/processed/course_demand_summary.csv`
- `data/processed/phase5_report.json`

需求代理严格为 `Students + W`；派生 W 标记占比严格为聚合计数上的
`W / (Students + W)`。详情、阈值、排名和限制见
`docs/phase5_analysis.md`。

## 许可

仓库代码许可未声明；各数据源条款依来源而定（source-specific）。

## 其他

- 无运行时 LLM（No runtime LLM）。
- 排课冲突、评论情感和 Excel 仍未声称完成；后续工作按 `PROJECT_SCOPE.md` 的项目范围管理。

## 预测分析与本地看板（2026-09-11）

本次已实现时间感知的预测分析和本地 Streamlit 看板。项目仍严格使用主窗口
2021–2023，2021–2022 为训练期，2023 为时间留出集；不会使用 2026 年及以后数据。

### 预测数据含义

- 分析单位是 `Year + Term + Subject + Number + Course Title` 的课程-学期，
  不是学生、注册事件或 section。
- `Students` 是源数据中不含 W 的人数；`W` 是源数据的 W 计数。
- `demand_proxy = Students + W`，只是需求代理，不是注册事件数、独立学生数、
  容量或等候名单。
- 旧三年实验中的 `W_proxy = W / (Students + W)` 仅是历史派生 W 标记占比，不是官方
  withdrawal/drop rate，不能识别退课时间、原因或因果留存影响。
- 旧三年实验的 `high_w_risk` 阈值只用训练期 W 标记占比第 75 百分位计算，随后固定用于 2023。
  真实训练数据第 75 百分位为 0，若使用 `>= 0` 会导致训练集没有负类；代码因此
  透明记录并采用严格 `W_proxy > 0` 的 tie policy；独立六年轨迹不使用这个分位数标签，而直接预测 `W > 0`。

预测特征包含课程等级、Subject、Term、Year_offset，以及严格早于当前年份的历史
W 标记占比、需求代理、Students、成绩总数和成绩份额。当前行的 Students、成绩总数、
成绩份额、W、W 标记占比、需求代理、排名、高需求标记和目标标签只留在审计表，不进入
模型特征，避免用期末结果预测同一期风险。历史 Students 仍是源计数，不是独立学生数。

### 预测模型与输出

- Logistic Regression：解释性主模型，使用训练集拟合的缺失值处理、标准化、类别
  one-hot 和 balanced class weight；当前行期末成绩和 Students 不进入预测矩阵。
- Random Forest：固定随机种子的非线性对照，不用留出集调参。
- 指标：AP（Average Precision）、ROC-AUC、F1、precision、recall、balanced accuracy、Brier score、
  混淆矩阵和 Recall@K（留出集前 20%）。
- K-Means：仅对训练期课程汇总做描述性课程画像；样本/特征不足或 silhouette
  低时明确跳过，不能解释为退课原因或因果分组。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase6.py
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

生成文件包括：`phase6_feature_table.csv`、`phase6_model_metrics.csv`、
`phase6_predictions.csv`、`phase6_feature_importance.csv`、
`phase6_course_profiles.csv` 和 `phase6_report.json`。

看板包含总览、需求/W 代理、预测风险、课程画像、数据与限制五个页面，
筛选器只影响描述性表格和图表，不会在浏览器中重新训练模型。由于 Course Explorer
课程安排数据仍缺少可复现的 section 时间字段，五个排课问题继续显示为
“数据不足”，没有用空图或虚构值替代。

### 复现验证

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

六年课程轨迹扩展可独立复现（不替换上述三年主线）：

```powershell
.\.venv\Scripts\python.exe scripts\analyze_course_trajectory.py
```

详细字段、输出表和防泄漏规则见 [docs/data_dictionary.md](docs/data_dictionary.md)
和 [docs/phase6_modeling.md](docs/phase6_modeling.md)。

## 结果如何阅读

2023 时间留出集上，Random Forest 的 AP 为 0.529、ROC-AUC 为 0.754、Recall@20% 为 0.484；Logistic Regression 的 AP 为 0.503。AP 优先于 accuracy，是因为 W 标记标签存在类别不平衡。这些数字表示排序/筛查表现，不是准确的退课概率，更不是官方退课率。

K-Means 使用训练期课程汇总特征，轮廓系数为 0.498。较大的画像簇包含 111 个课程键，较小规模画像簇包含 2,784 个课程键；两类的 W 代理中心接近，不能据此判断某一类课程更容易退课。K-Means 适合当前第一版画像，因为速度快、实现简单、聚类中心容易解释；层次聚类、DBSCAN 或文本聚类可在未来有更多年份、异常点或合法评论文本后作为稳定性对照。

## 未来路线与受众

从 UIUC 扩展到多所高校有实际意义：教务与课程负责人可以比较需求结构，教学支持团队可以建立复核优先级，研究者可以观察课程设计与结果的关联，数据团队也可以用它检验各校数据质量。但跨校比较的前提是统一课程身份、学期定义、成绩口径、隐私授权和许可证，不能直接横比未经校准的代理比例。

推荐路径是先接入少量许可清晰、字段字典稳定的高校；为每所学校保留独立指标，再提供经过口径校准的跨校比较；随后引入合法的 section 快照、容量/waitlist 和 LMS 汇总数据；最后再做滚动时间验证、画像稳定性和权限化发布。

## 质量、历史和变更边界

`HISTORY.md` 记录数据窗口、验证结果、接受/拒绝的输出和当前状态；`docs/DASHBOARD_CHANGE_BOUNDARY.md` 约束后续代理对看板的修改范围。内部脚本和历史记录可以保留阶段性文件名，但这些内部流程词不得出现在面向看板用户的标题、导航、说明或结论中。

## 六年轨迹的连续性与 EDA 证据

`course_trajectory_continuity.csv` 按稳定 `Subject + Number` 记录出现年份/学期、覆盖率、Spring/Fall 模式、2019–2024 观察格数、2021–2023 实际出现年份数、历史匹配规则、训练/2024 回测资格和排除原因；标题变化只进 `course_trajectory_title_audit.csv`，缺席学期不会填成 0。可识别的 Special/Selected Topics 不参与连续性比例或模型，明细保存在 `course_trajectory_special_topic_audit.csv`。EDA 可单独复现且不拟合模型：

```powershell
.\.venv\Scripts\python.exe scripts\generate_course_trajectory_eda.py
```

EDA 输出源切片的行列规模、字段类型、缺失、精确重复、年度/学期覆盖、Subject 分布、数值摘要、源表到课程-学期聚合的 Students/W 核对和 many-to-one 连接基数。原始重复课程-学期键通常来自多个教师/成绩分布记录的聚合，不是重复学生。当前 GPA 源有 A+ 到 F 成绩计数、Students 和 W，但没有官方数值 GPA、drop 事件或退课时间戳；轨迹表中的 `grade_point_mean` 只是 A+–F 计数换算的估算平均绩点，不能从 W 恢复官方 GPA 或 drop rate。

课程轨迹命令当前只生成 CSV/JSON，不生成 Excel 工作簿；Excel 导出仍是待办，不能以 CSV 产物代称已完成。

### W 的业务解释与选课人数数据缺口

业务上，W 可理解为学生在无 W 退课截止日之后留下的正式 W 成绩标记；标准本科整学期课程常接近课程过半（约第 8 周），但短学期、非标准课程、Part of Term 和研究生规则不同。当前文件只有期末 W 计数，不能还原退课日期或退课事件。因此 W=0 只能证明当前成绩记录没有观察到 W，不能证明没有更早 drop、学生已经适应或课程没有突然变难。

如果要估算开课后退课变化，需要同一 `CRN/section_id` 的第一周人数和加退课结束后（约第二周或官方 census）人数。两者之差只能表示粗略净变化，不能直接当作 drop 人数。已找到 UIUC 第 10 天 census 报告和部分课程/section enrollment 页面，但尚未找到公开、可复现的第一周—第二周配对快照；每日 roster/registration activity 通常需要授权访问。详见 [DAIR enrollment FAQ](https://dair.illinois.edu/faqs-updated/enrollment-faqs/)、[10th-day reports](https://enrollmentmanagement.illinois.edu/reports-data/) 和 [DMI section enrollment](https://www.dmi.illinois.edu/cp/listcourses.asp?org=1B1-KV-XXX-XXX&row=6540&year1=2023&year2=2024)。

“高 A/A+ 或水课更少 W”“专业必修课即使成绩低也更容易坚持”目前只是待验证假设。现有数据只有成绩档位计数，没有数值 GPA 或官方水课标签，后续只能先做成绩结构的描述性分析。
