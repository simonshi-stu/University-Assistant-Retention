from dataclasses import replace
from pathlib import Path

from course_retention.conflicts import compute_conflicts
from course_retention.parsers.uiuc_xml import parse_course_xml


FIXTURES = Path(__file__).parent / "fixtures"


def _parsed():
    return parse_course_xml((FIXTURES / "course_cs101_2023_fall.xml").read_bytes(), "2023-fall")


def test_overlap_edges_are_created_for_different_sections():
    parsed = _parsed()
    edges = compute_conflicts(parsed.sections, parsed.meetings)
    pairs = {(edge.section_id_a, edge.section_id_b) for edge in edges}
    assert ("2023-fall:CS 101:10001", "2023-fall:CS 101:10002") in pairs

    al1_al2 = [edge for edge in edges if edge.crn_a == "10001" and edge.crn_b == "10002"]
    assert {edge.day for edge in al1_al2} == {"MON", "WED", "FRI"}
    assert all(edge.overlap_minutes == 20 for edge in al1_al2)


def test_arranged_and_tba_meetings_create_no_conflicts():
    parsed = _parsed()
    edges = compute_conflicts(parsed.sections, parsed.meetings)
    assert not any("10003" in (edge.section_id_a, edge.section_id_b) for edge in edges)
    assert not any("10004" in (edge.section_id_a, edge.section_id_b) for edge in edges)


def test_non_overlapping_dates_create_no_conflicts():
    parsed = _parsed()
    edges = compute_conflicts(parsed.sections, parsed.meetings)
    assert not any("10005" in (edge.section_id_a, edge.section_id_b) for edge in edges)


def test_same_section_and_different_terms_are_excluded():
    parsed = _parsed()
    assert compute_conflicts(parsed.sections[:1], parsed.meetings[:1]) == []

    sections = list(parsed.sections)
    meetings = list(parsed.meetings)
    sections[1] = replace(sections[1], term="2022-fall")
    meetings = [
        replace(meeting, term="2022-fall") if meeting.crn == sections[1].crn else meeting
        for meeting in meetings
    ]
    edges = compute_conflicts(sections, meetings)
    assert not any(
        {edge.section_id_a, edge.section_id_b} == {sections[0].section_id, sections[1].section_id}
        for edge in edges
    )


