"""Acquisition actions for GPA CSV and Course Explorer XML roots.

Only two actions are supported:
  A) Download the single GPA CSV from SOURCES["gpa"]["url"].
  B) Probe exactly six Course Explorer root URLs for the approved window.

DMI and Enrollment Management are notes only and are never requested.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import DATA_RAW_DIR, PRIMARY_TERMS, SOURCES, validate_window

USER_AGENT = "course-retention-platform/0.1"
TIMEOUT = (10, 60)
ALLOWED_XML_HOST = "courses.illinois.edu"
GPA_FILENAME = "uiuc-gpa-dataset.csv"
MANIFEST_NAME = "acquisition_manifest.json"


class AcquisitionIncompleteError(RuntimeError):
    """Raised when probes fail and partial acquisition is not allowed."""

    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = Path(manifest_path)
        super().__init__(f"acquisition incomplete; see {self.manifest_path}")


@dataclass
class FetchResult:
    source: str
    path: str
    url: str
    status_code: Optional[int]
    sha256: Optional[str]
    bytes: Optional[int]
    retrieved_at_utc: str
    record_count: Optional[int]
    years: Tuple[int, ...] = ()
    terms: Tuple[str, ...] = ()
    notes: List[str] = field(default_factory=list)
    from_cache: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_inside(base: Path, *parts: str) -> Path:
    base = Path(base).resolve()
    candidate = base.joinpath(*parts).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"path escapes DATA_RAW_DIR: {candidate}")
    return candidate


def _headers(accept: str) -> Dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": accept}


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _get(session: requests.Session, url: str, accept: str) -> requests.Response:
    return session.get(url, headers=_headers(accept), timeout=TIMEOUT)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _looks_like_html(data: bytes, content_type: str) -> bool:
    if "html" in (content_type or "").lower():
        return True
    head = data[:512].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True).encode("utf-8"))


def _gpa_coverage(frame: pd.DataFrame) -> Tuple[Tuple[int, ...], Tuple[str, ...]]:
    years: Tuple[int, ...] = ()
    terms: Tuple[str, ...] = ()
    if "Year" in frame.columns:
        try:
            years = tuple(sorted({int(v) for v in frame["Year"].dropna().unique()}))
        except (TypeError, ValueError):
            years = ()
    if "Term" in frame.columns:
        terms = tuple(sorted({str(v).strip().lower() for v in frame["Term"].dropna().unique()}))
    return years, terms


def _download_gpa(session: requests.Session, force: bool) -> Tuple[FetchResult, List[str]]:
    url = SOURCES["gpa"]["url"]
    dest = _resolve_inside(DATA_RAW_DIR, "gpa", GPA_FILENAME)
    notes: List[str] = []
    if dest.exists() and not force:
        data = dest.read_bytes()
        frame = pd.read_csv(dest)
        years, terms = _gpa_coverage(frame)
        return FetchResult("gpa", str(dest), url, None, _sha256(data), len(data), _utc_now(), int(len(frame)), years, terms, ["cache hit"], True), notes
    response = _get(session, url, "text/csv,application/csv,*/*")
    if response.status_code >= 400:
        raise RuntimeError(f"GPA download HTTP {response.status_code} for {url}")
    data = response.content
    if not data:
        raise RuntimeError(f"GPA download empty body for {url}")
    content_type = response.headers.get("Content-Type", "")
    if _looks_like_html(data, content_type):
        raise RuntimeError(f"GPA download returned HTML for {url}")
    _atomic_write(dest, data)
    frame = pd.read_csv(dest)
    years, terms = _gpa_coverage(frame)
    return FetchResult("gpa", str(dest), url, response.status_code, _sha256(data), len(data), _utc_now(), int(len(frame)), years, terms, notes, False), notes


def _probe_xml(
    session: requests.Session, year: int, term: str, force: bool
) -> Tuple[Optional[FetchResult], Optional[Dict[str, Any]]]:
    base = SOURCES["course_explorer"]["url"].rstrip("/")
    url = f"{base}/schedule/{year}/{term}.xml"
    if requests.utils.urlparse(url).hostname != ALLOWED_XML_HOST:
        raise ValueError(f"disallowed XML host for {url}")
    dest = _resolve_inside(DATA_RAW_DIR, "course_explorer", str(year), term, "root.xml")
    if dest.exists() and not force:
        cached = dest.read_bytes()
        if cached:
            try:
                ElementTree.fromstring(cached)
            except ElementTree.ParseError:
                pass
            else:
                if not _looks_like_html(cached, ""):
                    return FetchResult("course_explorer", str(dest), url, None, _sha256(cached), len(cached), _utc_now(), None, (year,), (term,), ["cache hit"], True), None
    response = _get(session, url, "application/xml,text/xml,*/*")
    status = response.status_code
    action = response.headers.get("x-amzn-waf-action", "")
    content_type = response.headers.get("Content-Type", "")
    data = response.content
    failure: Dict[str, Any] = {"source": "course_explorer", "url": url, "year": year, "term": term, "status": status, "header_action": action, "content_type": content_type}
    if status == 202 or action == "challenge":
        failure["error"] = "WAF challenge or 202 accepted; no XML returned"
        return None, failure
    if status >= 400:
        failure["error"] = f"HTTP {status}"
        return None, failure
    if not data:
        failure["error"] = "empty body"
        return None, failure
    if _looks_like_html(data, content_type):
        failure["error"] = "HTML body instead of XML"
        return None, failure
    try:
        ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        failure["error"] = f"invalid XML: {exc}"
        return None, failure
    _atomic_write(dest, data)
    return FetchResult("course_explorer", str(dest), url, status, _sha256(data), len(data), _utc_now(), None, (year,), (term,), [], False), None


def acquire(years: Sequence[int] = (2021, 2022, 2023), terms: Sequence[str] = ("spring", "fall"), force: bool = False, allow_partial: bool = False) -> Dict[str, Any]:
    years_t = tuple(int(y) for y in years)
    terms_t = tuple(str(t).strip().lower() for t in terms)
    validate_window(years_t)
    if not terms_t:
        raise ValueError("terms must be nonempty")
    if len(set(terms_t)) != len(terms_t):
        raise ValueError("terms must not contain duplicates")
    for term in terms_t:
        if term not in PRIMARY_TERMS:
            raise ValueError(f"term {term!r} is not in PRIMARY_TERMS")
    session = _build_session()
    requested: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    source_notes = ["DMI is a note only and is never requested.", "Enrollment Management is a note only and is never requested."]
    gpa_url = SOURCES["gpa"]["url"]
    requested.append({"source": "gpa", "url": gpa_url})
    try:
        gpa_result, gpa_notes = _download_gpa(session, force)
    except Exception as exc:  # noqa: BLE001 - record and continue to XML probes
        failures.append({"source": "gpa", "url": gpa_url, "error": str(exc)})
    else:
        files.append(asdict(gpa_result))
        source_notes.extend(gpa_notes)
    for year in years_t:
        for term in terms_t:
            requested.append({"source": "course_explorer", "url": f"{SOURCES['course_explorer']['url'].rstrip('/')}/schedule/{year}/{term}.xml", "year": year, "term": term})
            result, failure = _probe_xml(session, year, term, force)
            if result is not None:
                files.append(asdict(result))
            if failure is not None:
                failures.append(failure)
    manifest = {"requested": requested, "files": files, "failures": failures, "source_notes": source_notes, "generated_at_utc": _utc_now()}
    manifest_path = _resolve_inside(DATA_RAW_DIR, MANIFEST_NAME)
    _atomic_write_json(manifest_path, manifest)
    if failures and not allow_partial:
        raise AcquisitionIncompleteError(manifest_path)
    return manifest
