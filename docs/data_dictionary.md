# Data Dictionary

## Source

- File: `data/raw/gpa/uiuc-gpa-dataset.csv`
- Grain: course-term-instructor grade distribution.
- No section identifier exists in the source. Records are not sections.
- The source currently spans 2010–2026. Only the approved module window is
  eligible for analysis; 2026 and later are excluded by policy.

## Raw columns

| Column | Type | Meaning |
| --- | --- | --- |
| Year | int | Calendar year of the offering; the implementation uses this field for window filtering. |
| Term | str | Term label (`spring`, `fall`, `summer`, or `winter` in the source). |
| YearTerm | str | Source year-term label, retained but not used for window filtering. |
| Subject | str | Subject code. |
| Number | str | Course number. |
| Course Title | str | Course title. |
| Sched Type | str | Schedule type label from the source. |
| A+ ... F | numeric counts | Count of final grade records in each letter-grade band. |
| W | numeric count | Count of formal `Withdraw` (W) marks in the grade-distribution record. It is a grade outcome count, not a drop-event count. |
| Students | numeric count | Count of final A+–F grade records after course completion; the source field equals the sum of the A+–F bands. It is not registration count, unique-student count, or section enrollment. |
| Primary Instructor | str | Instructor attached to the source record. |

The source grain includes `Year`, `Term`, `Subject`, `Number`, `Course Title`,
`Sched Type`, and `Primary Instructor`. The source has no section id, student
id, or attendance field.

For the trajectory input, the current exclusion is 34 special/selected-topic
raw records touching 11 stable `Subject + Number` keys. Three keys are
special-only and do not enter the ordinary trajectory; the other eight keys
also have ordinary-course records, and those ordinary records remain included.
This verified 34/11/3/8 decomposition is row-level: the 11 stable keys are not
treated as one excluded population. Any special-topic metadata must preserve
the distinction between special rows, special-only keys, and retained ordinary
rows.

## Business interpretation and next data requirement

