# Project History Log

This file is append-only. New work must add a dated entry; existing accepted evidence must not be silently rewritten.

## Current status

- Status date: 2026-09-10
- Historical analysis reference date: 2024-01-01
- Current phase: Phase 5 — UIUC demand and W-based withdrawal proxy analysis
- Completion: Phase 4 accepted; Phase 5 implementation is now active
- Active data window: primary candidate, 2021–2023
- DeepSeek model: `deepseek-v4-flash` only
- DeepSeek API key: expected in local `.env`; never recorded in this log
- Primary code executor: DeepSeek V4 Flash
- Supervisor/reviewer: Codex
- Allowed write area: `E:\Projects\course-retention-platform`
- Other repositories modified: none

## Fixed phase order

1. Environment and repository safety
2. Public data acquisition and source documentation
3. Data dictionary and normalized schema
4. Python ingestion, splitting, cleaning, and quality report
5. UIUC demand and W-based withdrawal proxy analysis
6. Logistic Regression, Random Forest comparison, and optional K-Means course profiles
7. Lawfully available course-review sentiment and topic analysis
8. Schedule-conflict graph and schedule-change analysis
9. Local website/dashboard and Excel export
10. Lean validation, visual cross-check, documentation, and resume evidence record

## Acceptance focus

The final dashboard and report must answer or explicitly document why the data cannot answer:

1. Which course combinations have the most severe conflicts?
2. Which time slots carry too many high-demand courses?
3. Which departments have concentrated conflicts among core courses?
4. Are some courses feasible only in low-demand time slots?
5. Is a schedule change associated with later course-selection volume?

## 2026-09-10 — Repository initialization

### Work completed

- Cloned the user-provided empty GitHub repository into the allowed workspace.
- Added local DeepSeek environment configuration and a committed example template.
- Added `.gitignore` rules preventing `.env`, private data, generated datasets, caches, and local databases from being committed.
- Added `AGENTS.md`, `PROJECT_SCOPE.md`, and `TEMPORAL_DATA_POLICY.md`.

### Decisions

- All DeepSeek calls use `deepseek-v4-flash`; V4 Pro is prohibited.
- Codex is a supervisor/reviewer, not the primary feature-code author or task scheduler.
- DeepSeek produces implementation code and first-pass analysis; Codex checks and accepts or rejects it.
- Validation is intentionally lean: data meaning, cleaning logic, totals, joins, metrics, one reproducible run, one dashboard smoke run, and visual/result cross-checks.

### Data-window policy

- Primary: 2021–2023; train 2021–2022, hold out 2023.
- Fallback: 2022–2024; train 2022–2023, hold out 2024.
- Last resort: 2023–2025; train 2023–2024, hold out 2025.
- Window sufficiency is evaluated per module.
- No 2026+ source data is allowed.
- OULAD is excluded from the main analysis because its principal course data fall outside the requested year windows.

### Evidence currently available

- Governance and configuration documents exist in the allowed repository.
- No source dataset has been downloaded or inspected yet.
- No cleaned table, model, dashboard, Excel workbook, or result metric exists yet.

### Current blockers and next acceptance point

- DeepSeek execution cannot begin until the user places a valid API key in the local `.env` file.
- The next acceptance point is a source inventory for UIUC Course Explorer, UIUC GPA data, public enrollment data, and legally accessible course-review data, including year coverage and field definitions.

### Resume evidence status

- No new resume claim is supported yet.
- The project remains a 2026 independent extension unless contemporaneous evidence proves that a specific output was completed during ATLAS.

## 2026-09-10 — Phase 2 acquisition evidence accepted

### Reproducible checks

- `compileall` completed successfully for `src`, `scripts`, and `tests`.
- The lean acquisition suite passed: 9 tests passed.
- The real acquisition CLI ran against the configured primary window `(2021, 2022, 2023)` and terms `spring`/`fall`.
- GPA raw file: 79,918 rows, 8,563,298 bytes, SHA-256 `a997a3c8e9139c21f816f95ebed5d8b1c707599715bb6fd4410ffaf508941bf4`.
- The GPA source currently contains years 2010–2026; only the approved module window will be used downstream. The raw file's 2026 rows are not eligible for this project.
- The manifest records six Course Explorer requests. All six returned HTTP 202 with `x-amzn-waf-action: challenge`, `Content-Type: text/html; charset=UTF-8`, and no XML file was accepted or fabricated.
- The CLI returned status `incomplete` because Course Explorer was blocked; the failure manifest is retained at `data/raw/acquisition_manifest.json`.

