from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Optional

from .models import ConflictEdge, Meeting, Section
from .normalize import time_to_minutes
from .schema import CONFLICT_FIELDS


def _float_or_none(value) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def read_sections_csv(path: Path) -> List[Section]:
    sections = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sections.append(
                Section(
                    term=row.get("term", ""),
                    subject=row.get("subject", ""),
                    number=row.get("number", ""),
                    crn=row.get("crn", ""),
                    section_number=row.get("section_number", ""),
                    part_of_term=row.get("part_of_term", ""),
                    start_date=row.get("start_date", ""),
                    end_date=row.get("end_date", ""),
                    credit_min=_float_or_none(row.get("credit_min")),
                    credit_max=_float_or_none(row.get("credit_max")),
                    credit_text=row.get("credit_text", ""),
                )
            )
    return sections


def read_meetings_csv(path: Path) -> List[Meeting]:
    meetings = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            weekdays = tuple(filter(None, (row.get("weekdays") or "").split("|")))
            meetings.append(
                Meeting(
                    term=row.get("term", ""),
                    subject=row.get("subject", ""),
                    number=row.get("number", ""),
                    crn=row.get("crn", ""),
                    meeting_index=int(row.get("meeting_index") or 0),
                    meeting_type=row.get("meeting_type", ""),
                    days_raw=row.get("days_raw", ""),
                    weekdays=weekdays,
                    start_time=row.get("start_time") or None,
                    end_time=row.get("end_time") or None,
                    building=row.get("building", ""),
                    room=row.get("room", ""),
                    start_date=row.get("start_date", ""),
                    end_date=row.get("end_date", ""),
                    is_arranged=_bool(row.get("is_arranged", "")),
                    is_tba=_bool(row.get("is_tba", "")),
                )
            )
    return meetings


def compute_conflicts(sections: Iterable[Section], meetings: Iterable[Meeting]) -> List[ConflictEdge]:
    section_by_id = {section.section_id: section for section in sections}
    meetings_by_section = defaultdict(list)
    for meeting in meetings:
        meetings_by_section[meeting.section_id].append(meeting)

    section_list = sorted(section_by_id.values(), key=lambda section: section.section_id)
    edges = []
    seen = set()

    for i in range(len(section_list)):
        for j in range(i + 1, len(section_list)):
            section_a = section_list[i]
            section_b = section_list[j]
            if section_a.term != section_b.term:
                continue
            if section_a.section_id == section_b.section_id:
                continue

            for meeting_a in meetings_by_section.get(section_a.section_id, []):
                if meeting_a.is_arranged or meeting_a.is_tba:
                    continue
                for meeting_b in meetings_by_section.get(section_b.section_id, []):
                    if meeting_b.is_arranged or meeting_b.is_tba:
                        continue

                    common_days = set(meeting_a.weekdays) & set(meeting_b.weekdays)
                    if not common_days:
                        continue

                    date_start_a = meeting_a.start_date or section_a.start_date
                    date_end_a = meeting_a.end_date or section_a.end_date
                    date_start_b = meeting_b.start_date or section_b.start_date
                    date_end_b = meeting_b.end_date or section_b.end_date
                    if not (date_start_a and date_end_a and date_start_b and date_end_b):
                        continue

                    overlap_start = max(date_start_a, date_start_b)
                    overlap_end = min(date_end_a, date_end_b)
                    if overlap_start > overlap_end:
                        continue

                    if not (
                        meeting_a.start_time
                        and meeting_a.end_time
                        and meeting_b.start_time
                        and meeting_b.end_time
                    ):
                        continue

                    start_a = time_to_minutes(meeting_a.start_time)
                    end_a = time_to_minutes(meeting_a.end_time)
                    start_b = time_to_minutes(meeting_b.start_time)
                    end_b = time_to_minutes(meeting_b.end_time)
                    if None in (start_a, end_a, start_b, end_b):
                        continue

                    overlap_minutes = min(end_a, end_b) - max(start_a, start_b)
                    if overlap_minutes <= 0:
                        continue

                    for day in sorted(common_days):
                        key = (
                            section_a.section_id,
                            section_b.section_id,
                            day,
                            meeting_a.start_time,
                            meeting_a.end_time,
                            meeting_b.start_time,
                            meeting_b.end_time,
                            overlap_start,
                            overlap_end,
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        edges.append(
                            ConflictEdge(
                                term=section_a.term,
                                section_id_a=section_a.section_id,
                                section_id_b=section_b.section_id,
                                crn_a=section_a.crn,
                                crn_b=section_b.crn,
                                subject_a=section_a.subject,
                                number_a=section_a.number,
                                section_number_a=section_a.section_number,
                                subject_b=section_b.subject,
                                number_b=section_b.number,
                                section_number_b=section_b.section_number,
                                day=day,
                                date_start=overlap_start,
                                date_end=overlap_end,
                                start_time_a=meeting_a.start_time,
                                end_time_a=meeting_a.end_time,
                                start_time_b=meeting_b.start_time,
                                end_time_b=meeting_b.end_time,
                                overlap_minutes=overlap_minutes,
                                meeting_type_a=meeting_a.meeting_type,
                                meeting_type_b=meeting_b.meeting_type,
                            )
                        )
    return edges


def write_conflicts_csv(edges: Iterable[ConflictEdge], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONFLICT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for edge in edges:
            writer.writerow({field: getattr(edge, field, "") for field in CONFLICT_FIELDS})


