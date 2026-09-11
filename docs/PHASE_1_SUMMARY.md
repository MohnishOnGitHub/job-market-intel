# Phase 1 Summary

## What Changed

Phase 1 refactored the monolithic FastAPI MVP into a modular package without changing the ranking formula.

- Application code now lives under `app/` (`api`, `core`, `db`, `schemas`, `services`).
- Configuration is centralized and read from environment variables.
- PostgreSQL access moved into a small repository layer.
- PDF parsing runs in memory and no longer writes `temp.pdf`.
- Skill extraction still uses the original 21-skill list, but matching is boundary-aware.
- Ranking is an independently testable service.
- `GET /health` and `GET /jobs` were added. `POST /upload-resume` remains the matching endpoint.
- `test_api.py` was renamed to `scripts/ingest_adzuna.py` and made environment-driven.
- `index.html` moved to `frontend/` and now displays `hybrid_score`.
- A real pytest suite was added.
- README, `.env.example`, and `.gitignore` were updated.

## Final Repository Structure

```text
job-market-intel/
├── app/
│   ├── main.py
│   ├── api/routes/
│   │   ├── health.py
│   │   ├── jobs.py
│   │   └── matching.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── database.py
│   │   └── repositories/jobs.py
│   ├── schemas/
│   │   ├── job.py
│   │   └── match.py
│   └── services/
│       ├── resume_parser.py
│       ├── skill_extractor.py
│       └── ranking.py
├── frontend/index.html
├── scripts/ingest_adzuna.py
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── PRD.md
│   ├── DESIGN.md
│   ├── PHASE_0_AUDIT.md
│   └── PHASE_1_SUMMARY.md
├── .env.example
├── main.py
├── pytest.ini
├── requirements.txt
├── runtime.txt
└── README.md
```

`uvicorn app.main:app --reload` is the preferred start command. `uvicorn main:app --reload` still works.

## Ranking Behavior

Preserved:

```text
match_score  = pairwise TF-IDF cosine(resume, job)
skill_score  = matched_skills / job_skills   if job_skills else 0
hybrid_score = 0.7 * match_score + 0.3 * skill_score
sort         = hybrid_score descending
```

Pairwise TF-IDF was not restored to corpus-level TF-IDF.

Allowed Phase 1 changes that can affect scores:

- Boundary-aware skill matching. `sql` is no longer extracted from `postgresql` / `mysql` / `nosql` / `sqlite`. `aws` is no longer extracted from `laws`.
- `matched_skills` is now returned.
- `missing_skills` / skill lists are ordered by the vocabulary list instead of a set hash order.

`skill_score = 0` when a job has no extracted skills remains in place. This is a known limitation: those jobs can only receive `0.7 * match_score`.

Weights were not tuned.

## Security Fixes

- Removed the hardcoded PostgreSQL password from source by deleting `test_api.py`.
- The replacement loader uses `DATABASE_URL` from the environment.
- Database exceptions return a generic 503 and do not include connection strings.
- `.env` is gitignored. `.env.example` contains placeholders only.
- Résumé bytes are parsed in memory. The shared `temp.pdf` path is gone.
- Upload type and size are validated.
- API errors no longer return HTTP 200 with `{"error": "<exception>"}`.

The previously committed password is still in git history. It must be rotated outside this repository. History was not rewritten.

## Tests Added

Unit:

- skill extraction
- false-positive prevention (`postgresql`, `mysql`, `nosql`, `sqlite`, `laws`)
- skill overlap
- hybrid-score calculation
- ranking order
- no-job-skills behavior
- PDF validation and in-memory extraction
- ingest script environment-only configuration

Integration:

- `GET /health` without a database
- `POST /upload-resume` with a mocked job repository
- rejected non-PDF upload
- `503` when `DATABASE_URL` is missing
- `GET /jobs` with a mocked repository

## Test Results

Isolated environment: `.venv` on system Python 3.9.6.

