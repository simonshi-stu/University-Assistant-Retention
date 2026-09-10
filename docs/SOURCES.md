# 数据源说明（SOURCES）

本文件列出各数据源的访问方式、粒度、预期用途、join 限制及访问/许可说明。

## GPA 数据

- **URL**：https://raw.githubusercontent.com/wadefagen/datasets/main/gpa/uiuc-gpa-dataset.csv
- **文档**：https://github.com/wadefagen/datasets/blob/main/gpa/README.md
- **访问**：公开 FOIA 衍生数据，可直接下载。
- **粒度**：课程-学期-教师（course-term-instructor），无 section id。
- **预期用途**：课程-学期级别的成绩分布分析；W/(Students+W) 仅作为退课代理指标，**绝非官方退课率**。
- **Join 限制**：未来可能将课程-学期 GPA 聚合附加到 section，但仅在键与基数验证通过时进行；**绝不假装 GPA 是 section 级别**。
- **访问/许可**：公开数据，具体条款依来源而定。

## Course Explorer

- **URL**：https://courses.illinois.edu/cisapp/explorer
- **官方文档**：https://answers.uillinois.edu/uic/88215
- **访问**：官方公开、无需认证的 XML 接口。
- **粒度**：section 课表（section schedules）。
- **预期用途**：提供 section 级别的课程安排信息。
- **Join 限制**：可作为 section 级数据源；与 GPA 聚合 join 时需验证键与基数，不得将 GPA 视为 section 级。
- **访问/许可**：官方公开接口，使用需遵守官方条款。

## DMI

- **URL**：https://dmi.illinois.edu/
- **访问**：公开网站。
- **粒度**：汇总统计（aggregate）。
- **预期用途**：仅作上下文参考（context only）。
- **Join 限制**：不用于 section 级 join。
- **访问/许可**：公开数据，条款依来源而定。

## Enrollment Management

- **URL**：https://enrollmentmanagement.illinois.edu/reports-data/
- **访问**：公开报告。
- **粒度**：汇总统计（aggregate）。
- **预期用途**：仅作上下文参考（context only）。
- **Join 限制**：不用于 section 级 join。
- **访问/许可**：公开数据，条款依来源而定。

## 评论/ICES

- **状态**：禁用（disabled）。
- **原因**：缺乏合法、可识别课程、带时间标签的文本。
- **备注**：不涉及出勤（attendance）。
