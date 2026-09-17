from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(script: str, output_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--output-root", str(output_root)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_default_nine_term_cache_only_run_is_isolated_and_reproducible(tmp_path):
    output_root = tmp_path / "course-retention-output"

    acquisition = _run("run_acquisition.py", output_root)
    assert "Wrote 9 acquisition records" in acquisition.stdout

    build = _run("build_tables.py", output_root)
    assert "9 quality rows" in build.stdout

    conflicts = _run("run_conflicts.py", output_root)
    assert "0 conflict edges" in conflicts.stdout

    acquisition_path = output_root / "data" / "processed" / "acquisition_records.csv"
    quality_path = output_root / "data" / "processed" / "quality_report.csv"
    with acquisition_path.open(newline="", encoding="utf-8") as handle:
        acquisition_rows = list(csv.DictReader(handle))
    with quality_path.open(newline="", encoding="utf-8") as handle:
        quality_rows = list(csv.DictReader(handle))

    expected_terms = {f"{year}-{term}" for year in (2021, 2022, 2023) for term in ("spring", "summer", "fall")}
    assert {row["term"] for row in acquisition_rows} == expected_terms
    assert {row["term"] for row in quality_rows} == expected_terms
    assert all(row["status"] == "blocked" for row in acquisition_rows)
    assert all(row["acquisition_status"] == "blocked" and row["verified"] == "false" for row in quality_rows)
    assert (output_root / "outputs" / "conflict_edges.csv").exists()

