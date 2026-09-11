from __future__ import annotations

from typing import List

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.schemas.job import Job


class JobRepository:
    def list_jobs(self) -> List[Job]:
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, title, company, location, description FROM jobs"
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


def get_job_repository() -> JobRepository:
    return JobRepository()
