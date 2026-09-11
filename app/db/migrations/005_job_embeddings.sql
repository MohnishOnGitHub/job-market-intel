CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS job_embeddings (
    job_id BIGINT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding vector NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (job_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_job_embeddings_model
    ON job_embeddings (embedding_model);
