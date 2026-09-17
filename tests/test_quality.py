from course_retention.models import Meeting, Section
from course_retention.quality import missing_critical_fields_for_section


def test_missing_critical_fields_are_reported():
    section = Section(
        term="2023-fall",
        subject="CS",
        number="101",
        crn="10001",
        section_number="AL1",
        part_of_term="",
        start_date="",
        end_date="",
        credit_min=None,
        credit_max=None,
        credit_text="",
    )
    meeting = Meeting(
        term="2023-fall",
        subject="CS",
        number="101",
        crn="10001",
        meeting_index=0,
        weekdays=(),
        start_time=None,
        end_time=None,
        room="",
        is_arranged=False,
        is_tba=False,
    )
    missing = missing_critical_fields_for_section(section, [meeting])
    assert "section.part_of_term" in missing
    assert "section.credit" in missing
    assert "meeting.0.weekdays" in missing
    assert "meeting.0.start_time" in missing


def test_arranged_meetings_do_not_require_time_fields():
    section = Section(
        term="2023-fall",
        subject="CS",
        number="101",
        crn="10001",
        section_number="AL1",
        part_of_term="1",
        start_date="2023-08-21",
        end_date="2023-12-06",
        credit_min=3.0,
        credit_max=3.0,
        credit_text="3",
    )
    meeting = Meeting(
        term="2023-fall",
        subject="CS",
        number="101",
        crn="10001",
        meeting_index=0,
        is_arranged=True,
    )
    assert missing_critical_fields_for_section(section, [meeting]) == []


