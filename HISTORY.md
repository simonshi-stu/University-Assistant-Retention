# Project History Log

This file is append-only. New work must add a dated entry; existing accepted evidence must not be silently rewritten.

## Current status

- Status date: 2026-09-14
- Historical analysis reference date: 2024-01-01
- Current phase: Phase 6 accepted; independent 2024 same-term trajectory extension accepted; Phase 7 is next
- Completion: Phase 6 and the user-approved six-year trajectory extension are accepted for the available GPA source; the local bilingual dashboard is updated; Phase 7 is next
- Active data window: primary 2021–2023; separate independent trajectory extension 2019–2024
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

## 2026-09-11 — Phase 6 DeepSeek generation blocked after five attempts

### Supervisor review

- Re-read `AGENTS.md`, `PROJECT_SCOPE.md`, `TEMPORAL_DATA_POLICY.md`,
  `README.md`, `docs/data_dictionary.md`, `docs/SOURCES.md`,
  `docs/phase5_analysis.md`, the complete prior history, and the accepted
  Phase 4/5 implementation before starting Phase 6.
- Confirmed that the repository still contains no Phase 6 module, model
  outputs, dashboard, or workbook, and that the latest accepted status is
  Phase 5.

### DeepSeek provenance and rejected attempts

- The configured request name was `deepseek-v4-flash`; the provider reported
  `deepseek-flash`. A minimal connectivity request returned `PING`, confirming
  that the local key and endpoint can authenticate.
- The first full request was blocked by the sandbox because it attempted to
  send local source/document contents to the external endpoint. A safer,
  minimized contract-only request was then used after external access was
  explicitly reviewed; no local source code, history, or raw data was sent.
- Five Phase 6 implementation-generation attempts were counted. The returned
  message content was empty on each generation attempt, including a final
  compact request; no DeepSeek code was copied into `src/`, `scripts/`,
  `tests/`, or `docs/`.

### Current decision and blocker

- Phase 6 is not accepted and no model result or dashboard claim is supported.
- The task is paused at the user-requested five-attempt limit. Further work
  requires either user authorization for Codex to write the primary Phase 6
  implementation directly, or a user-approved change to the local DeepSeek
  thinking/output configuration followed by a fresh request.
- No repository outside `E:\Projects\course-retention-platform` was modified.

## 2026-09-11 — Phase 6 implementation, DeepSeek audit, and local dashboard accepted

### Authorization and implementation

- The user explicitly authorized Codex to implement the primary Phase 6 code,
  local dashboard, data explanations, and README after five earlier DeepSeek
  generation attempts returned empty content.
- Added `src/course_retention/phase6.py`, `scripts/analyze_phase6.py`,
  `tests/test_phase6.py`, `docs/phase6_modeling.md`, and
  `dashboard/app.py`. Extended `README.md` and `docs/data_dictionary.md` with
  Phase 6 field meanings, formulas, feature controls, outputs, and limits.
- The implementation stays deterministic at runtime: no network call or LLM
  is required for ingestion, feature construction, modelling, report writing,
  or dashboard rendering.

### DeepSeek audit and Codex disposition

- Sent the completed core module, CLI, tests, and dashboard to the configured
  `deepseek-v4-flash` request endpoint for review only. The provider reported
  `deepseek-flash` and returned an audit report, not replacement code.
- DeepSeek verified the temporal split, training-only target threshold,
  current-row leakage exclusions, strict prior-year history construction,
  train-fitted preprocessing, model setup, robust metrics, deterministic
  outputs, and unsupported scheduling display.
- Codex accepted the verified strengths and corrected the material findings:
  historical joins now use an indexed many-to-one merge with order assertion;
  `historical_term_count` is named as a term count; `Year_offset` avoids an
  unseen 2023 one-hot category; K-Means report metadata explicitly discloses
  that training W proxy is a descriptive profile input; the JSON report now
  includes the approved-window decision, proxy definitions, and five
  machine-readable `unsupported` scheduling question records; the dashboard
  handles the available model/profile outputs and the tests cover these
  controls.
- A latent serializer edge case and single-class metric warning were also
  removed. The DeepSeek report's lower-priority observations about catalog
  number truncation and current grade features are documented limitations,
  not evidence of an acceptance failure.

### Accepted Phase 6 outputs and results

- The approved primary window is 2021–2023 with spring/fall; feature rows are
  8,973, with 5,933 train rows and 3,040 holdout rows. No output row is from
  2026 or later, and feature row IDs and prediction model/row keys are unique.
