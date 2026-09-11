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


def test_skills_migration_defines_tables_and_uniqueness():
    sql = (MIGRATIONS / "004_skills.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS skills" in sql
    assert "CREATE TABLE IF NOT EXISTS skill_aliases" in sql
    assert "CREATE TABLE IF NOT EXISTS job_skills" in sql
    assert "PRIMARY KEY (job_id, skill_id)" in sql
    assert "canonical_name TEXT NOT NULL UNIQUE" in sql


def test_embeddings_migration_requires_pgvector():
    sql = (MIGRATIONS / "005_job_embeddings.sql").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "CREATE TABLE IF NOT EXISTS job_embeddings" in sql
    assert "embedding vector NOT NULL" in sql
    assert "PRIMARY KEY (job_id, embedding_model)" in sql
    assert "content_hash TEXT NOT NULL" in sql


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
