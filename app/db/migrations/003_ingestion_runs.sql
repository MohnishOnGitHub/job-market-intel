CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_unchanged INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    records_failed INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT,
    CONSTRAINT ingestion_runs_status_check
        CHECK (status IN ('running', 'completed', 'completed_with_errors', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_source_started
    ON ingestion_runs (source, started_at DESC);