### Supervisor decision

- Phase 2 is accepted for source acquisition evidence with a documented Course Explorer access limitation.
- GPA processing may continue into Phase 3 using the primary window after explicit year/term filtering.
- Course Explorer-dependent schedule analysis remains data-insufficient unless a lawful, reproducible XML acquisition path becomes available; no fallback year window changes the observed WAF access condition.
- Phase 3 is now active: normalized schema, field dictionary, and deterministic GPA cleaning/validation are required next.

## 2026-09-10 — Phase 3 normalization evidence accepted

### DeepSeek review and corrections

- DeepSeek-generated normalization drafts were reviewed and rejected when they
  introduced student-level or invented section schemas, wrong imports, wrong
  function signatures, incomplete required-column checks, or the incorrect
  `W / Students` formula.
- The accepted implementation uses the actual UIUC GPA 24-column header,
  package-relative imports, governance-approved windows, spring/fall filtering
  before aggregation, course-term output keys, and the exact
  `W / (Students + W)` proxy formula.
- The accepted CLI and eight offline normalization tests use the reviewed
  module; no network call or runtime LLM is involved.

### Reproducible output evidence

- `scripts/normalize_data.py` completed successfully from the downloaded raw
  file and wrote interim, processed, and quality-report artifacts.
- Raw rows: 79,918. Filtered rows: 14,879. Filtered years: 2021–2023.
- Filtered terms: spring and fall only. No filtered row has year 2026 or later.
- Course-term metric rows: 8,973. The metric group key is unique.
- Numeric sum reconciliation between filtered rows and course-term metrics
  passed for A+–F, W, and Students.
- Filtered missing values: 13 `Primary Instructor` cells; all other reported
  filtered columns had zero missing values. Raw in-scope numeric columns had
  zero non-numeric values.
- The quality report records 29,985 rows participating in duplicate source
  instructor-grain keys. Because the source has no section id, this evidence is
  retained for review and is not silently deduplicated.

### Supervisor decision

- Phase 3 is accepted for the available GPA source and primary window.
- The exact data dictionary is at `docs/data_dictionary.md`; the reproducible
  outputs are under `data/interim` and `data/processed`.
- Course Explorer remains unavailable after six documented WAF challenges;
  section schedule, conflict graph, and schedule-change analyses cannot begin
  until a lawful reproducible section-level source is available.
- Phase 4 is active: ingestion/splitting/cleaning validation must build on the
  accepted normalized tables without using 2026+ source rows.

## 2026-09-10 — Execution resumed and workspace path corrected

### Supervisor review

- Re-read `AGENTS.md`, `PROJECT_SCOPE.md`, `TEMPORAL_DATA_POLICY.md`, the resume evidence boundary, the local-dashboard guidance, and the spreadsheet creation and verification requirements.
- Confirmed that the active writable repository is `E:\Projects\course-retention-platform`; older references to `E:\Projects\resume generation\course-retention-platform` were stale governance text and have been corrected only in this repository.
- Confirmed that `.env` exists, the API key is non-empty, the requested model is `deepseek-v4-flash`, and the DeepSeek API returned a successful connectivity response. The provider normalized the response model name to `deepseek-flash`; both names will be recorded in later execution evidence.
- Confirmed bundled Python 3.12.14, Node.js 24.19.0, and Git 2.53.0 are available without writing outside the repository.

### Resume and scope boundary

- This platform remains an independent project beginning on 2026-09-10.
- No implementation result may be written into the 2024 ATLAS experience without separate contemporaneous evidence.
- No implementation, data acquisition, model result, dashboard, or workbook is accepted yet; Phase 2 remains the next acceptance point.

## 2026-09-10 — Phase 2 DeepSeek review attempts

### DeepSeek provenance

- Every generation request used the configured request name `deepseek-v4-flash`; the provider returned the normalized model name `deepseek-flash`.
- File-generation calls used disabled thinking after enabled thinking exhausted the response budget without returning usable file content.

### Rejected outputs

