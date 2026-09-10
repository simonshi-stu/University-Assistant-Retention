"""Tests for course_retention.acquisition."""

from __future__ import annotations

import json

import pytest

from course_retention import acquisition
from course_retention import config


class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class FakeSession:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        if not self.responses:
            raise AssertionError(f"unexpected GET {url}")
        return self.responses.pop(0)


GPA_CSV = b"Year,Term\n2021,spring\n2021,fall\n2022,spring\n"
XML_BYTES = b"<?xml version='1.0'?><root><course/></root>"


def _gpa_response():
    return FakeResponse(200, GPA_CSV, {"Content-Type": "text/csv"})


def _xml_response():
    return FakeResponse(200, XML_BYTES, {"Content-Type": "application/xml"})


def _waf_response():
    return FakeResponse(202, b"", {"x-amzn-waf-action": "challenge"})


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    target = tmp_path / "raw"
    target.mkdir()
    monkeypatch.setattr(acquisition, "DATA_RAW_DIR", target)
    return target


def test_validate_window_direct():
    config.validate_window((2021, 2022, 2023))
    with pytest.raises(Exception):
        config.validate_window((1999,))


def test_acquire_invalid_term(raw_dir, monkeypatch):
    monkeypatch.setattr(acquisition, "_build_session", lambda: FakeSession())
    with pytest.raises(ValueError):
        acquisition.acquire(years=(2021,), terms=("winter",))


def test_acquire_duplicate_terms(raw_dir, monkeypatch):
    monkeypatch.setattr(acquisition, "_build_session", lambda: FakeSession())
    with pytest.raises(ValueError):
        acquisition.acquire(years=(2021,), terms=("spring", "spring"))


def test_gpa_row_coverage(raw_dir, monkeypatch):
    session = FakeSession([_gpa_response()] + [_waf_response() for _ in range(6)])
    monkeypatch.setattr(acquisition, "_build_session", lambda: session)
    manifest = acquisition.acquire(
        years=(2021, 2022, 2023), terms=("spring", "fall"), allow_partial=True
    )
    gpa_files = [f for f in manifest["files"] if f["source"] == "gpa"]
    assert len(gpa_files) == 1
    assert gpa_files[0]["record_count"] == 3
    assert gpa_files[0]["years"] == (2021, 2022)
    assert gpa_files[0]["terms"] == ("fall", "spring")


def test_waf_202_all_six_and_manifest(raw_dir, monkeypatch):
    session = FakeSession([_gpa_response()] + [_waf_response() for _ in range(6)])
    monkeypatch.setattr(acquisition, "_build_session", lambda: session)
    with pytest.raises(acquisition.AcquisitionIncompleteError):
        acquisition.acquire(years=(2021, 2022, 2023), terms=("spring", "fall"))
    manifest_path = raw_dir / acquisition.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text())
    xml_failures = [f for f in manifest["failures"] if f["source"] == "course_explorer"]
    assert len(xml_failures) == 6


def test_allow_partial_returns_manifest(raw_dir, monkeypatch):
    session = FakeSession([_gpa_response()] + [_waf_response() for _ in range(6)])
    monkeypatch.setattr(acquisition, "_build_session", lambda: session)
    manifest = acquisition.acquire((2021, 2022, 2023), ("spring", "fall"), allow_partial=True)
    assert manifest["failures"]


def test_valid_xml_cache(raw_dir, monkeypatch):
    dest = raw_dir / "course_explorer" / "2021" / "spring" / "root.xml"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(XML_BYTES)
    session = FakeSession([_gpa_response(), _xml_response(), _xml_response()])
    monkeypatch.setattr(acquisition, "_build_session", lambda: session)
    manifest = acquisition.acquire(
        years=(2021, 2022, 2023), terms=("spring",), allow_partial=True
    )
    xml_files = [f for f in manifest["files"] if f["source"] == "course_explorer"]
    assert len(xml_files) == 3
    cached = [f for f in xml_files if f["from_cache"] is True]
    assert len(cached) == 1
    assert cached[0]["years"] == (2021,)
    assert cached[0]["terms"] == ("spring",)


def test_containment(raw_dir):
    with pytest.raises(ValueError):
        acquisition._resolve_inside(raw_dir, "..", "escape.txt")


def test_retry_adapter():
    session = acquisition._build_session()
    adapter = session.get_adapter("https://courses.illinois.edu")
    assert adapter.max_retries.total == 3