- Training W proxy 75th percentile is `0.0`. Because inclusive `>= 0` would
  label all training rows positive, the documented tie policy uses strict
  `W_proxy > 0`: 1,152 train positives / 4,781 negatives and 608 holdout
  positives / 2,432 negatives.
- Holdout Logistic Regression: PR-AUC `0.5228`, ROC-AUC `0.7462`, F1
  `0.3971`, precision `0.2587`, recall `0.8536`, balanced accuracy `0.6211`,
  Brier `0.3347`, Recall@20% `0.4885`.
- Holdout Random Forest: PR-AUC `0.5556`, ROC-AUC `0.7725`, F1 `0.4964`,
  precision `0.4866`, recall `0.5066`, balanced accuracy `0.6865`, Brier
  `0.1512`, Recall@20% `0.5016`. RF improves ranking/F1 over the majority
  baseline and Logistic comparator, while Logistic remains the primary
  interpretable model under the project strategy.
- K-Means ran descriptively on 2,895 train-course keys with K=2 and silhouette
  `0.4982`; cluster sizes are 2,784 and 111. W proxy is disclosed as a
  profile input and is not used in the predictive feature matrix.
- Generated files are `phase6_feature_table.csv`, `phase6_model_metrics.csv`,
  `phase6_predictions.csv`, `phase6_feature_importance.csv`,
  `phase6_course_profiles.csv`, and `phase6_report.json` under
  `data/processed`.

### Reproducible validation

- Latest offline suite: 32 tests passed with `PYTHONDONTWRITEBYTECODE=1` and
  pytest cache disabled. AST parsing passed for `src`, `scripts`, and
  `dashboard` Python files.
- A second full Phase 6 run matched all six generated file SHA-256 values,
  including the report after rounding cluster-center display values for stable
  serialization. The latest report hash is
  `B85F78FA77757AFED131E5B6E4D633BA33EB44D059EB3CA3D67AB56008ECB93A`.
- Streamlit started successfully and returned HTTP 200 with the dashboard
  HTML on local port 8507; the test process was stopped afterward.
- The dashboard explicitly marks all five scheduling questions unsupported
  because Course Explorer remains WAF-blocked and the GPA source has no
  section time, capacity, core-course, or schedule-change fields.

### Supervisor decision and evidence boundary

- Phase 6 is accepted for time-aware association/screening analysis on the
  available public GPA source. Random Forest is the stronger nonlinear
  comparator on this holdout, but neither model establishes causal retention
  effects or an official withdrawal rate.
- The local dashboard summarizes the available Phase 3–6 results as requested;
  Excel export, lawful review text, section scheduling, and later phases remain
  separate work and are not claimed as complete.
- This independent project remains dated from its actual 2026-09-10 start and
  is not an ATLAS internship result.

## 2026-09-11 — Strict end-of-term leakage revision superseded provisional Phase 6 metrics

### Supervisor decision

- During final review, Codex identified that current-row `Students`, grade
  totals, and grade shares can be end-of-term outcomes. Although they are not
  W fields, using them to predict the same row's W label would weaken the
  project's historical-feature interpretation. They are now audit-only fields.
- The accepted predictive matrix is restricted to course level, Subject, Term,
  numeric `Year_offset`, and strictly earlier-year course aggregates: prior W
  proxy, prior demand proxy, prior Students, prior grade totals, prior grade
  shares, and prior observed term count. This is a deliberate accuracy-first
  revision, not a result-selection optimization.
- The earlier Phase 6 metrics in the preceding entry were generated before
  this stricter feature control and are superseded for reporting. The formal
  outputs and README/docs now use the strict version below.

### Final strict run

- The primary 2021–2023 window still produces 8,973 rows: 5,933 train and
  3,040 holdout. The train-only threshold remains `0.0` with strict `>` tie
  policy and class counts 1,152/4,781 train and 608/2,432 holdout.
- Strict Logistic Regression holdout metrics: PR-AUC `0.5029`, ROC-AUC
  `0.7357`, F1 `0.4154`, precision `0.2851`, recall `0.7648`, balanced accuracy
  `0.6427`, Brier `0.2742`, Recall@20% `0.4786`.
- Strict Random Forest holdout metrics: PR-AUC `0.5293`, ROC-AUC `0.7538`, F1
  `0.4971`, precision `0.4505`, recall `0.5543`, balanced accuracy `0.6926`,
  Brier `0.1712`, Recall@20% `0.4836`.
- K-Means remains K=2, silhouette `0.4982`, with cluster sizes 2,784 and 111;
  its descriptive W proxy input remains explicitly disclosed and separate from
  prediction features.