- Rejected the first Phase 2A response because it declared an unapproved MIT license, left institutional source URLs blank, and imposed a stale `pyarrow<18` constraint.
- Rejected the next Phase 2A response because it incorrectly made the entire project aggregate-only, removed the GPA and Course Explorer source definitions, changed Python compatibility, and broke the ordered year windows.
- Accepted only the DeepSeek-authored Phase 2A package/configuration skeleton and source notes after exact source URLs, three-year windows, repository-root paths, dependency ranges, and evidence boundaries were corrected.
- Rejected multiple Phase 2B acquisition drafts for concrete defects including wrong universities in the host allowlist, nonexistent modules or configuration keys, missing GPA acquisition, invalid Course Explorer endpoints, incompatible `validate_window` calls, missing dependencies, syntax errors in tests, cumulative manifests, and implementation/test mismatches.
- The current `src/course_retention/acquisition.py` is a DeepSeek-authored unaccepted draft retained for correction. It is not runnable because it imports a nonexistent `.windows` module and does not yet satisfy the reviewed retry, term-validation, cache, and failure-manifest contract.

### External-source evidence

- Verified the GPA source documentation states that `Students` excludes `W`; the future W-based proxy denominator is therefore `Students + W`.
- Verified the official Course Explorer public API is documented as unauthenticated XML access.
- Direct probes of 2023 Course Explorer XML endpoints returned HTTP 202 with `x-amzn-waf-action: challenge`, `Content-Length: 0`, and no XML body. No section data were fabricated or substituted.

### Current decision and blocker

- Phase 2 is not accepted. Phases 3–10 have not started.
- Safe external-call policy allows sending minimized requirements to DeepSeek but blocked sending the non-public local draft back for correction. Continuing under the fixed role split requires explicit user authorization to transmit that draft code to the configured DeepSeek API, or a change in role authority allowing Codex to correct implementation code locally.

## 2026-09-10 — Phase 4 ingestion, splitting, cleaning, and validation accepted

### Supervisor review after disk-space recovery

- Re-read the repository agreement and confirmed that the active writable
  repository remains `E:\Projects\course-retention-platform`; no other
  repository or desktop file was modified.
- Reviewed the DeepSeek-authored `src/course_retention/validation.py` and
  `scripts/validate_data.py` against the approved primary window, spring/fall
  term filter, course-term grain, exact W proxy formula, and chronological
  train/holdout split.
- Confirmed that the validation layer does not infer a section id, silently
  turn missing numeric values into zero, or use any 2026+ source rows.

### Reproducible checks

- `compileall` passed with a repository-local bytecode prefix, avoiding stale
  bytecode cache files left by the earlier full-disk interruption.
- The offline test suite passed: 17 tests passed (9 acquisition, 8
  normalization); no network call or runtime LLM was used.
- A fresh normalization and validation rerun completed successfully using the
  raw GPA file and wrote an independent verification copy under
  `.tmp/phase4_rerun` because the pre-existing generated files in
  `data/interim` and `data/processed` could not be overwritten by the current
  sandbox process. The existing standard artifacts were read-only checked and
  retained; no source data were deleted.
- Recomputed evidence: raw rows 79,918; filtered rows 14,879; course-term
  metric rows 8,973; temporal training rows 5,933; holdout rows 3,040.
- All validation checks passed: required columns, selected years and terms,
  unique course-term keys, W proxy range, source-to-metric column sums, and
  train/holdout split. The filtered table has 13 missing `Primary Instructor`
  values and no reported missing values in the other filtered columns; the
  quality report records 29,985 rows participating in duplicate instructor-
  grain keys, which were not silently deduplicated.

### Supervisor decision and next step

- Phase 4 is accepted for the available UIUC GPA source and primary window
  `(2021, 2022, 2023)`.
- The Phase 4 evidence does not unlock section scheduling: Course Explorer
  remains blocked by the documented WAF challenge, and the GPA source has no
  section, student, or attendance fields.
- Phase 5 is now active. Its acceptance point is a course-level demand and
  W-based withdrawal-proxy analysis with explicit denominators, source grain,
  year coverage, limitations, and traceable output tables; it must not be
  described as registration counts, official withdrawal rates, attendance,
  or causal retention effects.

### Resume evidence boundary

- No new ATLAS claim is supported. This independent project remains dated from
  its actual 2026-09-10 development start.

## 2026-09-10 — Phase 5 DeepSeek implementation attempts rejected

### Supervisor decision

- Phase 5 is active, but no Phase 5 implementation or output artifact is
  accepted yet.
