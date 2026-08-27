"""Heuristic mapping from common application-form fields to profile values.
Matches on a field's label text / placeholder / name / id / aria-label against
regex patterns - this covers the field naming conventions Greenhouse, Lever,
Ashby, and Workday tend to share, but no heuristic is perfect: always review
what got filled before submitting.
"""

import re


def build_text_field_values(profile: dict) -> list[tuple[re.Pattern, str]]:
    personal = profile.get("personal", {})
    full_name = personal.get("full_name", "")
    first_name, _, last_name = full_name.partition(" ")
    if " " in full_name and not last_name:
        parts = full_name.split(" ")
        first_name, last_name = parts[0], " ".join(parts[1:])

    return [
        (re.compile(r"first\s*name", re.I), first_name),
        (re.compile(r"last\s*name|surname", re.I), last_name),
        (re.compile(r"full\s*name|^name$", re.I), full_name),
        (re.compile(r"e-?mail", re.I), personal.get("email", "")),
        (re.compile(r"phone|mobile|telephone", re.I), personal.get("phone", "")),
        (re.compile(r"linked\s*in", re.I), personal.get("linkedin", "")),
        (re.compile(r"git\s*hub", re.I), personal.get("github", "")),
        (re.compile(r"portfolio|website|personal\s*site", re.I), personal.get("portfolio", "")),
        (re.compile(r"city|location|current\s*address", re.I), personal.get("location", "")),
    ]


# (label pattern, desired answer substring to click/select, field meaning - for logging only)
YES_NO_FIELD_PATTERNS = [
    (
        re.compile(r"legally\s+authorized\s+to\s+work|work\s+authorization", re.I),
        "work_authorization_positive",
    ),
    (
        re.compile(r"require.{0,20}sponsorship|need.{0,20}visa\s+sponsorship", re.I),
        "sponsorship_needed",
    ),
]
