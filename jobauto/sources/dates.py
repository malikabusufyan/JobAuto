"""Parses each source's differently-shaped posted_at value into a UTC datetime, so
postings can be filtered by recency regardless of which source they came from.

Observed formats in the wild: Greenhouse/Ashby/Adzuna give ISO 8601 (with "Z" or a
numeric UTC offset, sometimes with fractional seconds), USAJobs gives ISO 8601 with no
timezone at all, and Lever gives epoch milliseconds as a plain numeric string. The
experimental scrapers (indeed/linkedin/dice/ycombinator) don't provide a posted date at
all - callers should fall back to discovered_at for those.
"""

from datetime import datetime, timezone


def parse_posted_at(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        try:
            return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
