from __future__ import annotations

from app.db.migrate import apply_migrations


def test_migrations_are_idempotent(migrated_db):
    applied_again = apply_migrations(migrated_db)
    assert applied_again == []
    with migrated_db.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'jobs'
            """
        )
        columns = {row[0] for row in cursor.fetchall()}
        assert {
            "source",
            "source_job_id",
            "source_url",
            "first_seen_at",
            "last_seen_at",
            "active",
            "content_hash",
            "location_raw",
        }.issubset(columns)
        cursor.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'jobs'
            """
        )
        indexes = {row[0] for row in cursor.fetchall()}
        assert "uq_jobs_source_source_job_id" in indexes
        cursor.execute("SELECT 1 FROM ingestion_runs LIMIT 1")
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'job_embeddings'
            """
        )
        embedding_columns = {row[0] for row in cursor.fetchall()}
        assert {
            "job_id",
            "embedding_model",
            "embedding",
            "content_hash",
        }.issubset(embedding_columns)
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        assert cursor.fetchone() is not None
