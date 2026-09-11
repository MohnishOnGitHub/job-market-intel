from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional

from app.db.repositories.jobs import UPSERT_INSERTED, UPSERT_UNCHANGED, UPSERT_UPDATED
from app.ingestion.models import IngestionCounts, NormalizedJob, RawJob


class StaticJobSource:
    name = "adzuna"

    def __init__(self, jobs: Iterable[RawJob], name: str = "adzuna") -> None:
        self.name = name
        self._jobs = list(jobs)

    def fetch_jobs(self) -> List[RawJob]:
        return list(self._jobs)


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.rows: List[dict] = []
        self.next_id = 1

    def _find(self, job: NormalizedJob) -> Optional[dict]:
        if job.source_job_id:
            for row in self.rows:
                if row["source"] == job.source and row["source_job_id"] == job.source_job_id:
                    return row
        if job.source_url:
            for row in self.rows:
                if row["source"] == job.source and row["source_url"] == job.source_url:
                    return row
        if not job.source_job_id and not job.source_url:
            for row in self.rows:
                if (
                    row["source"] == job.source
                    and row["content_hash"] == job.content_hash
                    and row["source_job_id"] is None
                    and row["source_url"] is None
                ):
                    return row
        return None

    def find_existing(self, job: NormalizedJob) -> Optional[dict]:
        row = self._find(job)
        if row is None:
            return None
        return {
            "id": row["id"],
            "content_hash": row["content_hash"],
            "first_seen_at": row["first_seen_at"],
            "source_job_id": row["source_job_id"],
            "source_url": row["source_url"],
        }

    def upsert(self, job: NormalizedJob, now: Optional[datetime] = None) -> str:
        moment = now or datetime.now(timezone.utc)
        existing = self._find(job)
        if existing is None:
            self.rows.append(
                {
                    "id": self.next_id,
                    "source": job.source,
                    "source_job_id": job.source_job_id,
                    "source_url": job.source_url,
                    "company": job.company,
                    "title": job.title,
                    "description": job.description,
                    "location_raw": job.location_raw,
                    "location_normalized": job.location_normalized,
                    "content_hash": job.content_hash,
                    "first_seen_at": moment,
                    "last_seen_at": moment,
                    "updated_at": moment,
                    "active": True,
                }
            )
            self.next_id += 1
            return UPSERT_INSERTED

        if existing["content_hash"] == job.content_hash:
            existing["last_seen_at"] = moment
            existing["active"] = True
            return UPSERT_UNCHANGED

        existing.update(
            {
                "source_url": job.source_url,
                "company": job.company,
                "title": job.title,
                "description": job.description,
                "location_raw": job.location_raw,
                "location_normalized": job.location_normalized,
                "content_hash": job.content_hash,
                "last_seen_at": moment,
                "updated_at": moment,
                "active": True,
            }
        )
        return UPSERT_UPDATED


class InMemoryRunRepository:
    def __init__(self) -> None:
        self.runs: List[dict] = []
        self.next_id = 1

    def start_run(self, source: str, now: Optional[datetime] = None) -> int:
        run_id = self.next_id
        self.next_id += 1
        self.runs.append(
            {
                "id": run_id,
                "source": source,
                "started_at": now or datetime.now(timezone.utc),
                "completed_at": None,
                "status": "running",
                "counts": None,
            }
        )
        return run_id

    def finish_run(
        self,
        run_id: int,
        counts: IngestionCounts,
        now: Optional[datetime] = None,
    ) -> None:
        for run in self.runs:
            if run["id"] == run_id:
                run["completed_at"] = now or datetime.now(timezone.utc)
                run["status"] = counts.status
                run["counts"] = counts
                return
