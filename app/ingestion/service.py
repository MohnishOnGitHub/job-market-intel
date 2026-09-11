from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from app.core.exceptions import DatabaseUnavailableError, JobSourceError, JobValidationError
from app.db.repositories.ingestion_runs import IngestionRunRepository
from app.db.repositories.jobs import (
    UPSERT_INSERTED,
    UPSERT_UNCHANGED,
    UPSERT_UPDATED,
    JobRepository,
)
from app.ingestion.base import JobSource
from app.ingestion.models import IngestionCounts, RawJob
from app.ingestion.normalize import normalize_job

logger = logging.getLogger("app.ingestion")


class IngestionService:
    def __init__(
        self,
        job_repository: JobRepository,
        run_repository: IngestionRunRepository,
        now_fn: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.job_repository = job_repository
        self.run_repository = run_repository
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    def run(self, source: JobSource) -> IngestionCounts:
        source_name = getattr(source, "name", "unknown")
        started = self.now_fn()
        logger.info("event=ingestion_started source=%s", source_name)

        run_id = self.run_repository.start_run(source_name, now=started)
        counts = IngestionCounts()

        try:
            raw_jobs = list(source.fetch_jobs())
        except JobSourceError as exc:
            counts.status = "failed"
            counts.error_summary = exc.message
            self._safe_finish(run_id, counts)
            logger.info("event=ingestion_failed source=%s reason=source_error", source_name)
            raise
        except Exception:
            counts.status = "failed"
            counts.error_summary = "Source fetch failed."
            self._safe_finish(run_id, counts)
            logger.info("event=ingestion_failed source=%s reason=source_error", source_name)
            raise JobSourceError("Job source request failed.")

        counts.records_fetched = len(raw_jobs)
        logger.info(
            "event=source_fetch_completed source=%s records_fetched=%s",
            source_name,
            counts.records_fetched,
        )

        try:
            for raw in raw_jobs:
                self._ingest_one(raw, counts)
        except DatabaseUnavailableError:
            counts.status = "failed"
            counts.error_summary = "Database is unavailable."
            self._safe_finish(run_id, counts)
            logger.info("event=ingestion_failed source=%s reason=database", source_name)
            raise

        if counts.records_failed:
            counts.status = "completed_with_errors"
        else:
            counts.status = "completed"

        self.run_repository.finish_run(run_id, counts, now=self.now_fn())
        logger.info(
            "event=ingestion_completed source=%s status=%s inserted=%s updated=%s unchanged=%s skipped=%s failed=%s",
            source_name,
            counts.status,
            counts.records_inserted,
            counts.records_updated,
            counts.records_unchanged,
            counts.records_skipped,
            counts.records_failed,
        )
        return counts

    def _ingest_one(self, raw: RawJob, counts: IngestionCounts) -> None:
        try:
            normalized = normalize_job(raw)
        except JobValidationError:
            counts.records_skipped += 1
            return
        except Exception:
            counts.records_failed += 1
            logger.exception("event=job_failed reason=normalize")
            return

        try:
            outcome = self.job_repository.upsert(normalized, now=self.now_fn())
        except DatabaseUnavailableError:
            raise
        except Exception:
            counts.records_failed += 1
            logger.exception("event=job_failed reason=upsert")
            return

        if outcome == UPSERT_INSERTED:
            counts.records_inserted += 1
        elif outcome == UPSERT_UPDATED:
            counts.records_updated += 1
        elif outcome == UPSERT_UNCHANGED:
            counts.records_unchanged += 1
        else:
            counts.records_failed += 1

    def _safe_finish(self, run_id: int, counts: IngestionCounts) -> None:
        try:
            self.run_repository.finish_run(run_id, counts, now=self.now_fn())
        except Exception:
            logger.exception("event=ingestion_run_finalize_failed")
