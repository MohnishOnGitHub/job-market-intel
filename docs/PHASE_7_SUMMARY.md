# Phase 7 Summary

## Goal

Validate PostgreSQL + pgvector, run previously skipped tests, measure MiniLM ranking, Dockerize the app, add CI, and package the repository as a portfolio product. No new ranking models or dashboard features were added except bug fixes required for that validation.

## Environment

- Host Python: 3.9.6 (Apple CLT) via `.venv`
- Supported baseline: Python **3.10.13** (`runtime.txt`, Dockerfile, CI)
- PostgreSQL 16.15 (`pgvector/pgvector:pg16`)
- pgvector extension **0.8.6**
- sentence-transformers **3.1.1**, torch **2.8.0**
- Model: `all-MiniLM-L6-v2`, dimension **384**, cosine, `normalize_embeddings=True`

## PostgreSQL / pgvector Validation

`docker compose up -d postgres` on host port 5433. Clean migrate + sync created:

`schema_migrations`, `jobs`, `ingestion_runs`, `skills`, `skill_aliases`, `job_skills`, `job_embeddings`, plus `CREATE EXTENSION vector`.

## Previously Skipped Tests

All 14 previously skipped PostgreSQL tests ran against `TEST_DATABASE_URL`. Two new pgvector matching tests were added.

Fixture isolation bugs exposed by a real `.env` / shared test DB were fixed:

- tests now ignore dotenv when asserting “no database”
- `migrated_db` truncates skills and embeddings, not only jobs

## Live Ingestion

**NOT RUN.** `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` were unset. No fixture counts were substituted.

## Skill Enrichment Results

Local dataset = 32 committed evaluation fixture jobs (not Adzuna):

| Metric | Value |
|---|---|
| Total jobs | 32 |
| Jobs enriched | 32 |
| Jobs with ≥1 skill | 30 |
| Zero-skill jobs | 2 |
| job_skills relationships | 123 |
| Average skills / enriched job | 3.84 |
| Canonical skills synced | 160 |

## Sentence Transformer

Installed locally only (`requirements-semantic.txt`). Not in CI or the default Docker image.

- Model: `all-MiniLM-L6-v2`
- Dimension: 384
- Similarity: cosine of L2-normalized embeddings
- Provider name stored: `sentence-transformers:all-MiniLM-L6-v2`

## Embedding Generation

```text
first --only-missing: seen=32 written=32 unchanged=0 failed=0
second --only-missing: seen=32 written=0 unchanged=32  (idempotent)
```

## pgvector Retrieval

`match_resume_hybrid` on stored MiniLM vectors returned `retrieval = pgvector`, `candidate_count` respected, inactive jobs excluded. Integration test: `tests/integration/test_pgvector_matching.py`.

## End-to-End Matching

Resume `r_de_mid` → MiniLM → pgvector top-20 → DESIGN hybrid. Response: ranking `hybrid`, model `sentence-transformers:all-MiniLM-L6-v2`, label `Semantic + structured hybrid`, component scores and matched skills present. Score is not a hiring probability.

## Semantic Evaluation

Held-out test:

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| skills | 0.467 | 0.589 | 0.586 | 0.778 |
| tfidf | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 | 0.533 | 0.633 | 0.691 | 1.000 |
| MiniLM semantic | 0.667 | 0.811 | 0.833 | 1.000 |
| hybrid + hashing-v1 | 0.600 | 0.933 | 0.852 | 1.000 |
| hybrid + MiniLM | 0.667 | 0.878 | 0.892 | 1.000 |

Validation NDCG@10: MiniLM-only **0.769**, TF-IDF **0.685**, MiniLM hybrid **0.713**, hashing hybrid **0.677**.

MiniLM test ablations: semantic 0.833 → +skills 0.843 → +recency 0.806 → full hybrid 0.892.

## Retrieval Recall

In-memory cosine (fixture ranker):

| Provider | Split | R@20 | R@50 | R@100 |
|---|---|---|---|---|
| hashing-v1 | test | 0.917 | 1.000 | 1.000 |
| MiniLM | test | 1.000 | 1.000 | 1.000 |
| hashing-v1 | validation | 0.820 | 1.000 | 1.000 |
| MiniLM | validation | 0.931 | 1.000 | 1.000 |

