from pathlib import Path

from course_retention.parsers.uiuc_xml import parse_course_xml, parse_subject_xml


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_subject_xml_lists_courses():
    data = (FIXTURES / "subject_cs_2023_fall.xml").read_bytes()
    refs = parse_subject_xml(data)
    assert refs == [
        {
            "id": "CS 101",
            "href": "https://courses.illinois.edu/cisapp/explorer/schedule/2023/fall/CS/101.xml",
        }
    ]


def test_parse_course_xml_extracts_required_tables():
    data = (FIXTURES / "course_cs101_2023_fall.xml").read_bytes()
    parsed = parse_course_xml(data, "2023-fall")

    assert parsed.course.subject == "CS"
    assert parsed.course.number == "101"
    assert parsed.course.title.startswith("Intro Computing")
    assert parsed.course.credit_min == 3.0
    assert len(parsed.sections) == 5

    al1 = next(section for section in parsed.sections if section.crn == "10001")
    assert al1.section_number == "AL1"
    assert al1.part_of_term == "1"
    assert al1.start_date == "2023-08-21"
    assert al1.end_date == "2023-12-06"
    assert al1.credit_min == 3.0

    meeting = next(item for item in parsed.meetings if item.crn == "10001")
    assert meeting.weekdays == ("MON", "WED", "FRI")
    assert meeting.start_time == "10:00"
    assert meeting.end_time == "10:50"
    assert meeting.room == "1404"

    instructor = next(item for item in parsed.instructors if item.crn == "10001")
    assert instructor.name == "Ada Lovelace"
    assert instructor.email == "ada@example.edu"

    gened = next(item for item in parsed.gened if item.crn == "10001")
    assert gened.attribute_code == "QR"
    assert parsed.prerequisites[0].prerequisite_text.startswith("MATH 220")


