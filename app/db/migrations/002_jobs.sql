CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_job_id TEXT,
    source_url TEXT,
    company TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    location_raw TEXT,
    location_normalized TEXT,
    employment_type TEXT,
    experience_level TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT,
    posted_at TIMESTAMPTZ,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_source_source_job_id
    ON jobs (source, source_job_id)
    WHERE source_job_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_jobs_source_source_url
    ON jobs (source, source_url)
    WHERE source_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (active);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs (posted_at);
CREATE INDEX IF NOT EXISTS idx_jobs_location_normalized ON jobs (location_normalized);
CREATE INDEX IF NOT EXISTS idx_jobs_content_hash ON jobs (source, content_hash);
