"""Course retention analytics package."""

from .config import (
    ATTENDANCE_AVAILABLE,
    DATA_INTERIM_DIR,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    MAX_ALLOWED_YEAR,
    MODULE_WINDOWS,
    OUTPUTS_DIR,
    PRIMARY_TERMS,
    REPO_ROOT,
    REVIEWS_ICES_ENABLED,
    RUNTIME_LLM_ENABLED,
    SOURCES,
    validate_window,
    window_train_holdout,
)

__version__ = "0.1.0"

__all__ = [
    "REPO_ROOT",
    "DATA_RAW_DIR",
    "DATA_INTERIM_DIR",
    "DATA_PROCESSED_DIR",
    "OUTPUTS_DIR",
    "MODULE_WINDOWS",
    "PRIMARY_TERMS",
    "MAX_ALLOWED_YEAR",
    "validate_window",
    "window_train_holdout",
    "SOURCES",
    "REVIEWS_ICES_ENABLED",
    "ATTENDANCE_AVAILABLE",
    "RUNTIME_LLM_ENABLED",
    "__version__",
]
