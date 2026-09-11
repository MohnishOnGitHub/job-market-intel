from __future__ import annotations

from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "app" / "db" / "migrations"


def test_jobs_migration_defines_canonical_columns_and_identity():
    sql = (MIGRATIONS / "002_jobs.sql").read_text(encoding="utf-8")
    for column in (
        "source",
        "source_job_id",
        "source_url",
        "location_raw",
        "location_normalized",
        "first_seen_at",
        "last_seen_at",
        "active",
        "content_hash",
    ):
        assert column in sql
    assert "uq_jobs_source_source_job_id" in sql
    assert "uq_jobs_source_source_url" in sql


def test_ingestion_runs_migration_defines_metrics():
    sql = (MIGRATIONS / "003_ingestion_runs.sql").read_text(encoding="utf-8")
    for column in (
        "records_fetched",
        "records_inserted",
        "records_updated",
        "records_unchanged",
        "records_skipped",
        "records_failed",
        "error_summary",
    ):
        assert column in sql
    assert "completed_with_errors" in sql
