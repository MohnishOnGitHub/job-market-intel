# Phase 2 Summary

## Goal

Turn Job Market Intel into a system that owns a reproducible job-data ingestion pipeline:

source → raw job → validate → normalize → deterministic dedupe → PostgreSQL upsert → ingestion-run metrics.

Adzuna is the only external source. Ranking behavior from Phase 1 is unchanged.

## Architecture Added

```text
scripts/ingest_adzuna.py          thin CLI
app/ingestion/sources/adzuna.py   JobSource adapter
app/ingestion/models.py           RawJob / NormalizedJob
app/ingestion/normalize.py
app/ingestion/hashing.py
app/ingestion/dedupe.py
app/ingestion/service.py          orchestration
app/db/migrate.py                 numbered SQL migrations
app/db/repositories/jobs.py       upsert + active-job listing
app/db/repositories/ingestion_runs.py
```

Normalization, hashing, and upsert logic do not import the Adzuna HTTP client.

## Database Schema

`jobs`

- `id` BIGSERIAL PK
- `source` TEXT NOT NULL
- `source_job_id` TEXT
- `source_url` TEXT
- `company` TEXT (nullable — not invented)
- `title` TEXT NOT NULL
- `description` TEXT NOT NULL
- `location_raw` TEXT
- `location_normalized` TEXT
- `employment_type` TEXT
- `experience_level` TEXT
- `salary_min` / `salary_max` NUMERIC
- `salary_currency` TEXT
- `posted_at` TIMESTAMPTZ
- `first_seen_at` / `last_seen_at` TIMESTAMPTZ NOT NULL
- `active` BOOLEAN NOT NULL DEFAULT TRUE
- `content_hash` TEXT
- `created_at` / `updated_at` TIMESTAMPTZ

Unique indexes:

- `(source, source_job_id)` where `source_job_id IS NOT NULL`
- `(source, source_url)` where `source_url IS NOT NULL`

`ingestion_runs` stores per-run counts and status
(`running`, `completed`, `completed_with_errors`, `failed`).

`schema_migrations` records applied SQL files.

Alembic was not added. The project has no ORM; two tables plus a version table are enough. Numbered SQL files plus a small runner are the migration mechanism.

## Ingestion Flow

```text
AdzunaSource.fetch_jobs()
  -> list[RawJob]
normalize_job()
  -> NormalizedJob + content_hash
JobRepository.upsert()
  -> inserted | updated | unchanged
IngestionRunRepository.finish_run()
```

Source-wide HTTP/auth/network failures fail the run. A malformed individual job increments skipped/failed and does not stop the run.

## Adzuna Adapter

`AdzunaSource` implements `JobSource`.

