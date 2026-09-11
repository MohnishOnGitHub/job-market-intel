from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.exceptions import JobSourceError
from app.ingestion.models import RawJob
from app.ingestion.service import IngestionService
from tests.fakes import InMemoryJobRepository, InMemoryRunRepository, StaticJobSource


def _raw(job_id: str, description: str = "Build APIs with Python") -> RawJob:
    return RawJob(
        source="adzuna",
        source_job_id=job_id,
        source_url=f"https://example.com/jobs/{job_id}",
        company="Example",
        title=f"Engineer {job_id}",
        description=description,
        location="Bengaluru",
    )


def _service():
    jobs = InMemoryJobRepository()
    runs = InMemoryRunRepository()
    clock = {"n": 0}

    def now():
        clock["n"] += 1
        return datetime(2026, 1, 1, 0, clock["n"], tzinfo=timezone.utc)

    return IngestionService(jobs, runs, now_fn=now), jobs, runs


def test_first_ingestion_inserts_all_valid_jobs():
    service, jobs, runs = _service()
    source = StaticJobSource([_raw(str(i)) for i in range(10)])
    counts = service.run(source)
    assert counts.records_fetched == 10
    assert counts.records_inserted == 10
    assert counts.records_updated == 0
    assert counts.records_unchanged == 0
    assert counts.status == "completed"
    assert len(jobs.rows) == 10
    assert runs.runs[0]["status"] == "completed"


def test_second_identical_ingestion_is_idempotent():
    service, jobs, _runs = _service()
    source = StaticJobSource([_raw(str(i)) for i in range(10)])
    first = service.run(source)
    second = service.run(source)
    assert first.records_inserted == 10
    assert second.records_fetched == 10
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert second.records_unchanged == 10
    assert len(jobs.rows) == 10
    first_seen = [row["first_seen_at"] for row in jobs.rows]
    assert first_seen == sorted(first_seen)


def test_changed_source_record_updates_without_duplicating():
    service, jobs, _runs = _service()
    service.run(StaticJobSource([_raw("1", "Original description")]))
    counts = service.run(StaticJobSource([_raw("1", "Updated description")]))
    assert counts.records_inserted == 0
    assert counts.records_updated == 1
    assert counts.records_unchanged == 0
    assert len(jobs.rows) == 1
    assert jobs.rows[0]["description"] == "Updated description"
    assert jobs.rows[0]["first_seen_at"] < jobs.rows[0]["last_seen_at"]


def test_malformed_record_does_not_stop_the_run():
    service, jobs, _runs = _service()
    source = StaticJobSource(
        [
            _raw("1"),
            RawJob(source="adzuna", source_job_id="bad"),
            _raw("2"),
        ]
    )
    counts = service.run(source)
    assert counts.records_fetched == 3
    assert counts.records_inserted == 2
    assert counts.records_skipped == 1
    assert counts.records_failed == 0
    assert counts.status == "completed"
    assert {row["source_job_id"] for row in jobs.rows} == {"1", "2"}


def test_embedding_failure_does_not_fail_ingest():
    jobs = InMemoryJobRepository()
    runs = InMemoryRunRepository()

    class BoomEmbeddings:
        def embed_job(self, job):
            raise RuntimeError("embedding backend failed")

    service = IngestionService(
        jobs,
        runs,
        now_fn=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        embedding_service=BoomEmbeddings(),
    )
    counts = service.run(StaticJobSource([_raw("1")]))
    assert counts.status == "completed"
    assert counts.records_inserted == 1
    assert len(jobs.rows) == 1


def test_source_failure_marks_run_failed():
    service, _jobs, runs = _service()

    class Boom:
        name = "adzuna"

        def fetch_jobs(self):
            raise JobSourceError("Adzuna authentication failed.")

    with pytest.raises(JobSourceError):
        service.run(Boom())
    assert runs.runs[0]["status"] == "failed"
    assert runs.runs[0]["counts"].records_inserted == 0