- Final deterministic SHA-256 values are:
  `A3816B8BDFC910D51F613F5B1BA1107A42195D515A4D0BB4AE74A002090BBCF9` for
  the feature table, `E39A1B8A09F4BB4D2A1681E4CA8331C2625DF1D08560F7B1C36234500064DB91`
  for model metrics, `503E65C46B59C9FE32E9823582F38B5D4A0C0BF756C46E3CA65EEC40DF02915D`
  for predictions, `B2022A869DC60BE325BE0CA741DAD43FFCF73181CF3738CC34D6A43A9DD3EA89`
  for profiles, `51767822C6A9BC9B46733A202721FD0F9A5CB7B4D963090C733609E8B50ED361`
  for feature importance, and `3C2BFBC94C4EA171DF365C1097093B0A080DC0E398940DE044B84FFED50344C8`
  for the final report.
- The final strict code passes 32 offline tests, AST syntax checks pass, and a
  Streamlit smoke run on local port 8507 returned HTTP 200. No other
  repository was modified.

## 2026-09-11 — Final Phase 6 evidence-chain fields regenerated

- Added final report transparency fields for per-split historical feature
  coverage, calendar-year aggregation semantics, profile columns actually used
  after missing-column removal, training/holdout class status, and robust
  dashboard fallback behavior. These changes do not alter the strict model
  matrix or the reported holdout metrics.
- Final Phase 6 outputs were regenerated and matched a second run byte-for-byte.
  The final `phase6_report.json` SHA-256 is
  `A99E9A15D26566EE7F5BCE5AF6E10029A1512C3D2058DA853F85B9B24FD08322`.
- Latest test evidence remains 32 passed; the final dashboard smoke run on
  local port 8509 returned HTTP 200. The HTML shell check is complemented by
  the source-level dashboard limitation test; the app itself does not claim
  unsupported section scheduling capabilities.

## 2026-09-11 — Dashboard explanation and scope-boundary revision

### User-facing changes

- Kept the existing five-page structure, wide layout, chart types, colors, and
  core filters; added compact page guidance, data inventory, limitation paths,
  K-Means interpretation, and a plain-language explanation of Streamlit's
  Deploy entry point.
- Removed internal phase wording from user-facing dashboard titles, captions,
  warnings, navigation, and conclusions. Internal output filenames and agent
  history remain unchanged for reproducibility.
- Made the overview demand ranking use the active year/term/subject scope and
  the shared Top-N control. The feature-importance chart now uses the same
  Top-N control and its scope is shown in the caption.
- Explained the current K=2 result as a scale-oriented course profile: the
  two cluster centers have similar W-proxy levels, so the clusters are not
  interpreted as high/low withdrawal causes.
- Added explicit statements that the available GPA source has no student-level
  attendance, LMS activity, registration-event, section-time, capacity, or
  waitlist fields; added a feasible remedy or fallback for each limitation.

### Governance and documentation

- Added `docs/DASHBOARD_CHANGE_BOUNDARY.md` to constrain later agents to
  evidence and explanation improvements without redesigning the dashboard.
- Linked that boundary from `AGENTS.md` and expanded the README with the
  dashboard purpose, page guide, data meaning, verified results, Deploy
  explanation, future multi-school route, and likely users.

### Validation to rerun before acceptance

- 32 existing offline tests remain the minimum regression check.
- Re-run Python compilation, the full test suite, and one local Streamlit HTTP
  smoke run after the dashboard patch.
- Cross-check the displayed Top-N rankings, cluster descriptions, formulas,
  labels, and limitation tables against `data/processed` outputs.

## 2026-09-11 — Dashboard patch validation accepted

- Read-only Python compilation passed for all 13 Python files in `dashboard`,
  `src/course_retention`, and `scripts` without writing new bytecode caches.
- The existing offline suite remains green: 32 tests passed.
- A local Streamlit run on port 8510 loaded the overview, guidance expander,
  risk page, course-profile page, and data/limitations page successfully.
- Browser smoke verification confirmed that changing Top-N changes the ranking
  titles and feature-importance caption, while the model metrics remain fixed.
- Cross-checked displayed counts against generated outputs: 8,973 rows, 3,336
  course keys, 152 subjects, K=2, silhouette 0.4982, cluster sizes 2,784/111,
  and Random Forest holdout PR-AUC 0.5293.
- No external deployment or UI action was performed; the local server was used
  only for validation.
## 2026-09-14 — User-approved independent 2024 same-term trajectory extension

### Implementation evidence pending supervisor acceptance

