COURSE_FIELDS = [
    "term",
    "subject",
    "number",
    "course_id",
    "title",
    "description",
    "credit_min",
    "credit_max",
    "credit_text",
]

SECTION_FIELDS = [
    "term",
    "subject",
    "number",
    "course_id",
    "crn",
    "section_id",
    "section_number",
    "part_of_term",
    "start_date",
    "end_date",
    "credit_min",
    "credit_max",
    "credit_text",
]

MEETING_FIELDS = [
    "term",
    "subject",
    "number",
    "crn",
    "section_id",
    "meeting_index",
    "meeting_type",
    "days_raw",
    "weekdays",
    "start_time",
    "end_time",
    "building",
    "room",
    "start_date",
    "end_date",
    "is_arranged",
    "is_tba",
]

INSTRUCTOR_FIELDS = [
    "term",
    "subject",
    "number",
    "crn",
    "section_id",
    "instructor_index",
    "name",
    "email",
    "role",
]

GENED_FIELDS = [
    "term",
    "subject",
    "number",
    "crn",
    "section_id",
    "attribute_code",
    "attribute_description",
]

PREREQUISITE_FIELDS = [
    "term",
    "subject",
    "number",
    "course_id",
    "prerequisite_text",
]

ACQUISITION_FIELDS = [
    "term",
    "subject",
    "resource",
    "url",
    "status",
    "http_status",
    "sha256",
    "bytes",
    "cache_path",
    "fetched_at",
    "error",
    "source_rows",
    "normalized_rows",
    "missing_critical_fields",
]

QUALITY_FIELDS = [
    "term",
    "subject",
    "acquisition_status",
    "http_status",
    "file_hashes",
    "source_rows",
    "normalized_rows",
    "missing_critical_fields",
    "verified",
]

CONFLICT_FIELDS = [
    "term",
    "section_id_a",
    "section_id_b",
    "crn_a",
    "crn_b",
    "subject_a",
    "number_a",
    "section_number_a",
    "subject_b",
    "number_b",
    "section_number_b",
    "day",
    "date_start",
    "date_end",
    "start_time_a",
    "end_time_a",
    "start_time_b",
    "end_time_b",
    "overlap_minutes",
    "meeting_type_a",
    "meeting_type_b",
]

TABLE_SCHEMAS = {
    "courses": COURSE_FIELDS,
    "sections": SECTION_FIELDS,
    "meetings": MEETING_FIELDS,
    "instructors": INSTRUCTOR_FIELDS,
    "gened": GENED_FIELDS,
    "prerequisites": PREREQUISITE_FIELDS,
}