- Credentials: `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
- Country: `--country` or `ADZUNA_COUNTRY` (default `in`)
- CLI: `--query`, `--location`, `--pages`, `--results-per-page`

`id` → `source_job_id`. `redirect_url` → `source_url`. Predicted salaries (`salary_is_predicted`) are dropped. Automated tests mock HTTP responses and never call Adzuna.

## Normalization Rules

- Collapse whitespace; empty strings become `None`
- `"  Bengaluru   "` → `"Bengaluru"` (no city guessing)
- URLs: lowercase scheme/host, strip trailing slash and fragment
- Employment type: only a closed safe map (`full_time`, `part_time`, `contract`, `permanent`, `internship`, `temporary`); anything else is `None`
- Timestamps: ISO-8601 / `Z`; unparseable → `None`
- Money: numeric → `Decimal`; non-numeric → `None`
- Missing title or description → skip (`JobValidationError`)
- No invented salary or experience

## Deduplication Rules

Priority:

1. `(source, source_job_id)` when the source id exists
2. `(source, source_url)` when a canonical URL exists
3. `(source, content_hash)` only when both identity keys are missing

Company + title is never an identity. Two Adzuna ids with the same title remain two rows.

## Upsert Semantics

| Case | first_seen_at | last_seen_at | mutable fields | active | metric |
|---|---|---|---|---|---|
| New | now | now | insert | true | inserted |
| Same hash | preserved | now | unchanged | true | unchanged |
| Different hash | preserved | now | title, company, description, locations, employment, experience, salary, posted_at, source_url, content_hash, updated_at | true | updated |

Identity columns `source` and `source_job_id` are not rewritten.

## Job History

`first_seen_at` is the first successful insert. `last_seen_at` moves on every sighting. `active` is stored and defaults to true. The repository can `set_active`, but a single Adzuna page is not treated as a complete snapshot, so missing jobs are **not** auto-deactivated. That is deferred.

Matching lists `WHERE active = TRUE` and maps
`COALESCE(location_normalized, location_raw)` into the existing `Job.location` field. Ranking formulas are unchanged.

## Ingestion Run Metrics

Each CLI run writes a row with fetched / inserted / updated / unchanged / skipped / failed counts and a status. Logs emit `ingestion_started`, `source_fetch_completed`, `ingestion_completed`, and `ingestion_failed` without credentials, connection strings, or résumé text.

## Tests

Phase 1 tests kept.

Phase 2 unit tests cover RawJob/normalization, whitespace, timestamps, content-hash stability and change detection, dedupe identity, Adzuna mapping, malformed records, and an in-memory pipeline (insert → idempotent replay → update → skip).

Phase 2 PostgreSQL tests cover insert, unique constraint, first/last seen, ingestion-run persistence, and the same pipeline against a real database. They run when `TEST_DATABASE_URL` is set or when Docker can start `postgres:16-alpine`.

## Test Results

```text
.venv/bin/python -c "from app.main import app; ..."
# import_ok Job Market Intel

.venv/bin/pytest -v
# 69 passed, 10 skipped, 2 warnings
```

Passed (69): all Phase 1 tests plus Phase 2 unit tests, including in-memory idempotency.

Skipped (10): PostgreSQL repository / migration / pipeline tests.

Skip reason: no `TEST_DATABASE_URL`, nothing listening on localhost:5432, and `docker info` failed (Docker CLI is installed; the daemon is not running). Those tests were not fabricated as passing.

Idempotency (in-memory fixture, 10 jobs):

- Run 1: fetched 10, inserted 10
- Run 2 identical: fetched 10, inserted 0, updated 0, unchanged 10

## Known Limitations

- Live PostgreSQL upsert was not executed in this environment.
- Only Adzuna is supported.
- Location normalization is whitespace-only.
- Predicted Adzuna salaries are discarded.
- Jobs are not deactivated when absent from a page.
- Legacy Phase 1 rows without both title and description are archived, not invented.

## Deferred to Phase 3+

Skill taxonomy, job-skill enrichment, embeddings, pgvector, semantic search, analytics, ranking redesign, LLM features, extra sources, automatic deactivation.

## Files Added

```text
app/ingestion/
app/db/migrate.py
app/db/migrations/001_schema_migrations.sql
app/db/migrations/002_jobs.sql
app/db/migrations/003_ingestion_runs.sql
app/db/repositories/ingestion_runs.py
scripts/migrate.py
tests/fakes.py
tests/unit/test_normalize.py
tests/unit/test_content_hash.py
tests/unit/test_dedupe.py
tests/unit/test_adzuna_adapter.py
tests/unit/test_ingestion_service.py
tests/unit/test_migration_sql.py
tests/integration/conftest.py
tests/integration/test_migrations.py
tests/integration/test_jobs_repository.py
tests/integration/test_ingestion_pipeline.py
docs/PHASE_2_SUMMARY.md
```

## Files Modified

```text
app/core/config.py
app/core/exceptions.py
app/db/repositories/jobs.py
scripts/ingest_adzuna.py
tests/unit/test_ingest_script.py
.env.example
pytest.ini
README.md
```

Ranking modules (`app/services/ranking.py`, skill extractor) were not changed.

## Migration Instructions

```bash
cp .env.example .env    # set DATABASE_URL
python scripts/migrate.py
python scripts/ingest_adzuna.py --query "python developer" --pages 1
```

On a Phase 1 database, `jobs` is renamed to `jobs_legacy` and complete rows are copied into the canonical table.