- The user explicitly authorized this Luna implementation sub-agent to write
  the new module, script, lean tests, and generated outputs in this repository;
  this is a one-turn exception to the default DeepSeek implementation role.
- Added `src/course_retention/course_trajectory.py` and
  `scripts/analyze_course_trajectory.py`. The stable course key is
  `Subject + Number`; `Course Title` is display-only and a title-change audit
  records 289 changed keys. Raw data are filtered before aggregation to the
  six allowed years (2019–2024) and Spring/Fall.
- Same-term lag design is explicit: 2022 uses 2019–2021, 2023 uses 2020–2022,
  and 2024 uses 2021–2023. Incomplete three-year same-term histories are
  excluded from train/holdout metrics. Current 2024 W/Students/grades are
  retained only for post-prediction comparison.
- Generated `course_trajectory_table.csv`, `course_trajectory_predictions.csv`,
  `course_trajectory_metrics.csv`, `course_trajectory_logistic_coefficients.csv`,
  `course_trajectory_title_audit.csv`, and `course_trajectory_report.json`.
  The report contains Spring/Fall/all metrics, confusion counts, AP, ROC-AUC,
  Brier, Recall@20%, coefficient odds ratios/support, title audit, and annual W
  summaries. 2024 eligible holdout coverage is 1,597 rows (Spring 742, Fall
  855) out of 3,027 course-term rows; training cohort is 2,981 rows.
- 2024 all-scope holdout: Logistic AP 0.6105, ROC-AUC 0.7671, Brier 0.1959,
  Recall@20% 0.4813, confusion TN/FP/FN/TP 842/327/128/300; Random Forest
  AP 0.6056, ROC-AUC 0.7632, Brier 0.1858, Recall@20% 0.4696,
  confusion 915/254/159/269. The target is `W > 0` (a W marker), not a
  high official withdrawal-rate label or a count forecast.
- The annual W audit records sparse 2020 Fall (12 positive rows, W total 14)
  and 2021 Spring (10 positive rows, W total 10) observations for review.
  These are data characteristics, not causal explanations.
- Added three focused tests in `tests/test_course_trajectory.py`; they passed
  (`3 passed`). The new script completed once with the real raw file. Existing
  Phase 6 metadata was corrected so `Subject` is not simultaneously listed as
  a used and excluded predictive feature.

### Remaining limits

The six-year extension still uses course-level aggregate GPA data without
student IDs, registration events, sections, capacity, attendance, or causal
treatments. The same-term cohort restriction improves temporal comparability
but reduces coverage and cannot establish an official withdrawal rate or
causal retention effect. Unknown holdout Subject categories are encoded as
all-zero one-hot values by the documented `handle_unknown` policy.

## 2026-09-14 — Independent review return and corrective regeneration

- Independent review returned the first trajectory output for a P1 identity
  issue: raw `Subject + Number` keys merged same-term special-topic titles.
  The implementation now normalizes title punctuation/spacing, creates a
  `course_variant` only for base keys with same-term normalized-title
  collisions, and uses that variant across all years. Ordinary courses keep a
  `base` variant so cross-year title edits remain linked.
- Regenerated output is marked `generated_pending_supervisor_review`. It has
  3,603 base course keys, 4,157 variants, 104 collision base keys, 376
  collision course-term groups, and 313 base keys with cross-year title
  changes. Predictions now include `course_variant` in their unique key.
- Predictive features were reduced to course level, same-term lag1–3
  `W_proxy`, and lag1 `log1p(demand_proxy)` scale, plus Subject/Term. The
  categorical reference is selected by training support and coefficients
  include drop-index-derived references, support counts, and low-support
  warnings. Constant and persistence baselines do not report Recall@20% when
  tied probabilities make row-level ranking arbitrary.
- Real regeneration completed: training cohort 2,935 rows and 2024 holdout
  cohort 1,578 rows. Holdout all-scope Logistic AP 0.6166, ROC-AUC 0.7699,
  Brier 0.1987, Recall@20% 0.4727, TN/FP/FN/TP 805/352/127/294; Random Forest
  AP 0.6049, ROC-AUC 0.7664, Brier 0.1913, Recall@20% 0.4679,
  TN/FP/FN/TP 870/287/136/285.
- Focused trajectory tests pass (`5 passed`). Full-suite dashboard compatibility
  failure remains outside this sub-agent's assigned files.

## 2026-09-14 — Second independent review return and conservative identity fix

- Review returned the previous variant rule because it split only same-term
  collisions. The corrected conservative rule first counts normalized titles
  over the full 2019–2024 scope for each `Subject + Number`: any base key with
  more than one normalized title uses normalized title variants in every year;
  only a six-year single-title base uses `base`.
