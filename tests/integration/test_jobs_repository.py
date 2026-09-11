from __future__ import annotations

from datetime import datetime, timezone

import psycopg2
import pytest

from app.db.repositories.ingestion_runs import IngestionRunRepository
from app.db.repositories.jobs import UPSERT_INSERTED, UPSERT_UNCHANGED, UPSERT_UPDATED, JobRepository
from app.ingestion.models import IngestionCounts, RawJob
from app.ingestion.normalize import normalize_job


def _job(job_id="1", description="Build pipelines", url=None):
    return normalize_job(
        RawJob(
            source="adzuna",
            source_job_id=job_id,
            source_url=url or f"https://example.com/jobs/{job_id}",
            company="Example",
            title="Data Engineer",
            description=description,
            location="Bengaluru",
        )
    )


def test_insert_and_list_jobs(migrated_db):
    repo = JobRepository(migrated_db)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert repo.upsert(_job(), now=t1) == UPSERT_INSERTED
    jobs = repo.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].location == "Bengaluru"
    assert jobs[0].description == "Build pipelines"


def test_duplicate_upsert_is_unchanged_and_preserves_first_seen(migrated_db):
    repo = JobRepository(migrated_db)
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    repo.upsert(_job(), now=t1)
    assert repo.upsert(_job(), now=t2) == UPSERT_UNCHANGED
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM jobs")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT first_seen_at, last_seen_at, active FROM jobs")
        first_seen, last_seen, active = cursor.fetchone()
    assert first_seen == t1
    assert last_seen == t2
    assert active is True


def test_changed_record_updates_hash_and_preserves_first_seen(migrated_db):
    repo = JobRepository(migrated_db)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)
    repo.upsert(_job(description="Original"), now=t1)
    assert repo.upsert(_job(description="Changed"), now=t2) == UPSERT_UPDATED
    with migrated_db.cursor() as cursor:
        cursor.execute(
            "SELECT description, first_seen_at, last_seen_at, content_hash FROM jobs"
        )
        description, first_seen, last_seen, content_hash = cursor.fetchone()
    assert description == "Changed"
    assert first_seen == t1
    assert last_seen == t2
    assert content_hash == _job(description="Changed").content_hash


def test_unique_constraint_rejects_duplicate_source_job_id(migrated_db):
    repo = JobRepository(migrated_db)
    repo.upsert(_job("99"), now=datetime.now(timezone.utc))
    with pytest.raises(psycopg2.Error):
        with migrated_db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jobs (
                    source, source_job_id, title, description,
                    first_seen_at, last_seen_at
                )
                VALUES ('adzuna', '99', 'Other', 'Other desc', NOW(), NOW())
                """
            )
    migrated_db.rollback()


def test_company_and_title_do_not_merge_distinct_ids(migrated_db):
    repo = JobRepository(migrated_db)
    now = datetime.now(timezone.utc)
    repo.upsert(_job("1"), now=now)
    repo.upsert(_job("2"), now=now)
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM jobs")
        assert cursor.fetchone()[0] == 2


def test_ingestion_run_metrics_are_persisted(migrated_db):
    runs = IngestionRunRepository(migrated_db)
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    finished = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    run_id = runs.start_run("adzuna", now=started)
    runs.finish_run(
        run_id,
        IngestionCounts(
            records_fetched=10,
            records_inserted=8,
            records_updated=1,
            records_unchanged=0,
            records_skipped=1,
            records_failed=0,
            status="completed",
        ),
        now=finished,
    )
    with migrated_db.cursor() as cursor:
        cursor.execute(
            """
            SELECT source, status, records_fetched, records_inserted,
                   records_updated, records_skipped
            FROM ingestion_runs WHERE id = %s
            """,
            (run_id,),
        )
        row = cursor.fetchone()
    assert row == ("adzuna", "completed", 10, 8, 1, 1)
