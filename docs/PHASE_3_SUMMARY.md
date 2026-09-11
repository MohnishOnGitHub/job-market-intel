# Phase 3 Summary

## Goal

Add a curated technical skill taxonomy, deterministic alias-aware extraction, persisted job-skill enrichment, and SQL skill-demand analytics — without changing the TF-IDF / hybrid ranking formula and without embeddings.

## Taxonomy Design

Source of truth: `data/taxonomy/skills.yml`.

Each skill has `canonical_name`, `category`, `aliases`, and optional `match_strategy` (`boundary` default, `isolated_letter` for `R`).

Size: **160** canonical skills, **252** aliases (including canonical self-aliases), **13** categories.

Precision over recall: no standalone `C` or `Go`; no `cv` → Computer Vision; no bare `lambda` / `glue` / `dash` / `node`.

## Skill Categories

Programming, Databases, Data Engineering, Data Warehousing, Machine Learning, Deep Learning, NLP, Computer Vision, Cloud, MLOps, DevOps, Analytics / BI, Frameworks.

No soft skills.

## Alias Strategy

- Unique aliases across the file; loader fails on collisions.
- Longer aliases are tried first per skill.
- Case-insensitive boundary matching except `R` (isolated letter, case-sensitive).
- Database products do not use `sql` as an alias. `sql` inside `postgresql` / `mysql` / `nosql` / `sqlite` does not count as SQL.

## Extraction Algorithm

1. Load and cache the taxonomy.
2. Search each alias with word-boundary regex (or isolated-letter for `R`).
3. Emit unique `ExtractedSkill(canonical_name, category, matched_alias)` in taxonomy order.

`extract_skills()` still returns `list[str]` for ranking.

## Database Schema

Migration `004_skills.sql`:

- `skills` (`canonical_name` unique, `slug` unique, `category`)
- `skill_aliases` (`normalized_alias` unique)
- `job_skills` PK `(job_id, skill_id)`

## Taxonomy Sync

`python scripts/sync_skills.py` upserts from YAML. Running twice does not insert duplicate skills. Skills present only in the database are **not** deleted.

## Job Enrichment

`SkillEnrichmentService` extracts from the description and **replaces** that job’s `job_skills` rows. Re-running is idempotent. A description change from Python+SQL to Python+Spark drops SQL.

Design choice: jobs are stored first. Ingestion then calls enrichment best-effort after insert/update. Enrichment failure is logged and does not fail the ingest run. `python scripts/enrich_job_skills.py` backfills (`--all`, `--only-missing`, `--job-id`, `--limit`). No queue.

## Matching Integration

`rank_jobs` uses `job.persisted_skills` when the repository loaded `job_skills`; otherwise it extracts from the description. Formula unchanged:

```text
skill_score = matched / job_skills else 0
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

`matched_skills` / `missing_skills` are canonical names.

## Analytics Added

SQL aggregates: active job count, jobs with ≥1 skill, skill counts and `job_share` (skill jobs / filtered active jobs). Optional title and location `ILIKE` filters.

## APIs Added

- `GET /api/v1/skills`
- `GET /api/v1/analytics/skills?title=&location=&limit=`
- `GET /jobs/{id}` includes canonical skills

## Tests

Taxonomy load/validation, alias mapping, false positives, enrichment replace/idempotency, ranking formula + persisted-skill path, SQL migration contents, API fallbacks. PostgreSQL sync/enrichment/analytics tests exist and skip without a database.

## Test Results

```text
91 passed, 12 skipped, 2 warnings
```

Phase 1/2 tests still pass (extraction assertions updated to canonical names).

## Data Quality

No live PostgreSQL/Adzuna enrichment run in this environment. The enrichment CLI prints totals when pointed at a real database; those numbers were not fabricated.

## Known Limitations

- Taxonomy is curated, not exhaustive.
- Title filter is not role classification.
- No historical skill-growth claims.
- Enrichment needs `sync_skills` first or `job_skills` inserts will be empty.

## Deferred to Phase 4+

Embeddings, pgvector, semantic retrieval, hybrid-ranker redesign, market-weighted learning paths, extra sources, automatic deactivation.

## Files Added

```text
data/taxonomy/skills.yml
app/domain/skills.py
app/services/taxonomy.py
app/services/skill_enrichment.py
app/db/migrations/004_skills.sql
app/db/repositories/skills.py
app/db/repositories/analytics.py
app/schemas/skill.py
app/schemas/analytics.py
app/api/routes/skills.py
app/api/routes/analytics.py
scripts/sync_skills.py
scripts/enrich_job_skills.py
tests/unit/test_taxonomy.py
tests/unit/test_skill_aliases.py
tests/unit/test_skill_enrichment.py
tests/integration/test_skills_api.py
tests/integration/test_skills_repository.py
docs/PHASE_3_SUMMARY.md
```

## Files Modified

```text
app/services/skill_extractor.py
app/services/ranking.py
app/schemas/job.py
app/db/repositories/jobs.py
app/ingestion/service.py
app/api/routes/jobs.py
app/main.py
app/core/exceptions.py
scripts/ingest_adzuna.py
requirements.txt
README.md
tests/unit/test_skill_extractor.py
tests/unit/test_ranking.py
tests/unit/test_migration_sql.py
tests/integration/test_matching.py
```

## Migration Instructions

```bash
python scripts/migrate.py
python scripts/sync_skills.py
python scripts/enrich_job_skills.py --only-missing
```
