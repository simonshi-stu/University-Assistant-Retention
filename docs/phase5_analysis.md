# Phase 5：UIUC 需求与 W-based withdrawal proxy 分析

## 状态

本阶段使用 `data/processed/course_term_metrics.csv`，固定窗口为 2021、2022、2023，
固定学期为 spring 和 fall。分析是确定性的，不依赖网络或运行时 LLM。

## 方法与口径

- 输入粒度是课程-学期；更底层的 GPA 原始数据粒度是课程-学期-教师成绩分布。
- 需求代理定义为 `demand_proxy = Students + W`。来源文档说明 `Students` 不含 W，
  因而不能只使用 `Students` 作为分母或把两者相加后称为独立学生数。
- W proxy 定义为 `W_proxy = W / (Students + W)`，计算使用课程-学期聚合后的计数，
  仅在两个计数非缺失、非负且分母大于 0 时有效。
- “高需求”是全选定窗口课程-学期需求代理的第 75 百分位及以上；本次阈值为
  `105`。这是描述性分组，不是 Phase 6 的预测标签。
- W proxy 排名仅保留 `demand_proxy >= 20` 的课程-学期，以减少极小分母造成的不稳定；
  这个筛选不会改变明细表中的原始代理值。
- 课程汇总按 `Subject + Number + Course Title` 分组。标题发生变化时会形成不同课程键，
  不擅自把不同标题合并。

## 可复现输出

运行：

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase5.py
```

生成：

- `data/processed/course_term_demand_metrics.csv`：8,973 条课程-学期明细，保留成绩分布
  字段并增加 `demand_proxy`、高需求标记、需求排名和 W proxy 排名字段。
- `data/processed/course_demand_summary.csv`：3,336 个课程键的跨学期汇总，包含总需求代理、
  平均/最大需求、加权 W proxy、观察年份和高需求年份数。
- `data/processed/phase5_report.json`：窗口、覆盖、公式、阈值、排名前 10 和限制说明。

## 结果核对

- 2021–2023 六个 year-term 均有记录；明细行数分别为 2021 spring 1,373、2021 fall
  1,516、2022 spring 1,490、2022 fall 1,554、2023 spring 1,447、2023 fall 1,593。
- 明细表中 `Students` 总计为 1,003,282，`W` 总计为 3,483，需求代理总计为 1,006,765；
  课程汇总的对应总计完全一致。
- 明细表 8,973 行的 `demand_proxy` 和 W proxy 均有效；课程-学期键和课程汇总键均唯一。
- 总需求代理最高的课程-学期包括 LAS 101、CHEM 103、ECON 102、CHEM 102 和 MATH 241；
  跨窗口总需求代理最高的课程键包括 CHEM 103、CHEM 102、STAT 100、MATH 241 和 ECON 102。
- 在需求代理至少为 20 的排名口径下，W proxy 最高的课程-学期为 2021 fall 的 MACS 395，
  其 proxy 为 0.100000（3 W / 30 需求代理）。

以上结果是对公开 GPA 分布数据的描述性汇总。`demand_proxy` 不是注册事件数、独立学生数或
容量/等候名单；`W_proxy` 不是官方 withdrawal/drop rate，不能识别退课时点、退课原因或
因果留存影响。数据没有 section id、student id、attendance、capacity 或 waitlist 字段，
因此 Phase 5 不回答排课冲突和真实注册转化问题。
