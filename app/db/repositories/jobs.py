from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, List, Optional

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.ingestion.models import NormalizedJob
from app.schemas.job import Job

UPSERT_INSERTED = "inserted"
UPSERT_UPDATED = "updated"
UPSERT_UNCHANGED = "unchanged"


class JobRepository:
    def __init__(self, connection=None) -> None:
        self._connection = connection

    @contextmanager
    def _conn(self) -> Iterator:
        if self._connection is not None:
            yield self._connection
            return
        with get_connection() as conn:
            yield conn

    def list_jobs(self) -> List[Job]:
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            id,
                            title,
                            company,
                            COALESCE(location_normalized, location_raw) AS location,
                            description
                        FROM jobs
                        WHERE active = TRUE
                        ORDER BY id
                        """
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

        return [
            Job(
                id=row[0],
                title=row[1],
                company=row[2],
                location=row[3],
                description=row[4] or "",
            )
            for row in rows
        ]

    def find_existing(self, job: NormalizedJob) -> Optional[dict]:
        with self._conn() as conn:
            with conn.cursor() as cursor:
                return self._find_existing(cursor, job)

    def _find_existing(self, cursor, job: NormalizedJob) -> Optional[dict]:
        if job.source_job_id:
            cursor.execute(
                """
                SELECT id, content_hash, first_seen_at, source_job_id, source_url
                FROM jobs
                WHERE source = %s AND source_job_id = %s
                """,
                (job.source, job.source_job_id),
            )
            row = cursor.fetchone()
            if row:
                return _row_to_existing(row)

        if job.source_url:
            cursor.execute(
                """
                SELECT id, content_hash, first_seen_at, source_job_id, source_url
                FROM jobs
                WHERE source = %s AND source_url = %s
                """,
                (job.source, job.source_url),
            )
            row = cursor.fetchone()
            if row:
                return _row_to_existing(row)

        if not job.source_job_id and not job.source_url:
            cursor.execute(
                """
                SELECT id, content_hash, first_seen_at, source_job_id, source_url
                FROM jobs
                WHERE source = %s AND content_hash = %s
                  AND source_job_id IS NULL AND source_url IS NULL
                """,
                (job.source, job.content_hash),
            )
            row = cursor.fetchone()
            if row:
                return _row_to_existing(row)
        return None

    def upsert(self, job: NormalizedJob, now: Optional[datetime] = None) -> str:
        moment = now or datetime.now(timezone.utc)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    existing = self._find_existing(cursor, job)
                    if existing is None:
                        self._insert(cursor, job, moment)
                        if self._connection is None:
                            conn.commit()
                        return UPSERT_INSERTED

                    if existing["content_hash"] == job.content_hash:
                        cursor.execute(
                            """
                            UPDATE jobs
                            SET last_seen_at = %s,
                                active = TRUE
                            WHERE id = %s
                            """,
                            (moment, existing["id"]),
                        )
                        if self._connection is None:
                            conn.commit()
                        return UPSERT_UNCHANGED

                    cursor.execute(
                        """
                        UPDATE jobs
                        SET source_url = %s,
                            company = %s,
                            title = %s,
                            description = %s,
                            location_raw = %s,
                            location_normalized = %s,
                            employment_type = %s,
                            experience_level = %s,
                            salary_min = %s,
                            salary_max = %s,
                            salary_currency = %s,
                            posted_at = %s,
                            content_hash = %s,
                            last_seen_at = %s,
                            updated_at = %s,
                            active = TRUE
                        WHERE id = %s
                        """,
                        (
                            job.source_url,
                            job.company,
                            job.title,
                            job.description,
                            job.location_raw,
                            job.location_normalized,
                            job.employment_type,
                            job.experience_level,
                            job.salary_min,
                            job.salary_max,
                            job.salary_currency,
                            job.posted_at,
                            job.content_hash,
                            moment,
                            moment,
                            existing["id"],
                        ),
                    )
                    if self._connection is None:
                        conn.commit()
                    return UPSERT_UPDATED
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

    def set_active(self, job_id: int, active: bool) -> None:
        with self._conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE jobs SET active = %s, updated_at = NOW() WHERE id = %s",
                    (active, job_id),
                )
                if self._connection is None:
                    conn.commit()

    def _insert(self, cursor, job: NormalizedJob, moment: datetime) -> None:
        cursor.execute(
            """
            INSERT INTO jobs (
                source, source_job_id, source_url, company, title, description,
                location_raw, location_normalized, employment_type, experience_level,
                salary_min, salary_max, salary_currency, posted_at,
                first_seen_at, last_seen_at, active, content_hash,
                created_at, updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, TRUE, %s,
                %s, %s
            )
            """,
            (
                job.source,
                job.source_job_id,
                job.source_url,
                job.company,
                job.title,
                job.description,
                job.location_raw,
                job.location_normalized,
                job.employment_type,
                job.experience_level,
                job.salary_min,
                job.salary_max,
                job.salary_currency,
                job.posted_at,
                moment,
                moment,
                job.content_hash,
                moment,
                moment,
            ),
        )


def _row_to_existing(row) -> dict:
    return {
        "id": row[0],
        "content_hash": row[1],
        "first_seen_at": row[2],
        "source_job_id": row[3],
        "source_url": row[4],
    }


def get_job_repository() -> JobRepository:
    return JobRepository()
