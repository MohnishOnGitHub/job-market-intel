# Phase 6 Summary

## Goal

Turn existing jobs, skill analytics, and matching into a readable market-intelligence product. Ranking formulas were not changed.

## User Experience

Two workflows:

- **Market** (`/`) — overview, skill demand, categories, experience, locations, companies, posting age, shared filters.
- **Résumé match** (`/match.html`) — PDF upload, TF-IDF vs hybrid, optional location/experience, explainable cards, job detail dialog.

A third page, **Evaluation** (`/evaluation.html`), shows measured Phase 5 numbers only.

## Dashboard Architecture

Static HTML/CSS/JS under `frontend/`, served same-origin by FastAPI `StaticFiles`. Chart.js 4.4.1 (CDN) for four horizontal bar charts. No React.

## Analytics Added

SQL endpoints:

- `GET /api/v1/analytics/overview`
- `GET /api/v1/analytics/skills` (existing, plus optional experience filter)
- `GET /api/v1/analytics/categories`
- `GET /api/v1/analytics/experience`
- `GET /api/v1/analytics/locations`
- `GET /api/v1/analytics/companies`
- `GET /api/v1/analytics/freshness`

Also: `GET /api/v1/ranking/status` (no database) and richer `GET /jobs/{id}`.

## Metric Definitions

See `docs/METRICS.md`. Category metric is jobs with ≥1 skill in the category. Freshness uses `posted_at` only. Locations are stored strings.

## Resume Matching UI

Mode switch between `POST /upload-resume` and `POST /api/v1/matches/upload`. Hybrid label comes from the embedding provider: lexical vs semantic wording. Default hashing-v1 is never called semantic.

## Score Explanation

Overall **match score** plus component bars. Weight = 0 → **N/A**. Expandable weights. Not a hiring probability.

## Evaluation Presentation

Static table of the held-out test metrics from Phase 5. Sentence-transformer rows omitted. Disclaimer: directional, not statistically significant.

## API Changes

Additive analytics and job-detail fields. Hybrid response gained `embedding_kind` and `ranking_label`. Scoring functions were not edited.

## Tests

Freshness buckets, ranking labels, analytics API schemas, 503 without database, job-detail schema, ranking status without DB, frontend contract (same-origin, endpoints, terminology), optional Postgres analytics counts.

## Test Results

```text
147 passed, 14 skipped, 2 warnings in 1.69s
```

Skipped tests are PostgreSQL integration tests (no `TEST_DATABASE_URL` and Docker not ready), including the new `test_analytics_repository.py`. They were not counted as passes.

Phase 5 baseline in this environment was 138 passed / 13 skipped. Phase 6 added 9 passing tests and 1 additional Postgres skip.

## Known Limitations

- Market pages 503 without PostgreSQL.
- Category/skill charts need ingested and enriched jobs.
- Location normalization is still string-level.
- No historical trends.
- Browser visual QA depends on a running server and data.

## Deferred Work

Docker, CI, screenshots, larger evaluation, sentence-transformer install, skill-growth time series.

## Files Added

```text
app/services/freshness.py
app/services/ranking_labels.py
app/schemas/status.py
app/api/routes/status.py
frontend/css/app.css
frontend/js/api.js
frontend/js/market.js
frontend/js/match.js
frontend/match.html
frontend/evaluation.html
docs/METRICS.md
docs/PHASE_6_SUMMARY.md
tests/unit/test_freshness.py
tests/unit/test_ranking_labels.py
tests/unit/test_frontend_contract.py
tests/integration/test_analytics_api.py
tests/integration/test_analytics_repository.py
```

## Files Modified

```text
app/db/repositories/analytics.py
app/db/repositories/jobs.py
app/api/routes/analytics.py
app/api/routes/jobs.py
app/api/routes/matching.py
app/api/routes/matches.py
app/schemas/analytics.py
app/schemas/job.py
app/schemas/hybrid_match.py
app/services/matching.py
app/main.py
app/api/routes/health.py
app/api/routes/skills.py
frontend/index.html
README.md
```
