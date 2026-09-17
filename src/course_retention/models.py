from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class Course:
    term: str
    subject: str
    number: str
    title: str = ""
    description: str = ""
    credit_min: Optional[float] = None
    credit_max: Optional[float] = None
    credit_text: str = ""

    @property
    def course_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}"


@dataclass(frozen=True)
class Section:
    term: str
    subject: str
    number: str
    crn: str
    section_number: str = ""
    part_of_term: str = ""
    start_date: str = ""
    end_date: str = ""
    credit_min: Optional[float] = None
    credit_max: Optional[float] = None
    credit_text: str = ""

    @property
    def course_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}"

    @property
    def section_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}:{self.crn}"


@dataclass(frozen=True)
class Meeting:
    term: str
    subject: str
    number: str
    crn: str
    meeting_index: int
    meeting_type: str = ""
    days_raw: str = ""
    weekdays: Tuple[str, ...] = field(default_factory=tuple)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    building: str = ""
    room: str = ""
    start_date: str = ""
    end_date: str = ""
    is_arranged: bool = False
    is_tba: bool = False

    @property
    def section_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}:{self.crn}"


@dataclass(frozen=True)
class Instructor:
    term: str
    subject: str
    number: str
    crn: str
    name: str
    email: str = ""
    role: str = ""
    instructor_index: int = 0

    @property
    def section_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}:{self.crn}"


@dataclass(frozen=True)
class GenEdAttribute:
    term: str
    subject: str
    number: str
    crn: str
    attribute_code: str
    attribute_description: str = ""

    @property
    def section_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}:{self.crn}"


@dataclass(frozen=True)
class Prerequisite:
    term: str
    subject: str
    number: str
    prerequisite_text: str

    @property
    def course_id(self) -> str:
        return f"{self.term}:{self.subject} {self.number}"


@dataclass(frozen=True)
class ConflictEdge:
    term: str
    section_id_a: str
    section_id_b: str
    crn_a: str
    crn_b: str
    subject_a: str
    number_a: str
    section_number_a: str
    subject_b: str
    number_b: str
    section_number_b: str
    day: str
    date_start: str
    date_end: str
    start_time_a: str
    end_time_a: str
    start_time_b: str
    end_time_b: str
    overlap_minutes: int
    meeting_type_a: str = ""
    meeting_type_b: str = ""


