# Job Market Intel

An end-to-end résumé-to-job matching application. A user uploads a PDF résumé; the API extracts text and technical skills, compares the résumé to jobs stored in PostgreSQL, and returns a ranked list with matched and missing skills.

This repository is a Phase 5 modular FastAPI application: matching, Adzuna ingestion, a curated skill taxonomy, job-skill enrichment, skill-demand analytics, embedding generation, pgvector candidate retrieval, an explainable hybrid ranker, and an offline ranking evaluation fixture.

---

## Implemented now

1. Upload a PDF résumé at `POST /upload-resume` for the TF-IDF lexical baseline.
2. Extract canonical skills from a curated taxonomy (`data/taxonomy/skills.yml`).
3. Ingest jobs from Adzuna, normalize, deduplicate, and upsert into PostgreSQL.
4. Persist job-skill relationships and compute skill-demand shares in SQL.
5. Generate job embeddings and retrieve a candidate set with pgvector.
6. Rerank candidates with a hybrid score and per-component explanation (`POST /api/v1/matches`).
7. Evaluate rankers offline on a committed labeled fixture (`python scripts/evaluate_ranking.py`).

## Roadmap / future work

Not built yet: historical trend claims, skill-gap frequency product, Docker Compose app stack, CI.

---

## Architecture

```text
Adzuna adapter
    -> RawJob -> normalize -> dedupe -> jobs upsert
    -> best-effort skill enrichment -> job_skills
    -> best-effort embedding generation -> job_embeddings

Resume
    -> embedding
    -> pgvector candidate retrieval (or in-memory fallback)
    -> structured features (semantic, skills, recency, location, experience)
    -> hybrid ranker
    -> explainable ranked jobs

POST /upload-resume still uses the independent TF-IDF baseline.
```

Matching uses persisted `job_skills` when present and falls back to live extraction for jobs that have not been enriched.

---

## Ranking

Two rankers are available. Neither score is a hiring probability.

### TF-IDF baseline (`rank_tfidf` / `POST /upload-resume`)

Unchanged from Phase 1:

```text
match_score  = pairwise TF-IDF cosine(resume_text, job_description)
skill_score  = |matched_skills| / |job_skills|   if job_skills else 0
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

Pairwise TF-IDF fits a new vectorizer on exactly two documents. This is intentional and is not corpus-level TF-IDF.

### Hybrid ranker (`POST /api/v1/matches`)

```text
hybrid_score =
  w_semantic   * semantic_score +
  w_skill      * skill_score +
  w_experience * experience_score +
  w_recency    * recency_score +
  w_location   * location_score
