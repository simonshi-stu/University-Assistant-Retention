from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_file_executed_app_loads_and_gates_unverified_scheduling_data(monkeypatch, tmp_path):
    monkeypatch.setenv("COURSE_RETENTION_ROOT", str(tmp_path / "empty-output"))
    app = AppTest.from_file(str(ROOT / "src" / "course_retention" / "app.py"))
    app.run(timeout=30)

    assert not app.exception
    assert any("Insufficient verified data" in item.value for item in app.warning)
    assert not app.dataframe