- Multiple requests to the configured `deepseek-v4-flash` request name
  (provider response name: `deepseek-flash`) were reviewed before any file was
  written. Rejected defects included nonexistent imports, incompatible public
  function signatures, `W / Students` in place of `W / (Students + W)`,
  `Students * W` in place of `Students + W`, averaging ratios, missing
  spring/fall filtering, incorrect year windows, dropped grade columns,
  unsupported capacity/waitlist fields, and omitted output writers.
- The latest narrow request also returned a capacity/waitlist model unrelated
  to the accepted GPA schema. No rejected response was copied into
  `src/`, `scripts/`, `tests/`, or `docs/`.

### Current evidence and next acceptance point

- Phase 4 remains the latest accepted implementation. Its source, normalized
  tables, validation report, and 17-test evidence remain unchanged.
- Phase 5 still requires a DeepSeek-produced and supervisor-reviewed demand
  and W-proxy module, CLI, offline tests, documentation, and deterministic
  output tables. The required contract remains: demand proxy
  `Students + W`; W proxy `W / (Students + W)` from aggregated counts; only
  2021–2023 spring/fall rows; no registration, attendance, section, or causal
  claims.
- Because no valid Phase 5 code was returned, no Phase 5 metric, ranking, or
  business interpretation is reported as complete.

## 2026-09-10 — Phase 5 demand and W-proxy implementation accepted

### Authorization and implementation

- The user explicitly authorized Codex to correct implementation code directly
  for this continuation. All changes remained inside
  `E:\Projects\course-retention-platform`.
- Added `src/course_retention/phase5.py` and
  `scripts/analyze_phase5.py`. The implementation is deterministic and has no
  network or runtime LLM dependency.
- Added six offline Phase 5 tests in `tests/test_phase5.py` and configured the
  repository pytest path so the full suite runs from the repository root.
- Added the Phase 5 method/result note at `docs/phase5_analysis.md` and
  extended `docs/data_dictionary.md` and `README.md` with the new fields and
  run command.

### Accepted formulas and outputs

- The module filters to the approved primary window `(2021, 2022, 2023)` and
  `spring`/`fall` before ranking or course aggregation.
- `demand_proxy = Students + W`; the source documents `Students` as excluding
  W. `W_proxy = W / (Students + W)` is recomputed from the course-term
  aggregate and is explicitly not an official withdrawal rate.
- W-proxy ranking uses `demand_proxy >= 20` as a denominator-stability screen.
  The full proxy remains present in the course-term output.
- Generated artifacts:
  `data/processed/course_term_demand_metrics.csv`,
  `data/processed/course_demand_summary.csv`, and
  `data/processed/phase5_report.json`.

### Reproducible supervisor checks

- Full offline suite: 23 tests passed.
- `compileall` passed for `src`, `scripts`, and `tests`.
- Real Phase 5 run: 8,973 course-term rows, 3,336 course keys, 152 subject
  keys; all 8,973 rows had valid demand and W proxy values.
- Year-term coverage was complete for all six primary-window spring/fall
  combinations. Totals reconciled between the course-term and course-summary
  outputs: Students `1,003,282`, W `3,483`, demand proxy `1,006,765`.
- Recomputed formulas passed exactly within floating-point tolerance; both
  output keys were unique.
- A second run into `.tmp/phase5_run2` produced byte-identical SHA-256 files:
  course-term metrics `E40EA91448BA8E81A0DCD2F0EFD6CAFC67A378896272E25AC5A83D83F9BBC569`,
  course summary `1A986F64544E3095DA12ED2335A48978513D8D9070A4A57FD3A22FE4930E2A31`,
  and report `65F9F8358E2742B0952AB12E545E45B78F6538DA40046A0CFF8B774999181268`.
- The 75th-percentile high-demand threshold was `105`. The highest observed
  W proxy among rows meeting the minimum demand screen was MACS 395,
  `Documentary & Music Culture`, 2021 fall, `3 / 30 = 0.10`.

### Supervisor decision

- Phase 5 is accepted for descriptive UIUC demand and W-based withdrawal-proxy
  analysis on the available GPA source and primary window.
- The phase does not provide registration-event counts, unique-student
  counts, section schedules, capacity/waitlist, attendance, student-level
  outcomes, or causal retention effects. Course Explorer remains WAF-blocked;
  schedule-conflict questions 1–5 remain explicitly unsupported and are not
  replaced by fabricated or inferred fields.
- Next phase: Phase 6 — time-aware Logistic Regression and Random Forest
  comparison, with the Phase 5 proxy definitions carried forward.
