"""Central configuration for the course retention project.

This module defines the immutable configuration surface used across the
pipeline: module windows, primary terms, path constants, source registry,
and feature flags. It intentionally contains no I/O and no side effects
beyond module import.
"""

from pathlib import Path
import os
from typing import Final, Iterable


# Course Explorer extension constants.  These are additive to the established
# GPA pipeline configuration and are intentionally cache-first in callers.
COURSE_EXPLORER_BASE: Final[str] = "https://courses.illinois.edu/cisapp/explorer/schedule"
DEFAULT_USER_AGENT: Final[str] = "course-retention/0.1 (educational planning; local contact)"
DEEPSEEK_ENDPOINT: Final[str] = "https://api.deepseek.com"
TERM_CODES: Final = ("spring", "summer", "fall")
TARGET_TERMS: Final = tuple(
    f"{year}-{term}" for year in (2021, 2022, 2023) for term in TERM_CODES
)


class Paths:
    """Paths for the additive Course Explorer cache and normalized outputs."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.processed = self.root / "data" / "processed"
        self.cache = self.processed / "cache"
        self.tables = self.processed / "tables"
        self.quality = self.processed / "quality_report.csv"
        self.outputs = self.root / "outputs"


def default_paths(root: Path | None = None) -> Paths:
    configured_root = os.environ.get("COURSE_RETENTION_ROOT", "").strip()
    selected_root = Path(root) if root is not None else Path(configured_root or REPO_ROOT)
    return Paths(selected_root)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

DATA_RAW_DIR: Final[Path] = REPO_ROOT / "data" / "raw"
DATA_INTERIM_DIR: Final[Path] = REPO_ROOT / "data" / "interim"
DATA_PROCESSED_DIR: Final[Path] = REPO_ROOT / "data" / "processed"
OUTPUTS_DIR: Final[Path] = REPO_ROOT / "outputs"

MODULE_WINDOWS: Final = (
    (2021, 2022, 2023),
    (2022, 2023, 2024),
    (2023, 2024, 2025),
)

PRIMARY_TERMS: Final = ("spring", "fall")

MAX_ALLOWED_YEAR: Final = 2025

SOURCES: Final = {
    "gpa": {
        "url": "https://raw.githubusercontent.com/wadefagen/datasets/main/gpa/uiuc-gpa-dataset.csv",
        "docs_url": "https://github.com/wadefagen/datasets/blob/main/gpa/README.md",
        "access": "public",
        "granularity": "course-term-instructor grade distribution",
        "join_policy": (
            "GPA grain is course-term-instructor grade distribution and lacks "
            "section id; aggregate by validated course+term then many-to-one "
            "join to Course Explorer sections with recorded cardinality."
        ),
    },
    "course_explorer": {
        "url": "https://courses.illinois.edu/cisapp/explorer",
        "docs_url": "https://answers.uillinois.edu/uic/88215",
        "access": "public",
        "granularity": "course-section schedule",
        "join_policy": (
            "Course Explorer grain is course-section schedule; it is the "
            "many-to-one target for aggregated GPA course+term records."
        ),
    },
    "dmi": {
        "url": "https://dmi.illinois.edu/",
        "docs_url": "https://dmi.illinois.edu/",
        "access": "public",
        "granularity": "institutional aggregate",
        "join_policy": (
            "DMI data are institutional aggregates and context-only without "
            "compatible grain; no row-level join is performed."
        ),
    },
    "enrollment_management": {
        "url": "https://enrollmentmanagement.illinois.edu/reports-data/",
        "docs_url": "https://enrollmentmanagement.illinois.edu/reports-data/",
        "access": "public",
        "granularity": "institutional aggregate",
        "join_policy": (
            "Enrollment Management data are institutional aggregates and "
            "context-only without compatible grain; no row-level join is "
            "performed."
        ),
    },
}

REVIEWS_ICES_ENABLED: Final = False
ATTENDANCE_AVAILABLE: Final = False
RUNTIME_LLM_ENABLED: Final = False


def validate_window(window: Iterable) -> None:
    """Validate a module window."""
    if not isinstance(window, tuple):
        raise TypeError("window must be a tuple of three years")
    if len(window) != 3:
        raise ValueError("window must contain exactly three years")
    for year in window:
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError("window years must be integers")
    first, second, third = window
    if second != first + 1 or third != second + 1:
        raise ValueError("window years must be consecutive")
    if first < 2021 or third > MAX_ALLOWED_YEAR:
        raise ValueError("window years must lie within 2021..2025")


def window_train_holdout(window: Iterable):
    """Split a validated window into (train_years, holdout_year)."""
    validate_window(window)
    return (window[0], window[1]), window[2]
