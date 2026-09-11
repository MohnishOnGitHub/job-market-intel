CREATE TABLE IF NOT EXISTS skills (
    id BIGSERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skill_aliases (
    id BIGSERIAL PRIMARY KEY,
    skill_id BIGINT NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    UNIQUE (normalized_alias)
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id BIGINT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    skill_id BIGINT NOT NULL REFERENCES skills (id) ON DELETE CASCADE,
    extraction_source TEXT NOT NULL DEFAULT 'taxonomy_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (job_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill_id ON job_skills (skill_id);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills (category);
