#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    from course_retention.acquisition import CacheAdapter, acquisition_row
    from course_retention.config import TARGET_TERMS, default_paths
    from course_retention.pipeline import (
        build_parsed_from_cache,
        build_quality_rows,
        tables_from_parsed,
        write_csv,
        write_tables,
    )
    from course_retention.schema import ACQUISITION_FIELDS, QUALITY_FIELDS

    parser = argparse.ArgumentParser(description="Build normalized tables from cached UIUC XML.")
    parser.add_argument("--terms", nargs="*", default=list(TARGET_TERMS))
    parser.add_argument("--subjects", nargs="*", default=["CS"])
    parser.add_argument(
        "--output-root",
        default=None,
        help="Isolated root for cache and normalized evidence outputs; defaults to the repository root.",
    )
    parser.add_argument("--live", action="store_true", help="Permit outbound HTTPS for cache misses; default is cache-only.")
    args = parser.parse_args()

    paths = default_paths(Path(args.output_root) if args.output_root else root)
    cache = CacheAdapter(paths.cache)
    records, parsed_by = build_parsed_from_cache(args.terms, args.subjects, cache, allow_live=args.live)
    parsed_list = [parsed for plist in parsed_by.values() for parsed in plist]
    tables = tables_from_parsed(parsed_list)
    write_tables(tables, paths.tables)

    quality_rows = build_quality_rows(records, parsed_by)
    write_csv(paths.quality, QUALITY_FIELDS, quality_rows)
    write_csv(paths.processed / "acquisition_records.csv", ACQUISITION_FIELDS, [acquisition_row(record) for record in records])

    print(f"Wrote {len(parsed_list)} parsed courses and {len(quality_rows)} quality rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

