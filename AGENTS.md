# Course Retention Platform — Agent Working Agreement

## 1. Project identity

- Project: 高校课程注册与学习留存分析平台
- Repository: `E:\Projects\course-retention-platform`
- Owner: 用户本人
- Execution date: 2026-09-10 onward
- Historical analysis reference date: 2024-01-01
- Current mode: local development only
- Primary deliverable: reproducible Python data pipeline plus local website/dashboard

## 2. Agent roles

### DeepSeek executor

DeepSeek V4 Flash is the primary code and analysis executor. All generated implementation code, data-analysis code, dashboard code, and first-pass analytical explanations must come from `deepseek-v4-flash` through the local API configuration.

DeepSeek must follow the fixed project phases and current phase input. It must not modify another repository, change the agreed data windows, invent unavailable fields, or describe an unverified output as complete.

### Codex supervisor and reviewer

Codex is the supervising reviewer, not the primary feature-code author and not a task scheduler. Codex is responsible for:

- inspecting and understanding the dataset and its documented field meanings;
- reviewing DeepSeek-returned code for logical correctness and scope compliance;
- checking cleaned tables, joins, aggregations, metrics, model results, and dashboard figures against the source data;
- verifying that model choices are explained by problem fit, interpretability, data volume, assumptions, and limitations;
- rejecting or requesting correction of DeepSeek output when evidence, calculations, labels, or charts are wrong;
- confirming whether the current fixed project phase meets its acceptance criteria;
- updating the repository history log with evidence, decisions, rejected outputs, and current status;
- keeping project results separate from unsupported ATLAS resume claims.

Codex does not create background schedules, agent task queues, or delegated work plans. Codex follows the already agreed phase order in `PROJECT_SCOPE.md`. Codex may directly edit governance, configuration, review, and history documents, but primary implementation changes must be returned by DeepSeek and reviewed before acceptance.

The deterministic pipeline must remain runnable after code generation without calling an LLM. DeepSeek is used to produce code and analysis, not as a runtime dependency for ingestion, cleaning, metrics, models, or dashboard rendering.

### Human responsibility

The user supplies or locally enters the API key, confirms any personal factual claims, and decides whether a completed project may be listed as an independent project on a resume. No later project work may be retroactively attributed to the 2024 ATLAS internship unless supported by contemporaneous evidence.

## 3. Hard workspace boundary

### Allowed write area

Only this repository may be created or modified:

`E:\Projects\course-retention-platform`

### Explicitly read-only / do not modify

- `E:\Projects\resume generation\resume_2026_revision`
- `E:\Projects\product-promo-site`
- `E:\Projects\disney_park_itinerary_planner`
- any other repository, workspace, desktop file, or external project

Do not move, delete, overwrite, reset, or reformat files outside the allowed repository. Do not modify the original resume, the resume story library, or the existing Agent projects while working on this project.

## 4. Project time boundaries

- Development starts on 2026-09-10 and continues only through explicit user follow-ups.
- No background execution, scheduled automation, or monitoring is implied.
- The new platform is an independent project. It must not be backdated into ATLAS.
- Any seven-month duration may be stated only if the user actually works on the independent project for seven months and retains evidence of that work.
- Dataset time coverage must be recorded separately for each source; project development dates must never be confused with source-data dates.

### Ordered data-window policy

- The analysis clock is 2024-01-01; the actual repository work still occurs from 2026-09-10 onward.
- Primary window: 2021, 2022, and 2023. Use this window whenever it meets the module-level sufficiency checks.
- First fallback: 2022, 2023, and 2024. Use only for a module that fails the primary-window sufficiency checks.
- Last resort: 2023, 2024, and 2025. Use only when the first fallback also fails.
- Never use 2026 or later source data under the current agreement.
- Window selection is per analysis module; one insufficient module must not force unrelated modules to use later data.
- Each model uses the first two years for training and the third year for holdout evaluation.
- Every source adapter must expose its source years and apply the selected window before joins, feature engineering, model training, aggregation, or dashboard export.
- A 2024 or 2025 fallback result is a later independent extension and cannot be presented as work completed during ATLAS.

## 5. Required implementation phases

1. Environment and repository safety
2. Public data acquisition and licensing/source notes
3. Data dictionary and normalized schema
4. Python ingestion, splitting, cleaning, validation, and quality reports
5. UIUC course planning and W-based withdrawal proxy analysis
6. Simple course-level supervised and unsupervised modeling
7. Course-review sentiment and topic analysis only when lawful text data is available
8. Schedule-conflict graph and schedule-change analysis
9. Local website/dashboard and Excel export
10. Lean validation, visual cross-check, documentation, and resume evidence record

## 6. Accuracy and evidence rules

- Never fabricate a dataset row count, model score, project duration, user count, business impact, or completion status.
- Distinguish public aggregate enrollment, course-level enrollment, registration events, withdrawal records, and attendance.
- Treat UIUC `W` as a withdrawal proxy only when the denominator and limitations are documented.
- Treat VLE clicks or active days as online engagement proxies, never as physical attendance.
- Report associations unless the design supports a causal claim.
- Use time-aware evaluation for temporal prediction; no future observations may enter training features.
- Prefer interpretable baseline models before complex models.
- Every model choice must document the problem fit, assumptions, advantages, limitations, and why more complex alternatives were not selected.
- Every resume claim must point to a source, code path, output, or experiment record.

### Lean validation only

Do not build excessive defensive, stress, browser-matrix, or exhaustive permutation tests. Required validation is limited to checks that establish the correctness of the delivered analysis:

- selected years and source-row coverage;
- column meaning, types, missing-value treatment, duplicates, and join cardinality;
- reconciliation of source totals with cleaned and aggregated tables;
- correctness of W-based proxy, demand, conflict, sentiment, and model metrics;
- one reproducible pipeline run and one dashboard smoke run;
- cross-check of displayed values, filters, labels, axes, units, and written interpretations against generated tables;
- explicit answers to all five scheduling questions defined in `PROJECT_SCOPE.md`.

## 7. Technology constraints

- Required: Python, Pandas, scikit-learn, local website/dashboard, Excel export.
- Preferred: PyArrow, openpyxl or xlsxwriter, Streamlit, Plotly, NetworkX.
- Tableau is not part of this project.
- `importlib` may be used only for a modular plugin loader; it is not a dashboard framework.
- The data pipeline and dashboard must work without DeepSeek.

## 8. Completion definition

A phase is complete only when its DeepSeek-produced code or analysis, the supervisor review, required validation checks, source notes, and output artifact are present in this repository. `HISTORY.md` must record the accepted evidence and current step. The project is complete only when a fresh local run reproduces the cleaned data, metrics, model evaluation, dashboard output, five scheduling-question answers, and documented limitations without changing another repository.
