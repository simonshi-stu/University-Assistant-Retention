# Operations

## Offline doctor

Run before any live acquisition attempt:

```powershell
.\.venv\Scripts\python.exe scripts\run_doctor.py
```

This check does not probe DeepSeek or UIUC. Live acquisition is opt-in and
cache misses remain blocked unless `--live` is supplied.

## Reproducible cache-only evidence

The default target is the nine primary-window terms: spring, summer, and fall
for 2021, 2022, and 2023. Use `--output-root` to isolate a run from existing
generated files:

```powershell
$out = Join-Path $env:TEMP "course-retention-evidence"
.\.venv\Scripts\python.exe scripts\run_acquisition.py --output-root $out
.\.venv\Scripts\python.exe scripts\build_tables.py --output-root $out
.\.venv\Scripts\python.exe scripts\run_conflicts.py --output-root $out
```

The run writes acquisition and quality evidence under
`$out\data\processed\`, normalized tables under `$out\data\processed\tables\`,
and conflict edges under `$out\outputs\`. A cache-only miss is recorded as
`blocked` with empty HTTP/hash fields rather than silently treated as zero data.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The parser and acquisition tests use official-structure fixtures and do not
require live network access. The Streamlit AppTest uses an empty isolated root
and must show an explicit insufficient-data warning.

## Live acquisition

Only when outbound HTTPS is authorized, add `--live`:

```powershell
$out = Join-Path $env:TEMP "course-retention-evidence-live"
$env:COURSE_RETENTION_ALLOW_OUTBOUND_HTTPS = "true"
.\.venv\Scripts\python.exe scripts\run_acquisition.py --output-root $out --live --terms 2023-fall --subjects CS
```

No WAF bypass, scraping circumvention, or fabricated missing data is allowed.
HTTP 401, 403, 429, and challenge responses are retained as blocked evidence.

## Streamlit

```powershell
.\.venv\Scripts\python.exe -m streamlit run src\course_retention\app.py
```

The file-executed entry works without package-relative import errors. It shows
scheduling results only when quality evidence is verified and conflict edges
exist; otherwise it displays an explicit insufficient-data explanation.
