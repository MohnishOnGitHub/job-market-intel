from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, List, Optional, Tuple

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.services.freshness import FRESHNESS_BUCKETS


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
        experience: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        where, params = _job_filters(title, location, experience)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    total_jobs, jobs_with_skills = _job_totals(cursor, where, params)
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

        return {
            "total_jobs": total_jobs,
            "jobs_with_skills": jobs_with_skills,
            "skills": [
                {
                    "skill": row[0],
                    "category": row[1],
                    "job_count": row[2],
                    "job_share": _share(row[2], total_jobs),
                }
                for row in rows
            ],
        }

    def skill_categories(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        experience: Optional[str] = None,
    ) -> dict:
        where, params = _job_filters(title, location, experience)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    total_jobs, _jobs_with_skills = _job_totals(cursor, where, params)
                    cursor.execute(
                        f"""
                        SELECT s.category, COUNT(DISTINCT j.id) AS job_count
                        FROM skills s
                        JOIN job_skills js ON js.skill_id = s.id
                        JOIN jobs j ON j.id = js.job_id
                        WHERE {where}
                        GROUP BY s.category
                        ORDER BY job_count DESC, s.category
                        """,
                        params,
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc
        return {
            "total_jobs": total_jobs,
            "metric": "jobs_with_at_least_one_skill_in_category",
            "categories": [
                {
                    "category": row[0],
                    "job_count": row[1],
                    "job_share": _share(row[1], total_jobs),
                }
                for row in rows
            ],
        }

    def experience_counts(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> dict:
        where, params = _job_filters(title, location, None)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    total_jobs, _jobs_with_skills = _job_totals(cursor, where, params)
                    cursor.execute(
                        f"""
                        SELECT
                            COALESCE(NULLIF(BTRIM(j.experience_level), ''), 'unknown')
                                AS experience_level,
                            COUNT(*) AS job_count
                        FROM jobs j
                        WHERE {where}
                        GROUP BY 1
                        ORDER BY job_count DESC, experience_level
                        """,
                        params,
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc
        return {
            "total_jobs": total_jobs,
            "items": [
                {"experience_level": row[0], "job_count": row[1]} for row in rows
            ],
        }

    def locations(
        self,
        title: Optional[str] = None,
        experience: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        where, params = _job_filters(title, None, experience)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    total_jobs, _jobs_with_skills = _job_totals(cursor, where, params)
                    cursor.execute(
                        f"""
                        SELECT
                            COALESCE(
                                NULLIF(BTRIM(COALESCE(j.location_normalized, j.location_raw)), ''),
                                'unknown'
                            ) AS location,
                            COUNT(*) AS job_count
                        FROM jobs j
                        WHERE {where}
                        GROUP BY 1
                        ORDER BY job_count DESC, location
                        LIMIT %s
                        """,
                        [*params, limit],
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc
        return {
            "total_jobs": total_jobs,
            "note": (
                "Locations are COALESCE(location_normalized, location_raw) strings, "
                "not geocoded regions."
            ),
            "items": [{"location": row[0], "job_count": row[1]} for row in rows],
        }

    def companies(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        experience: Optional[str] = None,
        limit: int = 25,
    ) -> dict:
        where, params = _job_filters(title, location, experience)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    total_jobs, _jobs_with_skills = _job_totals(cursor, where, params)
                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM jobs j
                        WHERE {where}
                          AND (j.company IS NULL OR BTRIM(j.company) = '')
                        """,
                        params,
                    )
                    missing = cursor.fetchone()[0]
                    cursor.execute(
                        f"""
                        SELECT BTRIM(j.company) AS company, COUNT(*) AS job_count
                        FROM jobs j
                        WHERE {where}
                          AND j.company IS NOT NULL
                          AND BTRIM(j.company) <> ''
                        GROUP BY 1
                        ORDER BY job_count DESC, company
                        LIMIT %s
                        """,
                        [*params, limit],
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc
        return {
            "total_jobs": total_jobs,
            "jobs_without_company": missing,
            "items": [{"company": row[0], "job_count": row[1]} for row in rows],
        }

    def freshness(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        experience: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> dict:
        moment = now or datetime.now(timezone.utc)
        where, params = _job_filters(title, location, experience)
        d7 = moment - timedelta(days=7)
        d30 = moment - timedelta(days=30)
        d60 = moment - timedelta(days=60)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT
                            CASE
                                WHEN j.posted_at IS NULL THEN 'unknown'
                                WHEN j.posted_at >= %s THEN '0-7 days'
                                WHEN j.posted_at >= %s THEN '8-30 days'
                                WHEN j.posted_at >= %s THEN '31-60 days'
                                ELSE '61+ days'
                            END AS bucket,
                            COUNT(*) AS job_count
                        FROM jobs j
                        WHERE {where}
                        GROUP BY 1
                        """,
                        [d7, d30, d60, *params],
                    )
                    rows = {row[0]: row[1] for row in cursor.fetchall()}
                    cursor.execute(f"SELECT COUNT(*) FROM jobs j WHERE {where}", params)
                    total_jobs = cursor.fetchone()[0]
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc
        return {
            "total_jobs": total_jobs,
            "as_of": moment,
            "basis": "posted_at",
            "items": [
                {"bucket": bucket, "job_count": rows.get(bucket, 0)}
                for bucket in FRESHNESS_BUCKETS
            ],
        }

    def overview(
        self,
        title: Optional[str] = None,
        location: Optional[str] = None,
        experience: Optional[str] = None,
    ) -> dict:
        where, params = _job_filters(title, location, experience)
        demand = self.skill_demand(
            title=title, location=location, experience=experience, limit=1
        )
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM skills")
                    canonical_skills = cursor.fetchone()[0]
                    cursor.execute(
                        """
                        SELECT MAX(completed_at)
                        FROM ingestion_runs
                        WHERE status IN ('completed', 'completed_with_errors')
                        """
                    )
                    latest_ingestion = cursor.fetchone()[0]
                    cursor.execute(
                        f"SELECT MAX(j.last_seen_at) FROM jobs j WHERE {where}",
                        params,
                    )
                    latest_seen = cursor.fetchone()[0]
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

        top = demand["skills"][0] if demand["skills"] else None
        return {
            "active_jobs": demand["total_jobs"],
            "jobs_with_skills": demand["jobs_with_skills"],
            "canonical_skills": canonical_skills,
            "latest_ingestion_at": latest_ingestion,
            "latest_job_seen_at": latest_seen,
            "top_skill": top,
        }


def _job_filters(
    title: Optional[str],
    location: Optional[str],
    experience: Optional[str],
) -> Tuple[str, List]:
    filters = ["j.active = TRUE"]
    params: list = []
    if title:
        filters.append("j.title ILIKE %s")
        params.append(f"%{title}%")
    if location:
        filters.append("COALESCE(j.location_normalized, j.location_raw) ILIKE %s")
        params.append(f"%{location}%")
    if experience:
        cleaned = experience.strip().lower()
        if cleaned == "unknown":
            filters.append(
                "(j.experience_level IS NULL OR BTRIM(j.experience_level) = '')"
            )
        else:
            filters.append("LOWER(BTRIM(j.experience_level)) = %s")
            params.append(cleaned)
    return " AND ".join(filters), params


def _job_totals(cursor, where: str, params: list) -> Tuple[int, int]:
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
    return total_jobs, jobs_with_skills


def _share(count: int, total: int) -> float:
    if not total:
        return 0.0
    return round(count / total, 3)


def get_analytics_repository() -> AnalyticsRepository:
    return AnalyticsRepository()