Live pgvector (SQL `<=>`, MiniLM, 32 stored vectors):

| Split | R@20 | R@50 | R@100 |
|---|---|---|---|
| test | 1.000 | 1.000 | 1.000 |
| validation | 0.931 | 1.000 | 1.000 |

N=50/100 cover the entire 32-job pool.

## Ranking Recommendation

**KEEP DEFAULTS.**

Evidence: validation still disagrees with test; MiniLM-only beats MiniLM hybrid on validation; Phase 5 grid (recency 0, test NDCG 0.909) remains too small. Production DESIGN weights `0.50 / 0.25 / 0.10 / 0.10 / 0.05` and default `EMBEDDING_PROVIDER=hashing` were not changed. Switching the default provider to MiniLM would be a separate explicit decision (image size).

## Docker

- `docker-compose.yml` — postgres + app
- `Dockerfile` — Python 3.10.13-slim, non-root `appuser`, no secrets, uvicorn, healthcheck
- Built image **job-market-intel-app:latest ≈ 633 MB** (no torch)
- Strategy: keep MiniLM out of the image; document `requirements-semantic.txt` for local eval

## CI

`.github/workflows/ci.yml` — Python 3.10.13, pgvector service, migrate, full pytest. No Adzuna. No MiniLM download.

## Security Review

- `.env` is gitignored; a local compose `.env` was created for this machine and is not tracked
- Compose uses development placeholders only
- No Adzuna keys present
- No raw résumé logging added
- API errors remain generic (`DATABASE_URL is not set.`, `Database is unavailable.`)
- Historical password leak remains in git history and must stay rotated outside git

## Manual Product Validation

HTTP checks against a live server with the 32 fixture jobs and MiniLM:

- `/`, `/match.html`, `/evaluation.html`, `/docs` → 200
- Overview: 32 active jobs, 30 with skills, top skill Python 20/32
- Title filter `Data Engineer` → 7 jobs
- `GET /jobs/1` returned stored fields; `salary_min` null (not invented)
- TF-IDF upload → 200
- Hybrid JSON without prefs → `retrieval=pgvector`, experience/location weights 0 (UI N/A)
- Hybrid with Bengaluru + mid → full DESIGN weights

Browser DevTools / click-through: **not run** (no browser automation). Charts were not visually clicked.

## Screenshots

Not captured. Capture manually after `uvicorn` + populated DB:

1. `/` overview cards
2. `/` skill-demand chart/table
3. `/match.html` after Rank jobs
4. a card with component bars + open weights `<details>`

## Test Results

```text
163 passed, 2 warnings
0 skipped
```

Phase 6 baseline was 147 passed / 14 skipped. All former skips ran. New pgvector tests included.

## Known Limitations

- Live Adzuna ingestion was not run
- Default Docker image cannot do MiniLM
- Dashboard data in this pass is the evaluation fixture, not a live job board
- No screenshot files
- No browser console inspection
- Evaluation remains a small synthetic set

## Final Project Status

**COMPLETE WITH KNOWN LIMITATIONS**

Core Phase 7 flows were actually exercised (Postgres tests, migrate/sync, MiniLM embeddings, pgvector retrieval, e2e match, semantic evaluation, Docker build, CI config). Limitations above are real: no Adzuna live ingest, no visual browser QA, MiniLM not in the default image.

## Files Added

```text
docker-compose.yml
Dockerfile
.dockerignore
docker/postgres/init.sql
.github/workflows/ci.yml
requirements-semantic.txt
scripts/load_evaluation_jobs.py
scripts/evaluate_pgvector.py
tests/integration/test_pgvector_matching.py
docs/PHASE_7_SUMMARY.md
artifacts/evaluation/phase7/test/
artifacts/evaluation/phase7/validation/
artifacts/evaluation/phase7/pgvector-test/
artifacts/evaluation/phase7/pgvector-validation/
```

## Files Modified

```text
requirements.txt
.env.example
.gitignore
tests/conftest.py
tests/integration/conftest.py
tests/unit/test_evaluation_runner.py
tests/unit/test_generate_embeddings_script.py
scripts/migrate.py
scripts/sync_skills.py
scripts/enrich_job_skills.py
scripts/generate_embeddings.py
scripts/ingest_adzuna.py
README.md
docs/EVALUATION.md
frontend/evaluation.html
```
