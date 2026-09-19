import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from jobauto.config import DB_PATH
from jobauto.sources.dates import parse_posted_at
from jobauto.sources.experience import extract_min_years_required

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    remote INTEGER DEFAULT 0,
    salary TEXT,
    url TEXT NOT NULL,
    description TEXT,
    posted_at TEXT,
    discovered_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    resume_pdf_path TEXT,
    resume_docx_path TEXT,
    cover_letter_pdf_path TEXT,
    tailoring_json TEXT,
    notes TEXT,
    UNIQUE(source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
"""

# Status lifecycle: new -> generated -> ready -> applied -> interview -> offer -> rejected -> skipped


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
        if "estimated_min_years" not in existing_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN estimated_min_years INTEGER")
        if "application_plan" not in existing_cols:
            conn.execute(
                "ALTER TABLE jobs ADD COLUMN application_plan TEXT NOT NULL DEFAULT 'not_applied'"
            )


def upsert_job(job: dict) -> tuple[int, bool]:
    """Insert a job if new (matched by source+external_id); ignore if it already exists.
    Returns (row id, True if newly created)."""
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id FROM jobs WHERE source = ? AND external_id = ?",
            (job["source"], job["external_id"]),
        )
        row = cur.fetchone()
        if row:
            return row["id"], False
        cur = conn.execute(
            """INSERT INTO jobs
               (source, external_id, title, company, location, remote, salary, url,
                description, posted_at, discovered_at, status, estimated_min_years)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
            (
                job["source"],
                job["external_id"],
                job["title"],
                job["company"],
                job.get("location"),
                1 if job.get("remote") else 0,
                job.get("salary"),
                job["url"],
                job.get("description"),
                job.get("posted_at"),
                datetime.now(timezone.utc).isoformat(),
                extract_min_years_required(job.get("description") or ""),
            ),
        )
        return cur.lastrowid, True


def list_jobs(
    status: str | None = None,
    max_years: int | None = None,
    application_plan: str | None = None,
    posted_within_days: int | None = None,
) -> list[sqlite3.Row]:
    """max_years keeps jobs whose estimated requirement is <= max_years, OR unknown
    (estimated_min_years is NULL) - unrecognized postings aren't hidden just because the
    years-of-experience heuristic couldn't find a number in them.

    posted_within_days is applied in Python, not SQL, because posted_at is stored in
    whatever shape each source's API gives it (ISO 8601 with varying precision/timezone,
    or Lever's epoch-millisecond string) - see jobauto.sources.dates. Postings whose
    posted_at can't be parsed (or is missing, as with the experimental scrapers) fall
    back to discovered_at rather than being hidden."""
    query = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if max_years is not None:
        query += " AND (estimated_min_years IS NULL OR estimated_min_years <= ?)"
        params.append(max_years)
    if application_plan:
        query += " AND application_plan = ?"
        params.append(application_plan)
    query += " ORDER BY discovered_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    if posted_within_days is None:
        return rows
    cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
    return [row for row in rows if _effective_posted_at(row) >= cutoff]


def _effective_posted_at(row: sqlite3.Row) -> datetime:
    return (
        parse_posted_at(row["posted_at"])
        or parse_posted_at(row["discovered_at"])
        or datetime.min.replace(tzinfo=timezone.utc)
    )


def backfill_estimated_years() -> int:
    """Computes estimated_min_years for rows inserted before that column existed."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, description FROM jobs WHERE estimated_min_years IS NULL"
        ).fetchall()
        for row in rows:
            years = extract_min_years_required(row["description"] or "")
            if years is not None:
                conn.execute("UPDATE jobs SET estimated_min_years = ? WHERE id = ?", (years, row["id"]))
        return len(rows)


def get_job(job_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def delete_job(job_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def update_job(job_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))


def set_status(job_id: int, status: str):
    update_job(job_id, status=status)


def set_application_plan(job_id: int, application_plan: str):
    update_job(job_id, application_plan=application_plan)
