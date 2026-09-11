from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List, Optional

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection


class AnalyticsRepository:
    def __init__(self, connection=None) -> None:
        self._connection = connection

    @contextmanager
    def _conn(self) -> Iterator:
        if self._connection is not None:
            yield self._connection
            return
        with get_connection() as conn:
            yield conn

    def skill_demand(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        title_like = f"%{title}%" if title else None
        location_like = f"%{location}%" if location else None
        filters = ["j.active = TRUE"]
        params: list = []
        if title_like:
            filters.append("j.title ILIKE %s")
            params.append(title_like)
        if location_like:
            filters.append(
                "COALESCE(j.location_normalized, j.location_raw) ILIKE %s"
            )
            params.append(location_like)
        where = " AND ".join(filters)

        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM jobs j WHERE {where}", params)
                    total_jobs = cursor.fetchone()[0]
                    cursor.execute(
                        f"""
                        SELECT COUNT(DISTINCT j.id)
                        FROM jobs j
                        JOIN job_skills js ON js.job_id = j.id
                        WHERE {where}
                        """,
                        params,
                    )
                    jobs_with_skills = cursor.fetchone()[0]
                    cursor.execute(
                        f"""
                        SELECT s.canonical_name, s.category, COUNT(DISTINCT j.id) AS job_count
                        FROM skills s
                        JOIN job_skills js ON js.skill_id = s.id
                        JOIN jobs j ON j.id = js.job_id
                        WHERE {where}
                        GROUP BY s.canonical_name, s.category
                        ORDER BY job_count DESC, s.canonical_name
                        LIMIT %s
                        """,
                        [*params, limit],
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

        denominator = total_jobs or 0
        skills = [
            {
                "skill": row[0],
                "category": row[1],
                "job_count": row[2],
                "job_share": round(row[2] / denominator, 3) if denominator else 0.0,
            }
            for row in rows
        ]
        return {
            "total_jobs": total_jobs,
            "jobs_with_skills": jobs_with_skills,
            "skills": skills,
        }


def get_analytics_repository() -> AnalyticsRepository:
    return AnalyticsRepository()
