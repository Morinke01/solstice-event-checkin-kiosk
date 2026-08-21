"""SQLite-backed attendee and print-job state."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


TEST_ATTENDEES = [
    ("SOL-001", "Amina Njeri"),
    ("SOL-002", "David Ochieng"),
    ("SOL-003", "Grace Wanjiku"),
]


class AttendeeStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self.initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS attendees (
                    attendee_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'REGISTERED',
                    print_job_id TEXT,
                    checked_in_at TEXT
                );

                CREATE TABLE IF NOT EXISTS print_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attendee_id TEXT NOT NULL,
                    print_job_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (attendee_id) REFERENCES attendees(attendee_id)
                );
                """
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO attendees (attendee_id, name)
                VALUES (?, ?)
                """,
                TEST_ATTENDEES,
            )

    def get_attendee(self, attendee_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM attendees WHERE attendee_id = ?", (attendee_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_attendees(self) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM attendees ORDER BY attendee_id"
            ).fetchall()
        return [dict(row) for row in rows]

    def begin_printing(self, attendee_id: str) -> bool:
        """Reserve one attendee for printing using an atomic status change."""

        with self.connection() as connection:
            cursor = connection.execute(
                """
                UPDATE attendees
                SET status = 'PRINTING'
                WHERE attendee_id = ? AND status = 'REGISTERED'
                """,
                (attendee_id,),
            )
        return cursor.rowcount == 1

    def complete_check_in(self, attendee_id: str, print_job_id: str) -> None:
        completed_at = datetime.now(timezone.utc).isoformat()
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO print_attempts (attendee_id, print_job_id, created_at)
                VALUES (?, ?, ?)
                """,
                (attendee_id, print_job_id, completed_at),
            )
            connection.execute(
                """
                UPDATE attendees
                SET status = 'CHECKED_IN', print_job_id = ?, checked_in_at = ?
                WHERE attendee_id = ?
                """,
                (print_job_id, completed_at, attendee_id),
            )

    def reset_after_print_failure(self, attendee_id: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE attendees
                SET status = 'REGISTERED'
                WHERE attendee_id = ? AND status = 'PRINTING'
                """,
                (attendee_id,),
            )

    def print_attempt_count(self, attendee_id: str) -> int:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM print_attempts
                WHERE attendee_id = ?
                """,
                (attendee_id,),
            ).fetchone()
        return int(row["count"])
