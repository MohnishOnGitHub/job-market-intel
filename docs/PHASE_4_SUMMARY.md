# Phase 4 Summary

## Goal

Add embedding generation, pgvector candidate retrieval, and an explainable hybrid ranker — without replacing the pairwise TF-IDF baseline and without starting Phase 5 evaluation.

## Architecture

```text
Resume
  → Embedding
  → pgvector candidate retrieval
  → Top-N candidate jobs
  → Structured features
      ├── semantic similarity
      ├── canonical skill overlap
      ├── recency
      ├── location
      └── experience
  → Hybrid ranker
  → Explainable ranked jobs
```

Candidate retrieval and final ranking are separate steps. When stored vectors exist, the ranker does not score every active job in Python.

## Embedding Provider

`EmbeddingProvider` is a protocol (`name`, `dimension`, `embed_documents`, `embed_query`).

| Provider | When | Notes |
|---|---|---|
| `HashingEmbeddingProvider` | Default (`EMBEDDING_PROVIDER=hashing`) | Deterministic hashed tokens. No model download. Lexical, not semantic. |
| `SentenceTransformerProvider` | `EMBEDDING_PROVIDER=sentence-transformers` | Optional extra package. Preferred for real semantic similarity. |

Job text is deterministic:

```text
Title: ...
Company: ...
Location: ...
Description:
...
Skills:
Python, SQL
```

Content hash is SHA-256 of `model_name + text`. Vectors are rewritten only when that hash or the model name changes.

## Database

Migration `005_job_embeddings.sql`:

- `CREATE EXTENSION vector`
- `job_embeddings` PK `(job_id, embedding_model)`
- `embedding vector`, `content_hash`, timestamps

PostgreSQL must provide pgvector. Integration tests start `pgvector/pgvector:pg16` when Docker is available.

## Retrieval

```sql
ORDER BY embedding <=> :resume_embedding
LIMIT :candidate_count
```

Default candidate count is 100. Cosine similarity is `1 - cosine_distance`, clipped to `[0, 1]`.

If no rows exist for the current model, matching falls back to embedding all listed active jobs in memory. That path is labeled `in_memory_fallback` in the API response.

## Hybrid Ranking

```text
hybrid_score =
  w_semantic   * semantic_score +
  w_skill      * skill_score +
  w_experience * experience_score +
  w_recency    * recency_score +
  w_location   * location_score
```

Default weights from DESIGN.md: `0.50 / 0.25 / 0.10 / 0.10 / 0.05`. They are normalized if they do not already sum to 1. They are **not** empirically optimal.

Skill score is unchanged: `matched / job_skills`, else `0`.

Recency: `exp(-age_days / 30)`. Missing `posted_at` → `0.5` (documented neutral fallback; dates are not invented).

Experience: explicit levels only (`internship`, `entry`, `junior`, `mid`, `senior`, `lead`). Used only if the user sends a preference. Missing job level → `0.5`. Prose such as “5 years” is not parsed into years.

Location: used only if the user sends a preference. Exact match `1.0`, substring or hybrid `0.5`, incompatible `0.0`, missing job location `0.5`.

Unused optional signals have their weights set to 0 and the remaining weights are renormalized.

The aggregate score is never labeled as a hiring probability.

## TF-IDF Baseline

`rank_jobs` / `rank_tfidf` and `POST /upload-resume` are unchanged:

```text
hybrid_score = 0.7 * pairwise_tfidf + 0.3 * skill_score
```

Pairwise TF-IDF still fits a vectorizer on exactly two documents.

## APIs

- `POST /api/v1/matches` — JSON résumé text + optional location/experience/limit
- `POST /api/v1/matches/upload` — PDF + optional form fields
- `POST /upload-resume` — TF-IDF baseline, preserved

Response includes `components`, `matched_skills`, `missing_skills`, `embedding_model`, `retrieval`, and the weights used.

## Generation and Ingest

```bash
python scripts/generate_embeddings.py --all|--only-missing|--job-id
```

Ingestion still stores the job first. Enrichment and embedding are best-effort after insert/update. Either failure is logged and does not fail the ingest run.

## Tests

```text
116 passed, 13 skipped, 2 warnings
```

Phase 1–3 tests still pass. The extra skip is the new PostgreSQL embedding round-trip test. All 13 skips are Postgres tests (no `TEST_DATABASE_URL`, Docker daemon not running). Those were not fabricated as passed.

## Known Limitations

- Default hashing vectors are not sentence-transformer semantics.
- Weights are un-evaluated heuristics.
- No Precision@K / NDCG (Phase 5).
- No skill-gap frequency product (Phase 6).
- No frontend redesign.

## Files Added

```text
app/db/migrations/005_job_embeddings.sql
app/db/repositories/embeddings.py
app/services/embedding_provider.py
app/services/embedding_text.py
app/services/hybrid_ranking.py
app/services/job_embeddings.py
app/services/matching.py
app/schemas/hybrid_match.py
app/api/routes/matches.py
scripts/generate_embeddings.py
tests/unit/test_embeddings.py
tests/unit/test_hybrid_ranking.py
tests/unit/test_job_embeddings.py
tests/unit/test_matching_hybrid.py
tests/unit/test_generate_embeddings_script.py
tests/integration/test_matches_api.py
tests/integration/test_embeddings_repository.py
docs/PHASE_4_SUMMARY.md
```

## Files Modified

```text
app/core/config.py
app/core/exceptions.py
app/schemas/job.py
app/services/ranking.py
app/db/repositories/jobs.py
app/ingestion/service.py
app/main.py
scripts/ingest_adzuna.py
.env.example
README.md
tests/fakes.py
tests/unit/test_ranking.py
tests/unit/test_migration_sql.py
tests/unit/test_ingestion_service.py
tests/integration/conftest.py
tests/integration/test_migrations.py
```

## Migration Instructions

```bash
python scripts/migrate.py
python scripts/generate_embeddings.py --only-missing
```
