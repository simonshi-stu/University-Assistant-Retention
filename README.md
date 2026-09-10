# 高校课程注册与学习留存分析平台

当前状态：Phase 5 已接受。仓库包含公开 GPA 数据采集证据、窗口过滤、课程-学期标准化指标、质量报告、时间切分验证、需求代理和 W proxy 分析；Course Explorer 的六次主窗口请求均被 WAF 阻断，未伪造 section 数据。

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
- W/(Students+W) 仅为退课代理指标（withdrawal proxy），**绝非官方退课率（official drop rate）**。
- Course Explorer 为官方公开、无需认证的 XML 接口，提供 section 课表。
- 未来 join 可能将课程-学期 GPA 聚合附加到 section，但仅在键与基数（cardinality）验证通过时进行；**绝不假装 GPA 是 section 级别**。
- DMI 与 enrollment 总量仅作上下文参考。
- 评论/ICES 因缺乏合法、可识别课程、带时间标签的文本而禁用；不涉及出勤（attendance）。

## Phase 3 本地运行

在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe scripts\normalize_data.py
```

该命令不联网，固定使用 2021–2023 春秋窗口，写入：

- `data/interim/gpa_filtered.csv`
- `data/processed/course_term_metrics.csv`
- `data/processed/data_quality_report.json`

W proxy 仅定义为 `W / (Students + W)`，不是官方退课率。GPA 数据没有
section id、student id 或 attendance 字段，不能由此支持 section 冲突分析。

## Phase 5 本地运行

在 Phase 3 输出存在时运行：

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase5.py
```

该命令固定使用 2021–2023 春秋窗口，写入：

- `data/processed/course_term_demand_metrics.csv`
- `data/processed/course_demand_summary.csv`
- `data/processed/phase5_report.json`

需求代理严格为 `Students + W`；W proxy 严格为聚合计数上的
`W / (Students + W)`。详情、阈值、排名和限制见
`docs/phase5_analysis.md`。

## 许可

仓库代码许可未声明；各数据源条款依来源而定（source-specific）。

## 其他

- 无运行时 LLM（No runtime LLM）。
- 后续阶段继续按 `PROJECT_SCOPE.md` 顺序执行；当前尚未声称模型、看板、Excel 或排课冲突分析已完成。
