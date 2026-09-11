# Job Market Intel

An end-to-end résumé-to-job matching application. A user uploads a PDF résumé; the API extracts text and technical skills, compares the résumé to jobs stored in PostgreSQL, and returns a ranked list with matched and missing skills.

This repository is a Phase 2 modular FastAPI application: matching from Phase 1 plus a reproducible Adzuna ingestion pipeline. Later phases (skill taxonomy, embeddings, evaluation, and market analytics) are specified in `docs/PRD.md` and `docs/DESIGN.md` and are **not implemented yet**.

---

## Implemented now

1. Upload a PDF résumé at `POST /upload-resume`.
2. Extract text in memory and detect skills with boundary-aware matching.
3. Ingest jobs from Adzuna through a source adapter.
4. Normalize, deterministically deduplicate, and upsert into PostgreSQL.
5. Track `first_seen_at` / `last_seen_at` and ingestion-run metrics.
6. Rank stored jobs with pairwise TF-IDF plus skill overlap (`hybrid_score`).

## Roadmap / future work

Not built yet: skill taxonomy and aliases, embeddings / pgvector, semantic retrieval, ranking evaluation, market analytics, Docker Compose app stack, CI.

---

## Architecture

```text
Adzuna adapter
    -> RawJob
    -> validate / normalize
    -> deterministic dedupe
    -> PostgreSQL upsert
    -> ingestion_runs metrics

frontend/index.html
    -> FastAPI
    -> resume parser + skill extractor + ranking
    -> jobs repository (active jobs)
```

---

## Ranking formula

Unchanged from Phase 1:

```text
match_score  = pairwise TF-IDF cosine(resume_text, job_description)
skill_score  = |matched_skills| / |job_skills|   if job_skills else 0
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

Results are sorted by `hybrid_score` descending. These weights are an un-evaluated heuristic, not a hiring probability.

Matching reads `title`, `company`, `COALESCE(location_normalized, location_raw)`, and `description` from **active** jobs. Ranking math is the same.

---

## Requirements

- Python 3.10+ recommended (`runtime.txt` specifies 3.10.13). Python 3.9 can run the current test suite.
- PostgreSQL

---

## Setup

```bash
git clone https://github.com/MohnishOnGitHub/job-market-intel.git
cd job-market-intel

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`. Do not commit `.env`.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes, for matching and ingestion | PostgreSQL connection string |
| `APP_ENV` | No (default `development`) | Environment name |
| `LOG_LEVEL` | No (default `INFO`) | Logging level |
| `MAX_UPLOAD_MB` | No (default `5`) | Résumé upload size limit |
| `ADZUNA_APP_ID` | Yes, for ingestion | Adzuna application id |
| `ADZUNA_APP_KEY` | Yes, for ingestion | Adzuna application key |
| `ADZUNA_COUNTRY` | No (default `in`) | Adzuna country code |

---

## Database setup and migrations

Migrations are numbered SQL files under `app/db/migrations/`, applied by a small runner that records versions in `schema_migrations`. Alembic is not used: the project has no ORM and only two application tables.

```bash
python scripts/migrate.py
# or
python -m app.db.migrate
```

This creates:

- `jobs` — canonical job records
- `ingestion_runs` — per-run metrics
- `schema_migrations` — applied versions

If a Phase 1 `jobs` table exists (no `source` column), it is renamed to `jobs_legacy` and rows with both title and description are copied. Incomplete legacy rows are not invented.

### Job lifecycle fields

| Field | Meaning |
|---|---|
| `first_seen_at` | Set on insert; never overwritten |
| `last_seen_at` | Updated every time the source job is seen |
| `active` | Defaults to true on ingest; repository can set false |
| `content_hash` | SHA-256 of normalized title, company, description, location |
| `source` + `source_job_id` | Primary deterministic identity |
| `source` + `source_url` | Secondary identity when present |

Jobs are **not** marked inactive just because one Adzuna request omitted them. That request is a subset of the market. Automatic deactivation is deferred.

---

## Ingestion

```bash
python scripts/ingest_adzuna.py --query "python developer" --country in --location bangalore --pages 1
```

`python -m scripts.ingest_adzuna` is equivalent.

The CLI is thin. Fetching, normalization, dedupe, upsert, and metrics live in `app/ingestion/`.

### Example workflow

```bash
cp .env.example .env          # set DATABASE_URL and Adzuna keys
python scripts/migrate.py
python scripts/ingest_adzuna.py --query "data engineer" --pages 2
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 and upload a résumé.

### How idempotency works

1. Look up an existing row by `(source, source_job_id)`, else `(source, source_url)`, else `(source, content_hash)` when both identity keys are missing.
2. New identity → insert (`first_seen_at = last_seen_at = now`).
3. Same identity and same `content_hash` → update `last_seen_at` only (unchanged).
4. Same identity and different `content_hash` → update mutable fields, hash, `last_seen_at`, `updated_at`. Preserve `first_seen_at`.

Company + title alone never merges two jobs.

Re-running the same mocked or live snapshot should insert once, then report unchanged rows, not duplicates.

---

## Run the API

```bash
uvicorn app.main:app --reload
```

`uvicorn main:app --reload` also works.

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

---

## Tests

```bash
pytest
```

Unit tests mock Adzuna and do not need PostgreSQL.

Repository and pipeline tests need PostgreSQL. They use `TEST_DATABASE_URL` if set, otherwise they try to start a temporary `postgres:16-alpine` Docker container on port 55432. If neither is available those tests are skipped.

```bash
TEST_DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/job_market_test pytest
```

Do not point tests at a production database.

---

## API

### `GET /health`

```json
{"status": "ok"}
```

### `GET /jobs`

Lists active stored jobs. Requires `DATABASE_URL`.

### `POST /upload-resume`

Multipart field: `file` (PDF). Response includes `match_score`, `skill_score`, `hybrid_score`, `skills`, `matched_skills`, and `missing_skills`.

---

## Known limitations

- Skill extraction uses a fixed 21-item list, not a taxonomy with aliases.
- Jobs with no extracted skills receive `skill_score = 0`.
- Pairwise TF-IDF is scored in Python for every active job.
- Adzuna is the only source. One request is not a complete snapshot of the market.
- Predicted Adzuna salaries are discarded (they are inferred, not posted).
- Automatic job deactivation is not implemented.
- A previous version of this repository committed a plaintext database password. Rotate it outside git.

---

## Project documents

| Document | Role |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/DESIGN.md` | Target architecture |
| `docs/PHASE_0_AUDIT.md` | Pre-refactor audit of the MVP |
| `docs/PHASE_1_SUMMARY.md` | Modular foundation |
| `docs/PHASE_2_SUMMARY.md` | Ingestion pipeline |

---

## Author

**Mohnish Gurramkonda**

GitHub: [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
