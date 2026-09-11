# Job Market Intel

An end-to-end résumé-to-job matching application. A user uploads a PDF résumé; the API extracts text and technical skills, compares the résumé to jobs stored in PostgreSQL, and returns a ranked list with matched and missing skills.

This repository is a Phase 1 modular FastAPI MVP. Later phases (ingestion adapters, skill taxonomy, embeddings, evaluation, and market analytics) are specified in `docs/PRD.md` and `docs/DESIGN.md` and are **not implemented yet**.

---

## What it does today

1. Accept a PDF résumé at `POST /upload-resume`.
2. Extract text in memory with PyPDF2.
3. Detect skills with boundary-aware matching against a fixed 21-skill list.
4. Load jobs from PostgreSQL.
5. Score every job with pairwise TF-IDF cosine similarity plus skill overlap.
6. Return jobs sorted by `hybrid_score`.

It does **not** yet ingest jobs automatically, embed documents, search with pgvector, or compute market analytics.

---

## Current architecture

```text
frontend/index.html
        |
        v
   FastAPI (app/main.py)
        |
        +-- services/resume_parser.py
        +-- services/skill_extractor.py
        +-- services/ranking.py
        +-- db/repositories/jobs.py --> PostgreSQL
```

Business logic lives in services. Route handlers do not talk to PostgreSQL directly. Configuration is loaded from environment variables.

---

## Current ranking formula

```text
match_score  = pairwise TF-IDF cosine(resume_text, job_description)
skill_score  = |matched_skills| / |job_skills|   if job_skills else 0
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

Results are sorted by `hybrid_score` descending.

`match_score` fits a new TF-IDF vectorizer on exactly two documents (the résumé and one job). This is the working lexical baseline. It is not corpus-level TF-IDF.

If a job has no extracted skills, `skill_score` is `0`. That demotes those jobs relative to jobs with overlapping skills. This is a documented limitation, not a tuned ranking policy.

These weights are an un-evaluated heuristic. They are not a hiring probability.

---

## Requirements

- Python 3.10+ recommended (`runtime.txt` specifies 3.10.13). Python 3.9 can run the current test suite.
- PostgreSQL
- A `jobs` table (see below)

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

Edit `.env` and set a real `DATABASE_URL`. Do not commit `.env`.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes, for matching | PostgreSQL connection string |
| `APP_ENV` | No (default `development`) | Environment name |
| `LOG_LEVEL` | No (default `INFO`) | Logging level |
| `MAX_UPLOAD_MB` | No (default `5`) | Résumé upload size limit |
| `ADZUNA_APP_ID` | Only for the manual loader | Adzuna API id |
| `ADZUNA_APP_KEY` | Only for the manual loader | Adzuna API key |

### PostgreSQL table

Matching reads:

```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    title TEXT,
    company TEXT,
    location TEXT,
    description TEXT
);
```

The optional Adzuna loader also writes `created_at`. Matching does not use that column. `ON CONFLICT DO NOTHING` in the loader only skips duplicates if a unique constraint exists.

---

## Run the API

```bash
uvicorn app.main:app --reload
```

`uvicorn main:app --reload` also works (compatibility shim).

- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Frontend: http://127.0.0.1:8000/ or open `frontend/index.html`

The app can import and serve `/health` without `DATABASE_URL`. Matching and `/jobs` return HTTP 503 until the database is configured.

---

## Run tests

```bash
pytest
```

Tests do not call Adzuna or a production database. Matching API tests use a mocked job repository.

---

## API

### `GET /health`

```json
{"status": "ok"}
```

### `GET /jobs`

Lists stored jobs. Requires `DATABASE_URL`.

### `POST /upload-resume`

Multipart field: `file` (PDF).

```json
{
  "jobs": [
    {
      "id": 12,
      "title": "Data Analyst",
      "company": "Example Corp",
      "location": "Bengaluru",
      "match_score": 0.61,
      "skill_score": 0.57,
      "hybrid_score": 0.598,
      "skills": ["python", "sql", "pandas"],
      "matched_skills": ["python", "sql"],
      "missing_skills": ["pandas"]
    }
  ]
}
```

`improved_score`, `tfidf_score`, and `projected_score` are not returned.

---

## Manual Adzuna loader

`scripts/ingest_adzuna.py` is a one-shot loader, not a test.

```bash
python scripts/ingest_adzuna.py
```

It requires `DATABASE_URL`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY`. Do not run it unless you intend to write to your local database.

---

## Known limitations

- Skill extraction uses a fixed 21-item list, not a taxonomy with aliases (`postgres` will not become `PostgreSQL`).
- Matching is boundary-aware, so `sql` is not inferred from `PostgreSQL` / `MySQL` / `NoSQL`, and `aws` is not inferred from `laws`.
- Jobs with no extracted skills receive `skill_score = 0`.
- Pairwise TF-IDF is a weak lexical baseline and is scored in Python for every job.
- PDF extraction requires selectable text. Scanned image PDFs fail.
- Ranking has not been evaluated against a labeled relevance dataset.
- The Adzuna loader is not a production ingestion pipeline and does not guarantee deduplication.
- A previous version of this repository committed a plaintext database password. That credential must be rotated outside git. History was not rewritten.

---

## Project documents

| Document | Role |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/DESIGN.md` | Target architecture |
| `docs/PHASE_0_AUDIT.md` | Pre-refactor audit of the MVP |
| `docs/PHASE_1_SUMMARY.md` | What Phase 1 changed |

Roadmap (not yet built): Phase 2 ingestion and history, Phase 3 skill intelligence, Phase 4 semantic retrieval and hybrid ranking, Phase 5 evaluation, Phase 6 market analytics, Phase 7 product polish.

---

## Author

**Mohnish Gurramkonda**

GitHub: [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
