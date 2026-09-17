#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    from course_retention.acquisition import CacheAdapter, acquisition_row, ingest_subject
    from course_retention.config import TARGET_TERMS, default_paths
    from course_retention.pipeline import write_csv
    from course_retention.schema import ACQUISITION_FIELDS

    parser = argparse.ArgumentParser(description="Acquire UIUC Course Explorer XML into the local cache.")
    parser.add_argument("--terms", nargs="*", default=list(TARGET_TERMS))
    parser.add_argument("--subjects", nargs="*", default=["CS"])
    parser.add_argument(
        "--output-root",
        default=None,
        help="Isolated root for cache and evidence outputs; defaults to the repository root.",
    )
    parser.add_argument("--live", action="store_true", help="Permit outbound HTTPS; default is cache-only.")
    args = parser.parse_args()

    paths = default_paths(Path(args.output_root) if args.output_root else root)
    cache = CacheAdapter(paths.cache)
    records = []
    for term in args.terms:
        for subject in args.subjects:
            recs, _ = ingest_subject(term, subject, cache, allow_live=args.live)
            records.extend(recs)

    out_path = paths.processed / "acquisition_records.csv"
    write_csv(out_path, ACQUISITION_FIELDS, [acquisition_row(record) for record in records])
    print(f"Wrote {len(records)} acquisition records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