- Only trim/lower/collapse whitespace and punctuation are normalized. Acronyms,
  abbreviations, substantive renames, and rotating topic titles are not
  aliased automatically and remain a documented coverage limitation.
- Regenerated output metadata: 3,603 base keys, 4,408 variants, 310
  multi-title base keys, 104 same-term collision base keys, and 376 collision
  course-term groups. Training cohort is 2,833 rows; 2024 holdout is 1,538.
- Holdout all-scope Logistic AP 0.6235, ROC-AUC 0.7751, Brier 0.1974,
  Recall@20% 0.4672, TN/FP/FN/TP 797/330/123/288; Random Forest AP 0.6100,
  ROC-AUC 0.7701, Brier 0.1903, Recall@20% 0.4769,
  TN/FP/FN/TP 849/278/138/273. Constant and persistence Recall@20% remain
  null with an explicit tied-probability reason.
- Replaced the fragile dashboard source-string test with a lean contract test
  for bilingual `cannot_answer`, a five-row scheduling data structure, and the
  W-proxy boundary. Trajectory plus Phase 6 tests pass (`15 passed`).

## 2026-09-14 — Six-year trajectory extension supervisor acceptance

- Codex resumed the interrupted review from the saved conversation excerpt,
  repository evidence, generated artifacts, and the two independent read-only
  sub-agent audits. The Luna implementation exception remained limited to this
  user-approved follow-up and this repository.
- Final course identity is conservative and auditable. Across 2019–2024, a
  six-year single-title `Subject + Number` uses the `base` variant; every
  multi-title base is split by normalized title in every year. Normalization
  changes only case, punctuation, and whitespace. The final metadata contains
  3,603 base keys, 4,408 variants, 310 multi-title bases, 291 bases with titles
  differing across years, 104 same-term collision bases, and 376 collision
  course-term groups.
- Supervisor reconciliation confirmed that raw-to-trajectory `Students` and
  `W` totals match for every year and term, lag1–3 values come only from the
  same course variant and same Spring/Fall in prior years, prediction keys have
  no duplicates, and the declared model matrix excludes current 2024 `W`,
  `Students`, grades, `W_proxy`, and `demand_proxy` outcome values.
- The added truth-isolation regression mutates 2024 outcome fields and confirms
  that model scores do not change. Constant and persistence baselines now give
  separate, accurate tied-score reasons for leaving Recall@20% unreported.
- A fresh real-data run completed successfully after explicit write approval.
  It produced 2,833 training rows, 1,538 eligible 2024 holdout rows out of
  3,152 observations (Spring 710/1,508; Fall 828/1,644), and 24 metric rows.
  The expected `handle_unknown="ignore"` warning occurred for holdout Subject
  categories not seen in training; they are encoded as all-zero one-hot values.
- Accepted combined 2024 results: Logistic AP 0.6235, ROC-AUC 0.7751, Brier
  0.1974, Recall@20% 0.4672, TN/FP/FN/TP 797/330/123/288; Random Forest AP
  0.6100, ROC-AUC 0.7701, Brier 0.1903, Recall@20% 0.4769,
  TN/FP/FN/TP 849/278/138/273. These are W-mark screening results, not official
  withdrawal probabilities, count forecasts, causal effects, or deployment
  guarantees.
- The bilingual dashboard now reads final trajectory coverage and metrics from
  regenerated files, labels the old three-year experiment only as a historical
  comparison when used, displays the 2020 Fall (14 W) and 2021 Spring (10 W)
  data-review warning, translates coefficient metadata, and invalidates cached
  data when an artifact modification timestamp changes. The Chinese and English
  AppTest smoke runs had zero exceptions and displayed the final 1,538/3,152
  coverage and RF AP 0.610.
- Both model guides and both READMEs now describe the independent extension and
  its reproduction command. The dashboard layout and navigation were preserved;
  no internal phase label was added to the user-facing interface.
- Final lean verification: the full offline suite passed (`39 passed`), the
  real trajectory CLI completed once, and post-run metrics/reconciliation
  checks passed. The generated report intentionally retains
  `generated_pending_supervisor_review` because generation precedes review;
  this history entry is the supervisor acceptance record.
