from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.ingestion.models import IngestionCounts


class IngestionRunRepository:
    def __init__(self, connection=None) -> None:
        self._connection = connection

    @contextmanager
    def _conn(self) -> Iterator:
        if self._connection is not None:
            yield self._connection
            return
        with get_connection() as conn:
            yield conn

    def start_run(self, source: str, now: Optional[datetime] = None) -> int:
        moment = now or datetime.now(timezone.utc)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO ingestion_runs (source, started_at, status)
                        VALUES (%s, %s, 'running')
                        RETURNING id
                        """,
                        (source, moment),
                    )
                    run_id = cursor.fetchone()[0]
                    if self._connection is None:
                        conn.commit()
                    return run_id
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

    def finish_run(
        self,
        run_id: int,
        counts: IngestionCounts,
        now: Optional[datetime] = None,
    ) -> None:
        moment = now or datetime.now(timezone.utc)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE ingestion_runs
                        SET completed_at = %s,
                            status = %s,
                            records_fetched = %s,
                            records_inserted = %s,
                            records_updated = %s,
                            records_unchanged = %s,
                            records_skipped = %s,
                            records_failed = %s,
                            error_summary = %s
                        WHERE id = %s
                        """,
                        (
                            moment,
                            counts.status,
                            counts.records_fetched,
                            counts.records_inserted,
                            counts.records_updated,
                            counts.records_unchanged,
                            counts.records_skipped,
                            counts.records_failed,
                            counts.error_summary,
                            run_id,
                        ),
                    )
                    if self._connection is None:
                        conn.commit()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc


def get_ingestion_run_repository() -> IngestionRunRepository:
    return IngestionRunRepository()
