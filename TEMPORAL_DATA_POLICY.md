# Temporal Data Policy

## Purpose

This repository is being developed in 2026. Its historical analysis clock is set to 2024-01-01, and its preferred data accumulation window is the three complete years immediately before that date. The analysis clock, source-data years, and actual development date must remain separate metadata.

## Cutoffs

| Mode | Included years | Training years | Holdout year | Use |
|---|---|---|---|---|
| `primary` | 2021, 2022, 2023 | 2021–2022 | 2023 | Default for every module |
| `fallback` | 2022, 2023, 2024 | 2022–2023 | 2024 | Module-level fallback only |
| `last_resort` | 2023, 2024, 2025 | 2023–2024 | 2025 | Use only if fallback is still insufficient |

No 2026+ source data is allowed. A module that passes the primary sufficiency checks must remain on the primary window.

## Sufficiency checks

Window selection is evaluated separately for W proxy analysis, supervised modeling, schedule conflicts, and sentiment analysis. The minimum thresholds are defined in `PROJECT_SCOPE.md`. Every fallback decision must record source coverage, row counts after cleaning, missing critical fields, and the selected window in `HISTORY.md`.

## Required implementation behavior

1. Download or snapshot the source data without editing the raw files.
2. Record source URL, retrieval date, license, original year coverage, selected window, and fallback reason if any.
3. Apply the selected year set before joins, aggregations, feature engineering, model training, and exports.
4. Train only on the first two selected years and evaluate on the third year.
5. Keep `source_period`, `selected_data_years`, `analysis_reference_date`, and `project_development_period` as separate metadata fields.
6. Include one required validation that fails when a row outside the active year set reaches a cleaned, modeled, or dashboard dataset.
7. Do not mix modules using different windows without labeling each module's years in tables, charts, and written conclusions.

## Interpretation rules

- A dataset existing in 2021–2023 does not prove that the user analyzed it during ATLAS.
- A project developed in 2026 is an independent extension unless contemporaneous ATLAS evidence proves otherwise.
- UIUC `W` remains a withdrawal proxy, not a complete registration-event drop rate.
- OULAD is outside the requested 2021–2025 windows and is excluded from the main analysis and dashboard.
