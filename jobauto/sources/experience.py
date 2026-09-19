"""Best-effort extraction of a job posting's stated years-of-experience requirement,
so listings can be filtered to an early-career-friendly range. Job descriptions don't
have a structured field for this - it's free text - so this is a text heuristic, not
a guarantee: it can miss postings that phrase things unusually, and it can occasionally
be thrown off by an unrelated number (e.g. "our team has 40 years of combined experience").
"""

import re

# Explicit positive signals that override everything else - a posting that says any of
# these is early-career-friendly regardless of what other numbers appear in the text.
_JUNIOR_SIGNAL_RE = re.compile(
    r"\bnew\s*grad(?:uate)?s?\b|\bearly[\s-]career\b|\bentry[\s-]level\b|\bjunior\b|"
    r"\bassociate\s+(?:software\s+)?engineer\b|\bsoftware\s+engineer\s+i\b|\bswe\s*i\b(?!i)|"
    r"\b0\s*-\s*\d\s*yoe\b",
    re.I,
)

# Titles that reliably mean "years of experience will be well above entry-level" even when
# the posting doesn't spell out a number.
_SENIOR_TITLE_RE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|director|vp|vice president|head of|"
    r"distinguished|architect|manager|supervisory|supervisor|\biii\b|\biv\b)\b",
    re.I,
)

# Phrases that mean the nearby number describes something other than the individual
# candidate's required experience (team/company history, not a hiring bar).
_FALSE_CONTEXT_RE = re.compile(
    r"combined|collective|our team has|company has|founded|since \d{4}|team's? experience",
    re.I,
)

_YEAR_WORD = r"(?:years?|yrs?)"

# Range patterns are checked first and their matched spans are "claimed" - the single-number
# patterns below are skipped wherever they'd overlap a claimed span, so e.g. "2-4 years" isn't
# also read as an independent "4 years of experience" match that clobbers the range's real
# lower bound of 2.
_RANGE_PATTERNS = [
    # "2-4 years", "0 to 3 yrs", "3-5 years"
    re.compile(rf"(\d{{1,2}})\s*(?:\+)?\s*(?:-|–|—|to)\s*(\d{{1,2}})\+?\s*{_YEAR_WORD}\b", re.I),
    # "0-2 YOE"
    re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})\s*yoe\b", re.I),
]

_SINGLE_PATTERNS = [
    # "5+ years"
    re.compile(rf"(\d{{1,2}})\+\s*{_YEAR_WORD}\b", re.I),
    # "at least 5 years" / "minimum of 3 years"
    re.compile(rf"(?:at least|minimum(?:\s+of)?)\s*(\d{{1,2}})\s*{_YEAR_WORD}\b", re.I),
    # "3 years of experience" / "2 years professional experience"
    re.compile(
        rf"(\d{{1,2}})\s*{_YEAR_WORD}(?:\s+of)?\s+(?:professional\s+|relevant\s+|industry\s+|"
        rf"working\s+|hands-on\s+|prior\s+|software\s+(?:development\s+|engineering\s+)?)?experience\b",
        re.I,
    ),
    # "5+ YOE"
    re.compile(r"(\d{1,2})\+?\s*yoe\b", re.I),
]

_MAX_PLAUSIBLE_INDIVIDUAL_YEARS = 20


def extract_min_years_required(text: str) -> int | None:
    """Returns the best-guess minimum years of experience a posting asks for, or None
    if nothing usable was found. When multiple different numbers are mentioned (e.g. "5+
    years overall, with 2+ years in Node.js"), the largest is treated as the binding
    requirement, since sub-mentions of a specific skill are usually <= the overall bar."""
    if not text:
        return None

    candidates = []
    claimed_spans = []

    for pattern in _RANGE_PATTERNS:
        for match in pattern.finditer(text):
            context = text[max(0, match.start() - 40): match.start()]
            if _FALSE_CONTEXT_RE.search(context):
                continue
            groups = [int(g) for g in match.groups() if g is not None]
            lo = min(groups)
            if lo > _MAX_PLAUSIBLE_INDIVIDUAL_YEARS:
                continue
            candidates.append(lo)
            claimed_spans.append(match.span())

    for pattern in _SINGLE_PATTERNS:
        for match in pattern.finditer(text):
            if any(start <= match.start() < end for start, end in claimed_spans):
                continue  # part of an already-counted range - don't double count
            context = text[max(0, match.start() - 40): match.start()]
            if _FALSE_CONTEXT_RE.search(context):
                continue
            value = int(match.group(1))
            if value > _MAX_PLAUSIBLE_INDIVIDUAL_YEARS:
                continue
            candidates.append(value)

    if not candidates:
        return None
    return max(candidates)


def matches_experience_range(title: str, description: str, max_years: int) -> bool:
    haystack_title = title or ""
    if _JUNIOR_SIGNAL_RE.search(haystack_title) or _JUNIOR_SIGNAL_RE.search(description or ""):
        return True
    required = extract_min_years_required(description or "")
    if required is not None:
        return required <= max_years
    # No explicit number found - fall back to whether the title itself signals seniority.
    if _SENIOR_TITLE_RE.search(haystack_title):
        return False
    return True
