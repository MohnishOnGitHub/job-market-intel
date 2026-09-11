from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.ingestion_runs import IngestionRunRepository
from app.db.repositories.jobs import JobRepository
from app.ingestion.models import RawJob
from app.ingestion.service import IngestionService
from tests.fakes import StaticJobSource


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


def _service(conn, start_minute=0):
    clock = {"n": start_minute}

    def now():
        clock["n"] += 1
        return datetime(2026, 2, 1, 0, clock["n"], tzinfo=timezone.utc)

    return IngestionService(
        JobRepository(conn),
        IngestionRunRepository(conn),
        now_fn=now,
    )


def test_pipeline_insert_then_idempotent_replay(migrated_db):
    service = _service(migrated_db)
    source = StaticJobSource([_raw(str(i)) for i in range(10)])
    first = service.run(source)
    second = service.run(source)
    assert first.records_inserted == 10
    assert second.records_fetched == 10
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert second.records_unchanged == 10
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM jobs")
        assert cursor.fetchone()[0] == 10
        cursor.execute("SELECT COUNT(*) FROM ingestion_runs")
        assert cursor.fetchone()[0] == 2


def test_pipeline_updates_changed_jobs(migrated_db):
    service = _service(migrated_db)
    service.run(StaticJobSource([_raw("1", "Original")]))
    counts = service.run(StaticJobSource([_raw("1", "Updated")]))
    assert counts.records_updated == 1
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT description FROM jobs WHERE source_job_id = '1'")
        assert cursor.fetchone()[0] == "Updated"


def test_pipeline_keeps_going_after_malformed_record(migrated_db):
    service = _service(migrated_db)
    source = StaticJobSource(
        [_raw("1"), RawJob(source="adzuna", title=""), _raw("2")]
    )
    counts = service.run(source)
    assert counts.records_inserted == 2
    assert counts.records_skipped == 1
    assert counts.status == "completed"
