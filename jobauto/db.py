import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from jobauto.config import DB_PATH

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
                description, posted_at, discovered_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
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
            ),
        )
        return cur.lastrowid, True


def list_jobs(status: str | None = None) -> list[sqlite3.Row]:
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY discovered_at DESC", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM jobs ORDER BY discovered_at DESC").fetchall()


def get_job(job_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def update_job(job_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))


def set_status(job_id: int, status: str):
    update_job(job_id, status=status)