- Accepted SHA-256 evidence: table
  `0B682E7148298756196F53F521788E75E6448418F7B3CF1B0DB1929BB849EA36`,
  predictions
  `227C252FBB8450CD406DD6C498F22DD8E9A2E5DAD10E42B7E293045C6B1CDEBE`,
  metrics
  `6B53AAA8928777590D424FFF2F8BF0C9AF6A27D4C6D1577D5F1F336F1CA7BD72`,
  coefficients
  `2CDBC54FF472590CBA9E01B1CAEA75BF63A5FCF0C6641E0D5693DAA8F398ACDF`,
  title audit
  `EC2F0CB2928263D974E7E73B45B40CF0C756D7529BE71161CDCADAE32559C2E2`,
  and report
  `750EA33916ADB6F34953AF82EE978CC4648BEB84350DE5F26D1CA5FB4B72510A`.

## 2026-09-15 — Business W interpretation and enrollment-data investigation

- The project owner clarified the intended business meaning: a W is the formal
  W grade left after the no-W drop deadline, often near the halfway point for a
  standard full-term undergraduate course. The documentation records this as
  an operational interpretation, not a universal week-8 rule; UIUC deadlines
  vary by part of term, course length, and student level.
- The source boundary remains explicit: the GPA file contains final W counts,
  grade-count fields, and Students excluding W, but no withdrawal event/date,
  registration event, numeric GPA, student id, or official easy-course label.
- Official-source review found public 10th-day census reports, DMI historical
  course/section enrollment tables, and daily roster/registration services
  described as authorized campus data. No public, reproducible paired snapshot
  for the same section in week one and after week-two/add-drop was found.
  A future `week1_enrollment - week2_enrollment` measure would be a rough net
  change, not a gross drop count, and would require CRN/section identity,
  snapshot dates, capacity, part-of-term and cancellation/merge fields.
- The proposed relationships between A/A+ share, easier or “water” courses,
  required-major courses, GPA, and W are recorded as hypotheses for a future
  descriptive analysis. They are not conclusions from the current six-year
  trajectory model.

## 2026-09-14 — Continuity diagnostics, reproducible EDA, and bilingual evidence display

- Added course-level continuity and seasonality diagnostics for the independent
  2019–2024 Spring/Fall trajectory: observed years/terms, period coverage,
  Spring/Fall pattern, same-term sequence length, training and 2024 backtest
  eligibility, and explicit exclusion reasons. Missing offerings remain
  unobserved rather than being filled with zero; partial single-season series
  are classified as intermittent, while complete single-season series retain a
  seasonal classification.
- Added reproducible EDA generation through
  `scripts/generate_course_trajectory_eda.py` and integrated report/table
  outputs covering source and filtered size, dtypes, missingness, duplicates,
  year-term coverage, Subject distribution, numeric summaries, source-to-
  trajectory reconciliation, and many-to-one join cardinality. The source
  duplicate-key explanation is documented as multiple instructor/grade-
  distribution records being aggregated, not duplicate students.
- Added prediction score error fields and explicit W/drop/GPA boundaries:
  `W` remains a grade-table W-mark count and `W_proxy` is not an official
  drop/withdrawal rate; current data has no numeric GPA or official pass/drop
  event fields. Added bilingual dashboard display for continuity, error,
  EDA evidence, and exploratory statistical-method guidance while preserving
  the existing five-tab visual structure.
- Supervisor verification: the full lean pytest suite passed (`42 passed`);
  the independent EDA rerun succeeded and its report/coverage matched the
  generated artifacts; the trajectory CLI temporary-output run succeeded for
  2019–2024 with 2,833 training rows, 1,538 eligible 2024 holdout rows, and 24
  metric rows; raw-to-trajectory reconciliation matched Students `1,962,535`
  and W `5,726`, with no duplicate prediction keys; Chinese and English
  AppTest smoke runs had zero exceptions and displayed five tabs.
- Remaining incomplete items are Excel export, real section scheduling data
  and conflict analysis, lawful course-review text, and numeric GPA/official
  pass/drop outcomes. No completion claim is made for those items.

## 2026-09-15 — User review correction: stable course identity, W semantics, and evidence

- Addressed the review that the previous `3,817 intermittent` count needed
  row-level evidence. The trajectory input now uses stable `Subject + Number`;
  Course Title is display-only and title changes are retained in the title
  audit. Recognisable Special/Selected Topics are set aside before continuity
  and modeling, with a separate `course_trajectory_special_topic_audit.csv`.
- Regenerated continuity evidence from the actual 2019–2024 Spring/Fall
  source slice. The included ordinary-course population is 3,600 keys:
  317 `continuous_both_terms` (8.81%), 174 `seasonal_fall` (4.83%), 128
  `seasonal_spring` (3.56%), and 2,981 `intermittent` (82.81%). The exact
  observed-period distribution is 1/2/3/4/5/6/7/8/9/10/11/12 cells for
  832/477/425/306/303/405/130/86/83/88/148/317 keys. The 2021–2023 focus
  window has observations in all three years for 1,393 keys. These values and
  each course's `observed_periods` are present in the continuity CSV and
  dashboard evidence tables.
