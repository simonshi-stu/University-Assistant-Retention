# Course Enrollment and Learning Retention Explorer

Project outline: [docs/PROJECT_OUTLINE.md](docs/PROJECT_OUTLINE.md)

This is a reproducible local dashboard using public UIUC GPA course-term aggregates. It helps course owners and academic planners review observed course volume, W marks, estimated grade feedback, historical screening scores, and exploratory course profiles. It does not turn limited public data into an official withdrawal rate, attendance measure, registration count, or causal claim.

## What it shows

The five tabs are Overview, Course volume & W marks, Prediction screening, Course profiles, and Data & limits. Year, term, and Subject filters affect descriptive charts and rankings. They do not retrain models or change holdout metrics. Top N changes only rankings explicitly labelled as Top N.

The observed course-volume proxy is `Students + W`, where `Students` is the final A+–F grade-record count excluding W and `W` is the grade-table count of formal Withdraw marks. `w_mark_share = W / (Students + W)` is a derived share, not an official withdrawal rate. Neither is sign-ups, registration requests, capacity, waitlist, or a unique-student count. `grade_point_mean` is an estimated 4.0-style mean from A+–F counts, not an official GPA.

## Time and model boundaries

The primary source window is 2021–2023 spring/fall; the first two years train and the third is a time holdout. Approved fallbacks are 2022–2024 and 2023–2025 when a module fails its sufficiency check. Data from 2026 onward is excluded. The user-approved six-year course-trajectory extension (2019–2024) is independent of that primary line: it uses stable `Subject + Number`; ordinary courses use either term from prior calendar years, while genuinely one-season courses use same-season history. 2024 is truth-only holdout, and recognisable Special/Selected Topics are set aside in a separate audit.

The target is whether a course-term row has a W mark, not a high withdrawal probability. Logistic regression is the interpretable primary model; random forest is a fixed nonlinear comparator. Metrics are screening performance on a time holdout, not deployment guarantees or causal effects. AP means Average Precision. Brier score is a probability calibration error where lower is better. See the [model and proxy guide](docs/MODEL_AND_PROXY_GUIDE_EN.md) for formulas, confusion-matrix examples, same-term lag logic, coefficient interpretation, and K-Means limitations.

When the course-trajectory outputs are present, the Prediction tab first shows 2024 stable-course history predictions versus truth. It reads the generated outputs dynamically and does not retrain in the browser.

## Data limits and scheduling questions

The GPA source has no student ID, section time, capacity, waitlist, attendance, LMS event, or registration/withdrawal timestamp. Consequently, the dashboard reports five scheduling questions as data-insufficient and names the missing fields and practical acquisition path. K-Means is an exploratory course-volume appendix, not a student grouping, withdrawal explanation, or decision model.

## Local run

```powershell
.\.venv\Scripts\python.exe scripts\normalize_data.py
.\.venv\Scripts\python.exe scripts\analyze_phase5.py
.\.venv\Scripts\python.exe scripts\analyze_phase6.py
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

To reproduce the independent six-year course-trajectory extension (without replacing the three-year primary line):

```powershell
.\.venv\Scripts\python.exe scripts\analyze_course_trajectory.py
```

No runtime LLM is required. Source-specific licenses and data boundaries must be reviewed before any extension or cross-school comparison.


## Independent six-year evidence outputs

The trajectory command also writes `course_trajectory_continuity.csv` and compact EDA artifacts. To reproduce only the EDA (without fitting models), run:

```powershell
.\.venv\Scripts\python.exe scripts\generate_course_trajectory_eda.py
```

The EDA records the source slice's row/column counts, dtypes, missing cells, exact duplicates, year-term coverage, Subject distribution, numeric summaries, source-to-course-term reconciliation, and many-to-one join audit. Duplicate source course-term keys are expected when multiple instructor grade-distribution records are aggregated; they are not duplicate students. The current GPA source has grade counts A+ through F, `Students`, and `W`, but no pass-rate or GPA field and no drop event/withdrawal timestamp.

The trajectory outputs are CSV/JSON only. An Excel workbook is not currently generated, so Excel export remains pending and is not claimed as complete.

### W interpretation and enrollment-data gap

For business interpretation, W can be treated as a formal W grade recorded
after the no-W drop deadline; for a standard full-term undergraduate course
this is often near the halfway point (about week 8), but short, nonstandard,
part-of-term, and graduate deadlines differ. The current file contains only a
final W count, not a withdrawal date or event.

To estimate early-course change, we need the same `CRN/section_id` in an
opening-week enrollment snapshot and a post-add/drop (roughly week-two or
official census) snapshot. The difference is only a rough net change, not a
gross drop count. We found public 10th-day census reports and some historical
course/section enrollment pages, but not a reproducible public paired
first-week/second-week section series; daily rosters and registration activity
usually require authorised campus access. See the [DAIR enrollment FAQ](https://dair.illinois.edu/faqs-updated/enrollment-faqs/),
[10th-day reports](https://enrollmentmanagement.illinois.edu/reports-data/),
and [DMI section enrollment](https://www.dmi.illinois.edu/cp/listcourses.asp?org=1B1-KV-XXX-XXX&row=6540&year1=2023&year2=2024).

The ideas that high A/A+ share, easier grading, required-major status, or a
“water course” label changes W behavior are hypotheses for later testing. The
current source has grade counts but no numeric GPA or official easy-course
label, so it supports descriptive grade-profile analysis only. W=0 means no W
mark was observed in the final-grade records; it does not prove that no earlier
drop occurred or that students adapted to difficulty.