The project owner’s business interpretation is that a UIUC `W` is the formal
`Withdraw` mark left when a student withdraws after the no-W drop deadline. For
a standard 16-week undergraduate course, it may be described as a W left after
the halfway point (roughly week 8), but this timing is not universal and must
not be generalised to every course. Part-of-term, nonstandard, short-course,
and graduate rules differ. The current GPA file still contains only an
aggregated final W-mark count and no withdrawal time, event, or event id. See
the [Registrar refund and drop schedule](https://registrar.illinois.edu/fall-refund-schedule-26/).

`W=0` only means that no W was observed in the aggregated final-grade records;
it does not by itself prove no earlier drop, student adaptation, or absence of
a sudden difficulty change.

The desired next dataset is a section-level enrollment panel with the same
course/section identifier observed at two time points: an opening-week roster
or enrollment snapshot and a post-add/drop (approximately week-two or the
official census) snapshot. The difference would be a rough *net enrollment
change*, not a gross drop count, because late adds, section transfers,
cancellations, cross-listing, and different part-of-term start dates can also
change the number. It requires at least `term`, `CRN/section_id`,
`subject`, `number`, `snapshot_date`, `enrollment_count`, `capacity`,
`part_of_term`, and a flag for cancelled/merged sections.

The official public material we found provides useful partial sources, not the
complete paired panel: Illinois DAIR explains that rosters are updated daily
but public enrollment reporting uses a census snapshot on the 10th day, and
Enrollment Management publishes 10th-day reports. DMI also exposes historical
course/section enrollment tables. We did not find a public, reproducible
first-week plus second-week section snapshot series. Daily class rosters and
registration activity reports are described as authorized campus services, so
access would require an institutional data request and FERPA-appropriate
controls. See the [DAIR enrollment FAQ](https://dair.illinois.edu/faqs-updated/enrollment-faqs/),
[10th-day reports](https://enrollmentmanagement.illinois.edu/reports-data/),
and [DMI section-enrollment examples](https://www.dmi.illinois.edu/cp/listcourses.asp?org=1B1-KV-XXX-XXX&row=6540&year1=2023&year2=2024).

The proposed GPA/withdrawal ideas are hypotheses for a later analysis, not
current findings: courses with a larger A/A+ share or easier grading may have
fewer W marks, while required major courses may retain students despite lower
grades. The current file has letter-grade counts but no numeric GPA and no
official “easy/water course” label. An approximate grade-profile or weighted
grade score can be derived only after documenting the grade-point mapping; it
must not be presented as an official course GPA or a causal explanation.

## Filtering and interim output

`normalize_gpa` accepts a governance-approved three-year tuple. The primary
window is `(2021, 2022, 2023)`; allowed fallbacks are `(2022, 2023, 2024)`
and `(2023, 2024, 2025)`. Main terms are `spring` and `fall`.

The implementation converts `Year` to numeric, normalizes `Term` to lowercase,
filters the year and terms, and only then coerces `A+` through `F`, `W`, and
`Students` to numeric. Non-numeric values become `NA`; filtered rows are not
silently deleted for bad numeric values. Filtering occurs before aggregation,
join, model training, or dashboard export.

`data/interim/gpa_filtered.csv` retains the 24 source columns at the
course-term-instructor grain after the window/term filter. It does not add a
section id or imply section-level data.

## Processed output: `data/processed/course_term_metrics.csv`

The processed table is aggregated at course-term grain using:

`Year, Term, Subject, Number, Course Title`

It contains those group keys, summed `A+` through `F` counts, summed `W` and
`Students`, `grade_total`, `grade_point_mean`, `W_proxy` (legacy compatibility
alias), `w_mark_share`, and `share_*` fields. `Students` remains the A+–F final
grade-record count and equals the summed A+–F bands. The grade counts are
course-term totals across instructor records; a course-term may contain
multiple instructors and is not a section count, registration count, or
unique-student count.

### Formulas

- `grade_total = sum(A+ through F)`.
- `Students = sum(A+ through F)` in the source record and after course-term aggregation.
- `share_G = sum(G) / grade_total` when `grade_total > 0`; otherwise `NA`.
- `grade_point_mean = sum(grade count × documented 4.0-style grade points) / grade_total` when `grade_total > 0`.
- `w_mark_share = sum(W) / (sum(Students) + sum(W))` when both sums are available
  and the denominator is positive; otherwise `NA`.

`W` is the observed count of formal Withdraw marks. `w_mark_share` is a
derived share, not an official withdrawal rate; it must not be described as a
section-level/student-level withdrawal measure. `W_proxy` is retained only as
a legacy compatibility field name for the same derived share. `grade_point_mean`
is an estimated grade-profile mean, not an official student GPA.

## Quality report

`data/processed/data_quality_report.json` contains:

| Key | Meaning |
| --- | --- |
| `raw_rows` | Number of rows in the complete raw source table. |
| `filtered_rows` | Number of rows after the year and term filter. |
| `course_term_rows` | Number of course-term aggregate rows. |
| `window`, `terms` | The selected governance window and main terms. |
| `filtered_missing_counts` | Missing-value counts by column in the filtered table. |
| `raw_non_numeric_counts_in_scope` | Non-numeric counts for raw numeric columns within the selected window and terms. |
| `duplicate_rows` | Rows participating in duplicate source instructor-grain keys. |
| `source_grain`, `metrics_grain` | Explicit source and processed-table grain descriptions. |
| `filter_order` | Ordered record of validation, filtering, coercion, and aggregation. |
| `w_mark_share_formula` | The exact derived W-mark share formula and validity condition. |
| `no_section_id` | Evidence that no section identifier was inferred or produced. |

Course Explorer access was stopped by an access-protection response during
acquisition; no Course Explorer fields are guessed into the GPA tables. The
response details are retained in the acquisition record for reproducibility,
but are not an analysis measure.

## Phase 5 output tables

`data/processed/course_term_demand_metrics.csv` retains the course-term
metrics and adds:

| Column | Meaning |
| --- | --- |
| demand_proxy | `Students + W`; a demand proxy, not registration or unique-student count. |
| is_high_demand | True when `demand_proxy` is at or above the selected-window 75th percentile. |
| demand_rank | Descending rank across valid course-term demand proxies. |
| w_proxy_rankable | Compatibility field: True when the W-mark share is valid and demand proxy is at least the configured minimum of 20. |
| w_proxy_rank | Compatibility field: descending W-mark-share rank among rankable course-term rows. |

`data/processed/course_demand_summary.csv` is at course-key grain
(`Subject`, `Number`, `Course Title`). It contains the number of observed
course-terms and years, total/mean/median/max demand proxy, total Students
and W, the weighted W-mark share, and high-demand term/year counts. The weighted
W-mark share is calculated from valid demand rows as `sum(W) / sum(demand_proxy)`;
it is not an official withdrawal rate.

`data/processed/phase5_report.json` records the selected window and terms,
year-term coverage, thresholds, formulae, row counts, top rankings, and the
limitations that follow from the GPA source's lack of section and student
identifiers.

## Phase 6 modeling outputs

`scripts/analyze_phase6.py` reads the Phase 5 course-term table, filters the
approved three-year window and spring/fall terms before feature engineering,
and writes the following deterministic files:

| File | Grain | Meaning |
| --- | --- | --- |
| `phase6_feature_table.csv` | course-term | Traceability keys, train/holdout split, W-mark target label, predictive features, and audit-only source fields. |
| `phase6_model_metrics.csv` | model-split | Training/holdout row and class counts, AP (Average Precision), ROC-AUC, F1, precision, recall, balanced accuracy, Brier score, confusion matrix and Recall@20%. |
| `phase6_predictions.csv` | model-course-term | Actual label, predicted probability, 0.5 decision, split, course identity, W-mark share and fixed threshold used. |
| `phase6_feature_importance.csv` | model-encoded-feature | Absolute importance and Logistic Regression coefficient direction, where available. |
| `phase6_course_profiles.csv` | course | Train-only descriptive K-Means cluster, cluster size and silhouette. |
| `phase6_report.json` | report | Window, target threshold, tie policy, class counts, feature controls, model fit status, holdout metrics, profile status and limitations. |

### Phase 6 target and feature controls

`high_w_risk` is computed from valid training-year W-mark-share values only;
the source-compatible field name is `W_proxy`. The
default threshold is the 75th percentile. If that quantile equals the minimum
and inclusive `>=` would label every training row positive, the implementation
uses strict `>` and records this tie policy in the report. The holdout never
changes the threshold.

Predictive features in the older three-year experiment are `course_level`,
`Subject`, `Term`, `Year_offset`, and historical course-level aggregates.
Current-row Students, grade totals and share fields are audit-only because they
are end-of-term outcomes; current-row `W`, `W_proxy`, `demand_proxy`, rank
fields, high-demand flags and the target are also excluded from the model
matrix. Students remains a course-completion A+–F final-grade record count
equal to the A+–F band sum, not a registration-event, unique-student, or
section measure.
`historical_term_count` means the number of observed spring/fall terms in prior
years, not the number of unique students. Historical means are calendar-year
course aggregates and may mix spring and fall within the prior year; they are
not same-term lags in the older experiment. The separate user-approved course
trajectory extension uses stable-course history for 2022–2024: ordinary
courses use any term in prior calendar years, while one-season courses use
same-season lags.

Logistic Regression is the interpretable primary model. Random Forest is a
fixed-seed nonlinear comparator. Both use train-fitted imputation and encoding;
the holdout is used only for final evaluation. The ranking metric is reported as
AP (Average Precision), not PR-AUC; Recall@20% is included because the W-mark
label is imbalanced. Brier score is a probability-calibration error where lower
is better. If a split has one class, undefined ranking/calibration fields are
left null and the status explains why.

K-Means profiles are calculated from train-only course aggregates and are
descriptive. They may include the training W-mark-share mean as a profile input,
which is separate from predictive features and is explicitly disclosed in the
report. A profile is skipped when there are too few rows/features, no valid
silhouette, or a silhouette below the configured quality floor.

When the course-trajectory module is available, its stable-course predictions
and 2024 truth-only evaluation are separate outputs. The identity is always
`Subject + Number`; Course Title is display-only and title changes are recorded
in the title audit. Recognisable Special/Selected Topics are kept as row-level
audit records in `course_trajectory_special_topic_audit.csv`: 3 special-only
stable keys do not enter the ordinary trajectory, while 8 overlapping stable
keys retain their ordinary rows. This is the verified 34 raw records / 11 keys
/ 3 special-only keys / 8 overlapping keys decomposition.
Current-row Students, grade totals, W, shares, and estimated grade means are
audit/truth fields unless the trajectory report explicitly lists a prior-year
version in the model matrix; they must never be described as student-level or
registration data.

## Six-year continuity and EDA outputs

`course_trajectory_continuity.csv` is one row per stable `Subject + Number`
(`course_variant` remains the compatibility value `base`). It records observed
years/terms, exact `observed_periods`, period coverage, Spring/Fall counts and
years, 2021–2023 observed-year coverage, `term_match_mode`, continuity class,
training eligibility, 2024 backtest eligibility, and `excluded_reason`. Missing
offerings are not imputed as zero. `continuous_both_terms`, `seasonal_spring`,
`seasonal_fall`, and `intermittent` are descriptive classes. The generated
report also contains the exact observation-cell distribution used to verify
the intermittent count.

The independent EDA can be reproduced without fitting a model:

```powershell
.\.venv\Scripts\python.exe scripts\generate_course_trajectory_eda.py
```

It writes `course_trajectory_eda_report.json`, `course_trajectory_eda_inventory.csv`, `course_trajectory_eda_year_term_coverage.csv`, `course_trajectory_eda_subject_distribution.csv`, `course_trajectory_eda_numeric_summary.csv`, and `course_trajectory_eda_join_audit.csv`. The report explicitly records source/filtered/metric row and column counts, dtypes, missing cells, exact duplicate rows, annual-term coverage, numeric distributions, source-to-aggregate reconciliation, and join cardinality. Source totals for `Students` and `W` are compared with the course-term aggregate; the expected relationship is many source instructor records to one course-term aggregate.

The actual source has A+ through F grade-count fields, `Students`, `W`, and
`Primary Instructor`, but no numeric GPA, pass-rate, drop event, or withdrawal
timestamp. `W` is a formal Withdraw mark count, not an event timeline.
`w_mark_share` is a derived share and cannot be used to infer an official
withdrawal rate, drop timing, or cause. `grade_point_mean` is an estimated
4.0-style grade-profile mean. A raw duplicate course-term key commonly
reflects multiple instructor/grade-distribution records that are summed during
aggregation; it does not represent duplicate students.

No workbook is currently generated by the trajectory command. Excel export remains pending and must not be claimed complete merely because CSV outputs exist.
