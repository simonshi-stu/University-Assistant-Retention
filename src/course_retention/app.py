from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# `streamlit run src/course_retention/app.py` executes this file as a script,
# so package-relative imports are unavailable.  Keep module imports unchanged
# for normal package use while making the documented file entry executable.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from course_retention.config import default_paths
else:
    from .config import default_paths


def _read_csv(path):
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def verification_status(tables_dir, quality_path):
    quality = _read_csv(quality_path)
    if quality.empty:
        return False, "No quality report exists."
    if "verified" not in quality.columns:
        return False, "Quality report lacks verification flag."
    verified = quality[quality["verified"].astype(str).str.lower() == "true"]
    if verified.empty:
        return False, "No target term has verified acquisition and normalized data."
    conflicts = _read_csv(Path(tables_dir) / "conflict_edges.csv")
    if conflicts.empty:
        return False, "Verified data exist, but no reproducible conflict edges are present."
    return True, ""


def main():
    st.set_page_config(page_title="UIUC Course Retention", layout="wide")
    st.title("UIUC Course Retention Explorer")
    st.caption("Timetable overlap evidence for planning. Not observed student registration conflict.")

    paths = default_paths()
    verified, reason = verification_status(paths.tables, paths.quality)
    if not verified:
        st.warning(f"Insufficient verified data: {reason}")
        st.info(
            "No scheduling results are shown. Acquire official XML lawfully, build tables, "
            "and verify quality evidence first."
        )
        st.stop()

    st.success("Verified data found. Showing reproducible timetable-overlap edges only.")
    sections = _read_csv(paths.tables / "sections.csv")
    meetings = _read_csv(paths.tables / "meetings.csv")
    conflicts = _read_csv(paths.tables / "conflict_edges.csv")

    st.subheader("Conflict edges: timetable overlap, not observed registration conflict")
    st.dataframe(conflicts)
    st.subheader("Sections")
    st.dataframe(sections)
    st.subheader("Meetings")
    st.dataframe(meetings)


if __name__ == "__main__":
    main()

