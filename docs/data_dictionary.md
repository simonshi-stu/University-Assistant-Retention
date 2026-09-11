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
| A+ ... F | numeric counts | Count of students receiving each letter grade. |
| W | numeric count | Count of students with a W mark. |
| Students | numeric count | Student count recorded for the row. |
| Primary Instructor | str | Instructor attached to the source record. |

The source grain includes `Year`, `Term`, `Subject`, `Number`, `Course Title`,
`Sched Type`, and `Primary Instructor`. The source has no section id, student
id, or attendance field.

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
`Students`, `grade_total`, `W_proxy`, and `share_*` fields. The grade counts
are course-term totals across instructor records, not section counts.

### Formulas

- `grade_total = sum(A+ through F)`.
- `share_G = sum(G) / grade_total` when `grade_total > 0`; otherwise `NA`.
- `W_proxy = sum(W) / (sum(Students) + sum(W))` when both sums are available
  and the denominator is positive; otherwise `NA`.

`W_proxy` is a withdrawal proxy, not an official withdrawal rate. It must not
be described as an official drop rate or as a section-level/student-level
withdrawal measure.

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
| `w_proxy_formula` | The exact proxy formula and validity condition. |
| `no_section_id` | Evidence that no section identifier was inferred or produced. |

Course Explorer access was blocked by a WAF during Phase 2 acquisition; the
six responses are recorded in `data/raw/acquisition_manifest.json`. No Course
Explorer fields are guessed into the GPA tables.

## Phase 5 output tables

`data/processed/course_term_demand_metrics.csv` retains the course-term
metrics and adds:

| Column | Meaning |
| --- | --- |
| demand_proxy | `Students + W`; a demand proxy, not registration or unique-student count. |
| is_high_demand | True when `demand_proxy` is at or above the selected-window 75th percentile. |
| demand_rank | Descending rank across valid course-term demand proxies. |
| w_proxy_rankable | True when the W proxy is valid and demand proxy is at least the configured minimum of 20. |
| w_proxy_rank | Descending W proxy rank among rankable course-term rows. |

`data/processed/course_demand_summary.csv` is at course-key grain
(`Subject`, `Number`, `Course Title`). It contains the number of observed
course-terms and years, total/mean/median/max demand proxy, total Students
and W, the weighted W proxy, and high-demand term/year counts. The weighted
W proxy is calculated from valid demand rows as `sum(W) / sum(demand_proxy)`;
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
| `phase6_feature_table.csv` | course-term | Traceability keys, train/holdout split, W-proxy target label, predictive features, and audit-only source fields. |
| `phase6_model_metrics.csv` | model-split | Training/holdout row and class counts, PR-AUC, ROC-AUC, F1, precision, recall, balanced accuracy, Brier score, confusion matrix and Recall@K. |
| `phase6_predictions.csv` | model-course-term | Actual label, predicted probability, 0.5 decision, split, course identity, W proxy and fixed threshold used. |
| `phase6_feature_importance.csv` | model-encoded-feature | Absolute importance and Logistic Regression coefficient direction, where available. |
| `phase6_course_profiles.csv` | course | Train-only descriptive K-Means cluster, cluster size and silhouette. |
| `phase6_report.json` | report | Window, target threshold, tie policy, class counts, feature controls, model fit status, holdout metrics, profile status and limitations. |

### Phase 6 target and feature controls

`high_w_risk` is computed from valid training-year `W_proxy` values only. The
default threshold is the 75th percentile. If that quantile equals the minimum
and inclusive `>=` would label every training row positive, the implementation
uses strict `>` and records this tie policy in the report. The holdout never
changes the threshold.

Predictive features are `course_level`, `Subject`, `Term`, `Year_offset`,
`Students`, `grade_total`, available `share_*` columns, and historical
course-level aggregates. Historical fields are calculated only from rows with
strictly earlier years in the selected window. Current-row `W`, `W_proxy`,
`demand_proxy`, rank fields, high-demand flags and the target are excluded from
the model matrix. Current `Students` is kept as a scale control, but remains a
source count excluding W, not a registration-event or unique-student measure.
`historical_term_count` means the number of observed spring/fall terms in prior
years, not the number of unique students. Historical means are calendar-year
course aggregates and may mix spring and fall within the prior year; they are
not same-term lags.

Logistic Regression is the interpretable primary model. Random Forest is a
fixed-seed nonlinear comparator. Both use train-fitted imputation and encoding;
the holdout is used only for final evaluation. PR-AUC and Recall@K are included
because the high-risk label is imbalanced. If a split has one class, undefined
ranking/calibration fields are left null and the status explains why.

K-Means profiles are calculated from train-only course aggregates and are
descriptive. They may include the training W proxy mean as a profile input,
which is separate from predictive features and is explicitly disclosed in the
report. A profile is skipped when there are too few rows/features, no valid
silhouette, or a silhouette below the configured quality floor.
