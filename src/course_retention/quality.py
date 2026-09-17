from __future__ import annotations

from typing import Iterable, List

from .models import Meeting, Section


def missing_critical_fields_for_section(section: Section, meetings: Iterable[Meeting]) -> List[str]:
    missing = []
    for field_name in (
        "term",
        "subject",
        "number",
        "crn",
        "section_number",
        "part_of_term",
        "start_date",
        "end_date",
    ):
        if not getattr(section, field_name, ""):
            missing.append(f"section.{field_name}")
    if section.credit_min is None and section.credit_max is None:
        missing.append("section.credit")
    for meeting in meetings:
        if meeting.is_arranged or meeting.is_tba:
            continue
        prefix = f"meeting.{meeting.meeting_index}"
        if not meeting.weekdays:
            missing.append(f"{prefix}.weekdays")
        if not meeting.start_time:
            missing.append(f"{prefix}.start_time")
        if not meeting.end_time:
            missing.append(f"{prefix}.end_time")
        if not meeting.room:
            missing.append(f"{prefix}.room")
    return missing


