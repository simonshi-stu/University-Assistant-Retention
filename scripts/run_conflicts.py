#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))

    from course_retention.config import default_paths
    from course_retention.conflicts import compute_conflicts, read_meetings_csv, read_sections_csv, write_conflicts_csv

    parser = argparse.ArgumentParser(description="Compute reproducible timetable-overlap edges.")
    parser.add_argument("--tables-dir", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--output-root",
        default=None,
        help="Isolated root containing data/processed and outputs; defaults to the repository root.",
    )
    args = parser.parse_args()

    paths = default_paths(Path(args.output_root) if args.output_root else root)
    tables_dir = Path(args.tables_dir) if args.tables_dir else paths.tables
    out_path = Path(args.out) if args.out else paths.outputs / "conflict_edges.csv"

    sections_path = tables_dir / "sections.csv"
    meetings_path = tables_dir / "meetings.csv"
    if not sections_path.exists() or not meetings_path.exists():
        write_conflicts_csv([], out_path)
        write_conflicts_csv([], tables_dir / "conflict_edges.csv")
        print("No sections/meetings tables found; wrote empty conflict edges.")
        return 0

    sections = read_sections_csv(sections_path)
    meetings = read_meetings_csv(meetings_path)
    edges = compute_conflicts(sections, meetings)
    write_conflicts_csv(edges, out_path)
    write_conflicts_csv(edges, tables_dir / "conflict_edges.csv")
    print(f"Wrote {len(edges)} conflict edges to {out_path} and {tables_dir / 'conflict_edges.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

