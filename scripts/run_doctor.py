#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from course_retention.config import DEEPSEEK_ENDPOINT

    checks = []
    checks.append(("python>=3.9", sys.version_info >= (3, 9)))
    try:
        import requests  # noqa: F401

        checks.append(("requests available", True))
    except Exception:
        checks.append(("requests available", False))
    checks.append(("DEEPSEEK_ENDPOINT is HTTPS", str(DEEPSEEK_ENDPOINT).startswith("https://")))
    allow_flag = os.environ.get("COURSE_RETENTION_ALLOW_OUTBOUND_HTTPS", "").lower() in {"1", "true", "yes"}
    checks.append(("outbound HTTPS policy flag", allow_flag))

    for name, ok in checks:
        print(f"{'OK' if ok else 'WARN'} {name}")

    if not all(ok for _, ok in checks):
        print("Doctor warnings present. Live acquisition may be blocked; cache/fixture processing remains available.")
        return 1
    print("Offline doctor OK. No network probe was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


