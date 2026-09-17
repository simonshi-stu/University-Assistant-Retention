from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from xml.etree import ElementTree as ET

from ..models import Course, GenEdAttribute, Instructor, Meeting, Prerequisite, Section
from ..normalize import normalize_date, parse_credit, parse_days, parse_time, split_subject_number


def _local(tag: str) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _first_child_text(elem, *names: str) -> str:
    for child in list(elem):
        if _local(child.tag) in names:
            return (child.text or "").strip()
    return ""


def _desc_text(elem, *names: str) -> str:
    for node in elem.iter():
        if _local(node.tag) in names:
            text = (node.text or "").strip()
            if text:
                return text
    return ""


@dataclass
class ParsedCourse:
    course: Course
    sections: List[Section]
    meetings: List[Meeting]
    instructors: List[Instructor]
    gened: List[GenEdAttribute]
    prerequisites: List[Prerequisite]
    source_rows: Dict[str, int]


def parse_subject_xml(xml_bytes: bytes) -> List[Dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    refs = []
    for node in root.iter():
        if _local(node.tag) == "course":
            course_id = node.attrib.get("id") or _desc_text(node, "name")
            href = node.attrib.get("href") or ""
            if course_id and href:
                refs.append({"id": course_id, "href": href})
    return refs


def parse_course_xml(xml_bytes: bytes, term: str) -> ParsedCourse:
    root = ET.fromstring(xml_bytes)
    if _local(root.tag) != "course":
        for child in list(root):
            if _local(child.tag) == "course":
                root = child
                break

    course_name = root.attrib.get("id") or _desc_text(root, "name") or ""
    subject, number = split_subject_number(course_name)
    if not subject:
        subject = _desc_text(root, "subject").upper()
    if not number:
        number = _desc_text(root, "number").upper()

    title = _first_child_text(root, "title", "courseTitle") or _desc_text(root, "title")
    description = _first_child_text(root, "description") or _desc_text(root, "description")
    credit_text = _first_child_text(root, "creditHours") or ""
    credit_min, credit_max, _ = parse_credit(credit_text)
    course = Course(
        term=term,
        subject=subject,
        number=number,
        title=title,
        description=description,
        credit_min=credit_min,
        credit_max=credit_max,
        credit_text=credit_text,
    )

    course_gened = []
    for node in list(root):
        if _local(node.tag) == "genEdAttributes":
            for sub in node.iter():
                if _local(sub.tag) == "genEdAttribute":
                    text = (sub.text or "").strip()
                    if text:
                        course_gened.append(text)
        elif _local(node.tag) == "genEdAttribute":
            text = (node.text or "").strip()
            if text:
                course_gened.append(text)
    course_gened = list(dict.fromkeys(course_gened))

    prereq_text = _first_child_text(root, "prerequisites", "prerequisite") or _desc_text(root, "prerequisites")
    prerequisites = []
    if prereq_text:
        prerequisites.append(
            Prerequisite(term=term, subject=subject, number=number, prerequisite_text=prereq_text)
        )

    sections = []
    meetings = []
    instructors = []
    gened = []

    section_nodes = [node for node in root.iter() if _local(node.tag) == "section"]
    for section_index, node in enumerate(section_nodes):
        crn = node.attrib.get("id") or _first_child_text(node, "crn", "callNumber")
        if not crn:
            crn = f"UNKNOWN-{section_index}"
        section_number = _first_child_text(node, "sectionNumber", "section")
        part_of_term = _first_child_text(node, "partOfTerm", "partOfTermCode")
        start_date = normalize_date(_first_child_text(node, "startDate"))
        end_date = normalize_date(_first_child_text(node, "endDate"))
        section_credit_text = _first_child_text(node, "creditHours") or credit_text
        section_credit_min, section_credit_max, _ = parse_credit(section_credit_text)
        sections.append(
            Section(
                term=term,
                subject=subject,
                number=number,
                crn=crn,
                section_number=section_number,
                part_of_term=part_of_term,
                start_date=start_date,
                end_date=end_date,
                credit_min=section_credit_min,
                credit_max=section_credit_max,
                credit_text=section_credit_text,
            )
        )

        seen_instructors = set()
        instructor_index = 0
        for instructor_node in node.iter():
            if _local(instructor_node.tag) != "instructor":
                continue
            name = _first_child_text(instructor_node, "name", "instructorName") or (instructor_node.text or "").strip()
            if not name or name in seen_instructors:
                continue
            seen_instructors.add(name)
            instructors.append(
                Instructor(
                    term=term,
                    subject=subject,
                    number=number,
                    crn=crn,
                    name=name,
                    email=_first_child_text(instructor_node, "email"),
                    role=_first_child_text(instructor_node, "role"),
                    instructor_index=instructor_index,
                )
            )
            instructor_index += 1

        meeting_nodes = [meeting for meeting in node.iter() if _local(meeting.tag) == "meeting"]
        for meeting_index, meeting_node in enumerate(meeting_nodes):
            meeting_type = _first_child_text(meeting_node, "type", "meetingType")
            days_raw = _first_child_text(meeting_node, "days", "day")
            start_raw = _first_child_text(meeting_node, "start", "startTime")
            end_raw = _first_child_text(meeting_node, "end", "endTime")
            building = _first_child_text(meeting_node, "building", "buildingName")
            room = _first_child_text(meeting_node, "room", "roomNumber")
            meeting_start = normalize_date(_first_child_text(meeting_node, "startDate")) or start_date
            meeting_end = normalize_date(_first_child_text(meeting_node, "endDate")) or end_date
            weekdays = parse_days(days_raw)
            start_time = parse_time(start_raw)
            end_time = parse_time(end_raw)
            raw_values = [days_raw, start_raw, end_raw]
            is_arranged = any((value or "").upper().startswith("ARR") for value in raw_values)
            is_tba = any((value or "").upper() in {"TBA", "TBD"} for value in raw_values + [building, room])
            if is_arranged:
                weekdays = tuple()
                start_time = None
                end_time = None
            meetings.append(
                Meeting(
                    term=term,
                    subject=subject,
                    number=number,
                    crn=crn,
                    meeting_index=meeting_index,
                    meeting_type=meeting_type,
                    days_raw=days_raw,
                    weekdays=weekdays,
                    start_time=start_time,
                    end_time=end_time,
                    building=building,
                    room=room,
                    start_date=meeting_start,
                    end_date=meeting_end,
                    is_arranged=is_arranged,
                    is_tba=is_tba,
                )
            )

        section_gened = []
        for gened_node in node.iter():
            if _local(gened_node.tag) == "genEdAttribute":
                text = (gened_node.text or "").strip()
                if text:
                    section_gened.append(text)
        if not section_gened:
            section_gened = course_gened
        for attribute in dict.fromkeys(section_gened):
            gened.append(
                GenEdAttribute(
                    term=term,
                    subject=subject,
                    number=number,
                    crn=crn,
                    attribute_code=attribute,
                    attribute_description=attribute,
                )
            )

    source_rows = {
        "sections": len(section_nodes),
        "meetings": len(meetings),
        "instructors": len(instructors),
        "gened": len(gened),
        "prerequisites": len(prerequisites),
    }
    return ParsedCourse(
        course=course,
        sections=sections,
        meetings=meetings,
        instructors=instructors,
        gened=gened,
        prerequisites=prerequisites,
        source_rows=source_rows,
    )