```text
.venv/bin/python -c "from app.main import app, create_app; print('import_ok', app.title)"
# import_ok Job Market Intel

.venv/bin/python -m py_compile app/main.py app/core/config.py \
  app/services/ranking.py app/services/skill_extractor.py \
  app/services/resume_parser.py scripts/ingest_adzuna.py main.py
# OK

.venv/bin/pytest -v
# 39 passed, 2 warnings in 0.13s
```

Warnings:

- PyPDF2 deprecation (still the current project dependency)
- urllib3 LibreSSL notice on macOS system Python

Smoke checks against a running app with no `DATABASE_URL`:

- `GET /health` → 200 `{"status":"ok"}`
- `GET /jobs` → 503 `{"detail":"DATABASE_URL is not set."}`
- `GET /` → 200 frontend
- `POST /upload-resume` with a `.txt` file → 400 unsupported file type

Not run:

- `scripts/ingest_adzuna.py` against a live API or database (intentionally)
- browser click-through of the upload UI (no browser automation available)
- matching against a real PostgreSQL instance

## API Changes

| Endpoint | Change |
|---|---|
| `GET /health` | Added |
| `GET /jobs` | Added (list id/title/company/location) |
| `POST /upload-resume` | Same path and multipart field `file` |

Matching response still includes `id`, `title`, `company`, `location`, `match_score`, `skill_score`, `hybrid_score`, `skills`, `missing_skills`.

Added:

- `matched_skills`

Removed from error responses:

- HTTP 200 `{"error": "..."}` — errors now use HTTP 4xx/5xx `{"detail": "..."}`

## Known Limitations

- Pairwise TF-IDF remains a weak lexical baseline.
- Every job is still scored in Python.
- Skill vocabulary is still 21 strings with no aliases.
- Empty job-skill lists still produce `skill_score = 0`.
- No unique constraint, so the Adzuna loader may insert duplicates.
- No Docker, CI, embeddings, analytics, or evaluation framework.
- Python 3.10.13 is specified in `runtime.txt`; this Phase 1 test run used 3.9.6 because no 3.10 binary was available on the machine.

## Deferred to Phase 2+

- Source adapters, normalization, deduplication, first/last seen
- Skill taxonomy and aliases
- Embeddings, pgvector, semantic retrieval
- Experience / recency / location ranking signals
- Evaluation metrics and labeled data
- Market analytics and dashboard redesign
- Docker / CI
- Credential rotation and git-history cleanup (external operations)

## Files Added

```text
app/__init__.py
app/main.py
app/api/__init__.py
app/api/routes/__init__.py
app/api/routes/health.py
app/api/routes/jobs.py
app/api/routes/matching.py
app/core/__init__.py
app/core/config.py
app/core/exceptions.py
app/db/__init__.py
app/db/database.py
app/db/repositories/__init__.py
app/db/repositories/jobs.py
app/schemas/__init__.py
app/schemas/job.py
app/schemas/match.py
app/services/__init__.py
app/services/resume_parser.py
app/services/skill_extractor.py
app/services/ranking.py
frontend/index.html
scripts/__init__.py
scripts/ingest_adzuna.py
tests/conftest.py
tests/unit/test_skill_extractor.py
tests/unit/test_ranking.py
tests/unit/test_resume_parser.py
tests/unit/test_ingest_script.py
tests/integration/test_health.py
tests/integration/test_matching.py
.env.example
pytest.ini
docs/PHASE_1_SUMMARY.md
```

## Files Modified

```text
main.py
requirements.txt
README.md
.gitignore
```

`docs/PRD.md`, `docs/DESIGN.md`, and `docs/PHASE_0_AUDIT.md` were left as source-of-truth documents.

## Files Removed/Moved

| Old path | New path |
|---|---|
| `skills.py` | `app/services/skill_extractor.py` |
| `test_api.py` | `scripts/ingest_adzuna.py` |
| `index.html` | `frontend/index.html` |

`Untitled` is an leftover prompt file and was not deleted.