```

Default weights (from DESIGN.md, not empirically tuned): `0.50 / 0.25 / 0.10 / 0.10 / 0.05`. Weights are normalized to sum to 1. Location and experience are used only when the request includes a preference; those weights are then dropped and the rest are renormalized.

| Signal | Range | Rule |
|---|---|---|
| embedding (`semantic` field) | 0–1 | Cosine of résumé and job vectors, clipped to `[0, 1]`. With the default `hashing-v1` provider this is **lexical hashing**, not sentence-transformer semantics. |
| skills | 0–1 | `matched / job_skills`, else `0` |
| recency | 0–1 | `exp(-age_days / 30)`; missing `posted_at` is `0.5` |
| experience | 0–1 | Explicit levels only: internship → lead; missing job level is `0.5` |
| location | 0–1 | Exact `1.0`, substring/hybrid `0.5`, mismatch `0.0`; missing job location is `0.5` |

If stored vectors exist for the current model, candidates are retrieved with pgvector (`ORDER BY embedding <=> query LIMIT N`). The ranker then scores only that candidate set. If no vectors exist, all active jobs are scored in memory with the same embedding provider. That fallback is documented and is not used once embeddings are stored.

---

## Requirements

- Python 3.10+ recommended (`runtime.txt` specifies 3.10.13). Python 3.9 can run the current test suite.
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension

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
| `EMBEDDING_PROVIDER` | No (default `hashing`) | `hashing` or `sentence-transformers` |
| `EMBEDDING_MODEL` | No (default `all-MiniLM-L6-v2`) | Model name when using sentence-transformers |
| `EMBEDDING_DIMENSION` | No (default `256`) | Hashing-vector size |
| `CANDIDATE_COUNT` | No (default `100`) | pgvector retrieval depth |
| `RECENCY_TAU_DAYS` | No (default `30`) | Recency decay constant |
| `RANK_WEIGHT_*` | No | Hybrid weights; normalized if they do not sum to 1 |

---

## Database setup and migrations

Migrations are numbered SQL files under `app/db/migrations/`, applied by a small runner that records versions in `schema_migrations`. Alembic is not used: the project has no ORM.

```bash
python scripts/migrate.py
# or
python -m app.db.migrate
```

This creates:

- `jobs` — canonical job records
- `ingestion_runs` — per-run metrics
- `skills`, `skill_aliases`, `job_skills` — taxonomy and enrichment
- `job_embeddings` — one vector per job and embedding model
- `schema_migrations` — applied versions

Migration `005_job_embeddings.sql` runs `CREATE EXTENSION vector`. PostgreSQL must have pgvector installed. Test containers use `pgvector/pgvector:pg16`.

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
python scripts/sync_skills.py
python scripts/ingest_adzuna.py --query "data engineer" --pages 2
python scripts/enrich_job_skills.py --only-missing
python scripts/generate_embeddings.py --only-missing
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

## Skill intelligence

The taxonomy file `data/taxonomy/skills.yml` is the source of truth (~160 technical skills, aliases, categories). Extraction is deterministic: boundary-aware, alias-aware, canonicalized. Short tokens such as `R` use an isolated-letter rule. `Go` and `C` are not matched as English words.

```bash
python scripts/sync_skills.py              # upsert skills/aliases; does not delete extras
python scripts/enrich_job_skills.py --all  # replace job_skills per job
python scripts/enrich_job_skills.py --only-missing --limit 100
python scripts/enrich_job_skills.py --job-id 12
```

Ingestion stores jobs first, then attempts enrichment, then embeddings. A skill-enrichment or embedding failure does not fail the ingest run. Re-enrichment replaces stale links (Python+SQL → Python+Spark drops SQL). Embeddings are regenerated when the embedding text hash or model name changes.

```bash
python scripts/generate_embeddings.py --all
python scripts/generate_embeddings.py --only-missing
python scripts/generate_embeddings.py --job-id 12
```

The default embedding provider is deterministic hashed n-grams (`hashing-v1`). That keeps tests and local setup free of model downloads. It is lexical hashing retrieval, not semantic retrieval. For sentence-transformer embeddings:

```bash
pip install sentence-transformers
# EMBEDDING_PROVIDER=sentence-transformers
```

Analytics use SQL aggregates, not a full table load in Python:

- `GET /api/v1/skills`
- `GET /api/v1/analytics/skills?title=Data%20Engineer&location=Bengaluru&limit=25`

Title and location filters are conservative `ILIKE` matches, not a job-family classifier.

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

Multipart field: `file` (PDF). TF-IDF lexical baseline. Response includes `match_score`, `skill_score`, `hybrid_score`, `skills`, `matched_skills`, and `missing_skills` as **canonical** names.

### `POST /api/v1/matches`

JSON hybrid ranking. Example body:

```json
{
  "resume_text": "python sql spark",
  "preferred_location": "Bengaluru",
  "preferred_experience": "mid",
  "limit": 20
}
```

Response includes `hybrid_score`, `components` (`semantic`, `skills`, `experience`, `recency`, `location`), matched/missing canonical skills, the embedding model, retrieval mode (`pgvector` or `in_memory_fallback`), and the weights actually used. `POST /api/v1/matches/upload` accepts a PDF plus the same optional form fields.

### `GET /api/v1/skills`

Taxonomy list. Falls back to the YAML file if the database is empty or unavailable.

### `GET /api/v1/analytics/skills`

Skill demand among active jobs. Optional `title`, `location`, `limit`. Requires PostgreSQL.

### `GET /jobs/{id}`

Job detail with canonical skills when available.

---

## Ranking evaluation

Offline fixture: 8 synthetic profiles × 32 jobs = **256** independent labels (`data/evaluation/v1`). Profile-level split (5 validation / 3 test). Relevance ≥ 2 counts as relevant. Details: `docs/EVALUATION.md`.

```bash
python scripts/evaluate_ranking.py --dataset data/evaluation/v1 --split test
```

On the v1 **held-out test** set (3 profiles), DESIGN-weight hybrid ranking with hashing-v1 embeddings reached NDCG@10 **0.852** versus **0.757** for pairwise TF-IDF, **0.691** for lexical hashing-v1, and **0.586** for skill overlap. On the **validation** set (5 profiles), pairwise TF-IDF was ahead (NDCG@10 **0.685** vs hybrid **0.677**). That disagreement is why these numbers are directional, not a claim of statistically significant improvement.

sentence-transformer semantic evaluation was **not run** (package not installed). Live pgvector retrieval was **not run**. hashing-v1 is lexical hashing retrieval, not semantic retrieval. Production weights were not changed.

---

## Known limitations

- Default hashing-v1 vectors are lexical hashing, not sentence-transformer semantics.
- Hybrid DESIGN weights remain an un-evaluated production default. The v1 benchmark is too small to justify changing them.
- Jobs with no extracted skills receive `skill_score = 0`.
- Jobs with no extracted skills receive `skill_score = 0`.
- Experience uses explicit normalized levels only; years are not inferred from prose.
- Location and experience affect ranking only when the user supplies a preference.
- Missing `posted_at` uses a documented recency fallback of `0.5`.
- Title/location analytics filters are substring `ILIKE`, not role classification.
- Trend / “fastest growing” metrics are not claimed; history is still thin.
- Adzuna is the only source. One request is not a complete snapshot of the market.
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
| `docs/PHASE_3_SUMMARY.md` | Skill taxonomy and enrichment |
| `docs/PHASE_4_SUMMARY.md` | Embeddings, retrieval, hybrid ranking |
| `docs/EVALUATION_GUIDE.md` | Relevance label definitions |
| `docs/EVALUATION.md` | v1 ranking evaluation report |
| `docs/PHASE_5_SUMMARY.md` | Offline evaluation framework |

---

## Author

**Mohnish Gurramkonda**

GitHub: [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