- Replaced unconditional same-term matching with adaptive history: ordinary
  courses use either Spring/Fall from prior calendar years, while genuinely
  one-season courses use same-season history. The regenerated 2024 eligible
  coverage is 1,857/3,023 observations (Spring 896/1,452; Fall 961/1,571),
  with 3,574 training rows. Holdout all-scope Logistic AP/ROC-AUC/Brier/
  Recall@20% are 0.6110/0.7772/0.1836/0.4860; RF values are
  0.6177/0.7794/0.1796/0.4708. These remain W-mark screening metrics.
- Corrected user-facing definitions: W is the formal `Withdraw` mark count;
  W=0 means no W was observed in final-grade records and does not prove no
  earlier drop, student adaptation, or absence of a sudden difficulty change.
  `w_mark_share` is the derived `W/(Students+W)` share, not a W count or
  official withdrawal rate. `Students` is the final A+–F record count
  excluding W, not a unique-student or strict completion count.
- Added `grade_point_mean`, an explicitly labeled 4.0-style weighted estimate
  from A+–F counts for historical feedback. The source has no official numeric
  GPA. Added `course_trajectory_instructor_audit.csv` and exposed instructor
  context in trajectory predictions; names remain audit context because the
  source has no section id and a course-term can include multiple instructors.
- Supervisor validation: the final real-data trajectory CLI rerun succeeded;
  raw-to-analysis Students/W reconciliation is exact after the 34 excluded
  special-topic source rows; prediction keys have no duplicates; full offline
  tests pass (`43 passed`); Chinese and English Streamlit AppTest smoke runs
  report zero exceptions, five tabs, 17 dataframes. The generated report keeps
  `generated_pending_supervisor_review` as a generation status; this entry is
  the supervisor acceptance record for the correction.

## 2026-09-15 — Documentation correction: W marks, Students grain, and special-topic rows

- Updated only `docs/MODEL_AND_PROXY_GUIDE_ZH.md`,
  `docs/MODEL_AND_PROXY_GUIDE_EN.md`, `docs/data_dictionary.md`,
  `docs/PROJECT_OUTLINE.md`, and this history file. No source, dashboard,
  test, or processed-data files were changed.
- Standardised the user-facing meaning of `W` as the formal `Withdraw` mark
  count and `w_mark_share` as a derived share. The standard 16-week
  undergraduate roughly-week-8 interpretation is documented as business
  context only; the source has no withdrawal time or event field. `W=0` only
  means that W was not observed in aggregated final-grade records and does not
  establish earlier-drop absence or student adaptation.
- Documented `Students` as the course-completion A+–F final-grade record count,
  equal to the source A+–F band sum, not registrations, unique students, or
  section enrollment. Course-level aggregation may contain multiple instructor
  records.
- Re-stated the continuity focus as 2021–2023, with 2024 as bridge history and
  truth-only holdout; stable identity is `Subject + Number`; ordinary courses
  use either term from the prior calendar year, while genuinely one-season
  courses use same-season history.
- Verified the row-level special-topic decomposition: 34 raw
  special/selected-topic records touch 11 stable keys; 3 keys are special-only
  and do not enter the ordinary trajectory, while 8 overlapping keys retain
  their ordinary rows. The documentation does not treat the 11 keys as one
  excluded population.
- Targeted documentation/trajectory validation passed: `16 passed` for
  `tests/test_dashboard_contract.py` and `tests/test_course_trajectory.py`.

## 2026-09-15 — Final supervisor acceptance: course-trajectory evidence revision

- Final supervisor verification passed: the full offline suite completed with
  `pytest -q -p no:cacheprovider` reporting `49 passed`. The real
  `analyze_course_trajectory.py` and `generate_course_trajectory_eda.py`
  reruns both succeeded. Fifteen generated files were promoted into
  `data/processed`; the prior generated artifacts remain in
  `.tmp/trajectory-previous-20260915-1629`.
- Accepted trajectory evidence records 3,574 training rows, 1,857 2024
  holdout rows, and 24 metric rows. The ordinary stable-key population is
  3,600, with continuity counts `317/174/128/2,981`; observed periods 1..12
  are `832/477/425/306/303/405/130/86/83/88/148/317`; 1,393 keys have
  observations in each of 2021, 2022, and 2023. The Special Topics row-level
  decomposition is `34/11/3/8`; the title audit contains 3,600 rows and 309
  multi-title keys. Prediction-key duplicates are 0, and raw-to-analysis
  reconciliation is zero.
