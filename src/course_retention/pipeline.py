from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .acquisition import CacheAdapter, ingest_subject
from .models import Course, GenEdAttribute, Instructor, Meeting, Prerequisite, Section
from .quality import missing_critical_fields_for_section
from .schema import ACQUISITION_FIELDS, QUALITY_FIELDS, TABLE_SCHEMAS


def _fmt(value):
    if value is None:
        return ""
    return value


def bool_str(value: bool) -> str:
    return "true" if value else "false"


def course_to_row(course: Course) -> Dict[str, object]:
    return {
        "term": course.term,
        "subject": course.subject,
        "number": course.number,
        "course_id": course.course_id,
        "title": course.title,
        "description": course.description,
        "credit_min": _fmt(course.credit_min),
        "credit_max": _fmt(course.credit_max),
        "credit_text": course.credit_text,
    }


def section_to_row(section: Section) -> Dict[str, object]:
    return {
        "term": section.term,
        "subject": section.subject,
        "number": section.number,
        "course_id": section.course_id,
        "crn": section.crn,
        "section_id": section.section_id,
        "section_number": section.section_number,
        "part_of_term": section.part_of_term,
        "start_date": section.start_date,
        "end_date": section.end_date,
        "credit_min": _fmt(section.credit_min),
        "credit_max": _fmt(section.credit_max),
        "credit_text": section.credit_text,
    }


def meeting_to_row(meeting: Meeting) -> Dict[str, object]:
    return {
        "term": meeting.term,
        "subject": meeting.subject,
        "number": meeting.number,
        "crn": meeting.crn,
        "section_id": meeting.section_id,
        "meeting_index": meeting.meeting_index,
        "meeting_type": meeting.meeting_type,
        "days_raw": meeting.days_raw,
        "weekdays": "|".join(meeting.weekdays),
        "start_time": meeting.start_time or "",
        "end_time": meeting.end_time or "",
        "building": meeting.building,
        "room": meeting.room,
        "start_date": meeting.start_date,
        "end_date": meeting.end_date,
        "is_arranged": bool_str(meeting.is_arranged),
        "is_tba": bool_str(meeting.is_tba),
    }


def instructor_to_row(instructor: Instructor) -> Dict[str, object]:
    return {
        "term": instructor.term,
        "subject": instructor.subject,
        "number": instructor.number,
        "crn": instructor.crn,
        "section_id": instructor.section_id,
        "instructor_index": instructor.instructor_index,
        "name": instructor.name,
        "email": instructor.email,
        "role": instructor.role,
    }


def gened_to_row(attribute: GenEdAttribute) -> Dict[str, object]:
    return {
        "term": attribute.term,
        "subject": attribute.subject,
        "number": attribute.number,
        "crn": attribute.crn,
        "section_id": attribute.section_id,
        "attribute_code": attribute.attribute_code,
        "attribute_description": attribute.attribute_description,
    }


def prereq_to_row(prerequisite: Prerequisite) -> Dict[str, object]:
    return {
        "term": prerequisite.term,
        "subject": prerequisite.subject,
        "number": prerequisite.number,
        "course_id": prerequisite.course_id,
        "prerequisite_text": prerequisite.prerequisite_text,
    }


def tables_from_parsed(parsed_courses: Iterable) -> Dict[str, List[dict]]:
    course_rows = {}
    section_rows = {}
    meeting_rows = {}
    instructor_rows = {}
    gened_rows = {}
    prereq_rows = {}

    for parsed in parsed_courses:
        course_rows[parsed.course.course_id] = course_to_row(parsed.course)
        for section in parsed.sections:
            section_rows[section.section_id] = section_to_row(section)
        for meeting in parsed.meetings:
            meeting_rows[(meeting.section_id, meeting.meeting_index)] = meeting_to_row(meeting)
        for instructor in parsed.instructors:
            instructor_rows[(instructor.section_id, instructor.instructor_index, instructor.name)] = instructor_to_row(instructor)
        for attribute in parsed.gened:
            gened_rows[(attribute.section_id, attribute.attribute_code, attribute.attribute_description)] = gened_to_row(attribute)
        for prerequisite in parsed.prerequisites:
            prereq_rows[prerequisite.course_id] = prereq_to_row(prerequisite)

    return {
        "courses": list(course_rows.values()),
        "sections": list(section_rows.values()),
        "meetings": list(meeting_rows.values()),
        "instructors": list(instructor_rows.values()),
        "gened": list(gened_rows.values()),
        "prerequisites": list(prereq_rows.values()),
    }


def write_csv(path, fields, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_tables(tables: Dict[str, List[dict]], tables_dir) -> None:
    tables_dir = Path(tables_dir)
    tables_dir.mkdir(parents=True, exist_ok=True)
    for name, fields in TABLE_SCHEMAS.items():
        write_csv(tables_dir / f"{name}.csv", fields, tables.get(name, []))


def build_parsed_from_cache(terms, subjects, cache: CacheAdapter, *, allow_live: bool = False):
    records = []
    parsed_by = {}
    for term in terms:
        for subject in subjects:
            recs, parsed = ingest_subject(term, subject, cache, allow_live=allow_live)
            records.extend(recs)
            parsed_by[(term, subject)] = parsed
    return records, parsed_by


def build_quality_rows(records, parsed_by):
    records_by_key = defaultdict(list)
    for record in records:
        records_by_key[(record.term, record.subject)].append(record)

    keys = sorted(set(records_by_key.keys()) | set(parsed_by.keys()))
    rows = []
    for term, subject in keys:
        recs = records_by_key.get((term, subject), [])
        parsed = parsed_by.get((term, subject), [])

        source_sections = sum(len(item.sections) for item in parsed)
        source_meetings = sum(len(item.meetings) for item in parsed)
        source_instructors = sum(len(item.instructors) for item in parsed)
        source_gened = sum(len(item.gened) for item in parsed)
        source_prereqs = sum(len(item.prerequisites) for item in parsed)
        source_rows = source_sections + source_meetings + source_instructors + source_gened + source_prereqs
        normalized_rows = source_rows

        missing = []
        for item in parsed:
            for section in item.sections:
                section_meetings = [m for m in item.meetings if m.section_id == section.section_id]
                missing.extend(missing_critical_fields_for_section(section, section_meetings))
        missing = sorted(set(missing))

        statuses = {record.status for record in recs}
        if "ok" in statuses:
            acquisition_status = "ok"
        elif "cache" in statuses:
            acquisition_status = "cache"
        elif "blocked" in statuses:
            acquisition_status = "blocked"
        elif "http_error" in statuses:
            acquisition_status = "http_error"
        elif "network_error" in statuses:
            acquisition_status = "network_error"
        else:
            acquisition_status = "missing"

        http_status = ";".join(sorted({record.http_status for record in recs if record.http_status}))
        file_hashes = ";".join(sorted({record.sha256 for record in recs if record.sha256}))
        verified = acquisition_status in {"ok", "cache"} and normalized_rows > 0 and not missing

        rows.append(
            {
                "term": term,
                "subject": subject,
                "acquisition_status": acquisition_status,
                "http_status": http_status,
                "file_hashes": file_hashes,
                "source_rows": source_rows,
                "normalized_rows": normalized_rows,
                "missing_critical_fields": ";".join(missing),
                "verified": bool_str(verified),
            }
        )
    return rows


