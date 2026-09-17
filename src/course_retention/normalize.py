from __future__ import annotations

import re
from typing import Optional, Tuple


DAY_MAP = {
    "M": "MON",
    "T": "TUE",
    "W": "WED",
    "R": "THU",
    "F": "FRI",
    "S": "SAT",
    "U": "SUN",
}


def split_subject_number(text: str, default_subject: str = "", default_number: str = "") -> Tuple[str, str]:
    if text:
        match = re.match(r"^([A-Za-z]{2,6})\s*(\d+[A-Za-z]?)$", str(text).strip())
        if match:
            return match.group(1).upper(), match.group(2).upper()
    return default_subject.upper(), default_number.upper()


def parse_days(text: str) -> Tuple[str, ...]:
    if not text:
        return tuple()
    value = str(text).strip().upper().replace(".", "").replace(",", "").replace(" ", "")
    if not value or value in {"ARR", "ARRANGED", "TBA", "TBD"}:
        return tuple()
    value = value.replace("TH", "R")
    out = []
    for char in value:
        if char in DAY_MAP:
            out.append(DAY_MAP[char])
    return tuple(dict.fromkeys(out))


def parse_time(text: str) -> Optional[str]:
    if text is None:
        return None
    value = str(text).strip().upper()
    if not value or value in {"TBA", "TBD", "ARR", "ARRANGED"}:
        return None
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([AP]\.?M\.?)?$", value)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = (match.group(3) or "").replace(".", "")
    if ampm == "PM" and hour != 12:
        hour += 12
    if ampm == "AM" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def time_to_minutes(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.match(r"^(\d{2}):(\d{2})$", str(text).strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def parse_credit(text: str) -> Tuple[Optional[float], Optional[float], str]:
    if text is None:
        return None, None, ""
    value = str(text).strip()
    if not value:
        return None, None, ""
    numbers = re.findall(r"\d+(?:\.\d+)?", value)
    if not numbers:
        return None, None, value
    values = [float(number) for number in numbers]
    if len(values) == 1:
        return values[0], values[0], value
    return min(values), max(values), value


def normalize_date(text: str) -> str:
    if not text:
        return ""
    value = str(text).strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", value)
    if match:
        return f"{match.group(3)}-{int(match.group(1)):02d}-{int(match.group(2)):02d}"
    return value