- Chinese and English Streamlit AppTest runs each started and switched without
  exceptions; each exposed 5 tabs and 17 dataframes, with no unreplaced
  placeholders.
- This acceptance covers the revised definitions, analysis scope, and
  evidence trail only. It does not claim that Excel export, schedule-conflict
  analysis, course-review text analysis, or official GPA is complete. Older
  history records are retained without rewriting.

## 2026-09-17 — Auditable Sol / DeepSeek / Luna workflow

- Added a repository-local development state machine with unique task IDs,
  explicit scope and acceptance criteria, one irrevocable DeepSeek attempt per
  task, Luna review/correction records, and Sol's criterion-by-criterion final
  decision. Rejected or failed work can continue only under a linked new task
  ID; the original record is retained as superseded.
- Added append-only hash-chained events, immutable stage artifacts, hashes for
  Luna-reviewed files, path allowlists, secret redaction, offline configuration
  checks, and a verification command. This tooling is isolated from the
  deterministic analytics and dashboard runtime.
- Recorded two pre-workflow DeepSeek calls as explicit bootstrap records. The
  first returned empty final content and consumed its attempt. The second
  returned a unified diff whose captured transport output was truncated; it is
  not represented as a complete state-machine audit trail.
- Added the CLI, Chinese operating guide, and offline tests. Supervisor
  validation passed: the workflow suite reports `12 passed`, the full offline
  project suite reports `61 passed`, and `doctor` reports `ok=true` with
  `network_request_made=false`. The real `.env` has the required key, base URL,
  model, and one-call policy without exposing the secret value.

## 2026-09-17 — Course Explorer workflow task rejected and superseded

- Task `CRP-20260917-050544-965827BD` consumed its single DeepSeek V4.1 Flash
  attempt. The configured API call failed with a connection error before any
  implementation response or code was produced; the audit record contains the
  redacted request metadata and failure evidence, not a fabricated result.
- GPT-5.6 Luna independently reviewed the failure and recorded `blocked` with
  no changed implementation files. GPT-5.6 Sol then evaluated all seven fixed
  acceptance criteria as failed because there was no implementation artifact
  to verify, recorded `rejected`, and did not retry DeepSeek under the same
  task ID.
- The rejected task was superseded by linked revision
  `CRP-20260917-052202-B816E890`. The revision retains the original objective,
  allowlist, and acceptance criteria while requiring an approved runtime with
  outbound HTTPS access before its one executor attempt is consumed. The new
  task remains `planned`; no Course Explorer implementation is claimed.
- Audit verification passed for both the superseded task and its planned
  revision.

## 2026-09-17 — Luna review: Course Explorer revision

- Integrated the DeepSeek Course Explorer extension additively: normalized
  models/schema/parser, cache-first acquisition records, quality evidence,
  timetable-overlap conflict edges, offline fixtures/tests, CLI helpers, and a
  verified-data Streamlit entry were added without replacing the established
  GPA/phase 5–6 pipeline or editing `dashboard/`.
- Preserved the original acquisition API and merged the new cache adapter into
  `src/course_retention/acquisition.py` so existing WAF/manifest behavior and
  tests remain intact.
- Added README and data-dictionary documentation for outputs, field grain,
  WAF/cache limitations, and the distinction between timetable overlap and
  observed student registration conflict.
- Full offline validation passed: `72 passed`. Cache-only acquisition and table
  build produced a blocked evidence row for `2023-fall/CS` without network use;
  conflict CLI produced an empty output because no verified source data exist.
- Existing user-facing `dashboard/` was intentionally unchanged per the task
  allowlist and dashboard change boundary. The new Streamlit entry preserves an
  explicit insufficient-data gate; no verified live Course Explorer dataset is
  claimed.

## 2026-09-17 — Course Explorer revision: reproducible offline evidence and AppTest

- Corrected `src/course_retention/app.py` so the documented file-executed
  Streamlit entry works with `python -m streamlit run src/course_retention/app.py`
  as well as package imports; an empty isolated root shows the explicit
  insufficient-data gate without scheduling results.
- Added `--output-root` to acquisition, table-build, and conflict CLI commands,
  and made the default cache-only run cover all nine 2021–2023 spring/summer/fall
  terms without overwriting existing generated outputs.
- Added focused CLI and Streamlit AppTest regression coverage. Live UIUC data
  remain unavailable and no `dashboard/` files were changed.
