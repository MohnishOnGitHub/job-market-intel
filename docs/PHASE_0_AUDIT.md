# Phase 0 — Repository Audit

**Project:** Job Market Intel  
**Date:** 2026-09-11  
**Branch:** `main` @ `5d3ae43` (`fix: use hybrid job matching score`)  
**Scope:** Audit and stabilize only. No Phase 1 implementation. No architecture changes.

This document is the Phase 0 deliverable required by `docs/PRD.md` and `docs/DESIGN.md`. It records what the repository actually does today, where that differs from the design documents, and what Phase 1 should change.

---

## 1. Executive summary

The current repository is a small FastAPI MVP, not the modular platform described in the design documents.

A user uploads a PDF résumé. The server extracts text with PyPDF2, finds skills by lowercase substring match against a hardcoded 21-item list, loads every row from a PostgreSQL `jobs` table, scores each job with pairwise TF-IDF cosine similarity plus skill overlap, and returns jobs sorted by `hybrid_score`.

```
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

Results are ordered by `hybrid_score` descending. `improved_score` does **not** exist in the current code. It existed until commit `5d3ae43` and is still mentioned in `README.md`.

There are no automated tests. `test_api.py` is an Adzuna ingestion script, not a test suite. It contains a committed plaintext PostgreSQL password.

The static frontend is out of date relative to the API: it still reads `tfidf_score` and `projected_score`, which the backend no longer returns.

The app cannot be imported or started without `DATABASE_URL`. This workspace has no `.env`, no virtualenv, and the system Python (3.9.6) is missing most runtime dependencies. `runtime.txt` asks for Python 3.10.13.

---

## 2. Method

Inspected:

- every tracked source, frontend, config, and documentation file
- untracked files: `docs/`, `Untitled`, `.DS_Store`
- `git status`, `git branch -vv`, `git log --oneline --decorate -15`
- full history of `main.py`, `index.html`, `skills.py`, `test_api.py`
- scoring commits `a9434f7` → `54fe0bb` → `5d3ae43`

Verified locally:

- `ast.parse` / `py_compile` on `main.py`, `skills.py`, `test_api.py`
- isolated reproduction of current ranking and skill-extraction formulas
- package availability on system Python 3.9.6

Did **not** run `test_api.py`. It is not a test. It calls the live Adzuna API and writes to a local database using committed credentials.

Did **not** start the API. Required packages and `DATABASE_URL` are not present in this workspace.

---

## 3. Repository inventory

### 3.1 Tracked files

| File | Role |
|---|---|
| `main.py` | Entire FastAPI app, DB access, PDF parsing, scoring, and the only HTTP route |
| `skills.py` | Hardcoded skill vocabulary (21 strings) |
| `test_api.py` | Adzuna fetch + PostgreSQL insert script (misnamed) |
| `index.html` | Static upload UI + Chart.js (stale API contract) |
| `requirements.txt` | Unpinned runtime deps (incomplete) |
| `runtime.txt` | `python-3.10.13` |
| `README.md` | Project docs (partially stale) |
| `.gitignore` | `venv/`, `.env`, `__pycache__/`, `*.pyc` |

### 3.2 Untracked files

| File | Role |
|---|---|
| `docs/PRD.md` | Product source of truth (not yet committed) |
| `docs/DESIGN.md` | Technical source of truth (not yet committed) |
| `Untitled` | Leftover prompt that requested the `improved_score` → `hybrid_score` change |
| `.DS_Store` | macOS junk |

### 3.3 Missing relative to DESIGN.md target

No `app/` package, no `api/`, `core/`, `db/`, `schemas/`, `services/`, `ingestion/`, or `domain/` modules. No `tests/`. No `.env.example`. No Docker. No CI. No migrations. No skill taxonomy file. No evaluation dataset. No health/jobs/analytics routes.

---

## 4. Git state

```
branch: main
upstream: origin/main (up to date)
HEAD: 5d3ae43 fix: use hybrid job matching score
remote: https://github.com/MohnishOnGitHub/job-market-intel.git
working tree: clean except untracked docs/, Untitled, .DS_Store
```

Recent commits:

```
5d3ae43 (HEAD -> main, origin/main) fix: use hybrid job matching score
684c765 docs: remove legacy readme
ced51c0 docs: improve project README
54fe0bb final backend fix
5ccacfe add requirements.txt
e26b6f0 fix python version
a9434f7 initial commit
233fe27 Initial setup with API working
```

Scoring history is the most important history in this repo:

| Commit | Ranking behavior |
|---|---|
| `a9434f7` | Corpus-wide TF-IDF (resume + all jobs). `match_score = 0.5 * tfidf + 0.5 * skill` plus a +0.1 bonus. Also returned `tfidf_score`, `projected_score`. Sorted by `match_score`. Top 5 only. Hardcoded DB password in `main.py`. |
| `54fe0bb` | Rewrote matching. Pairwise TF-IDF as `match_score`. Fake `improved_score = min(match_score + 0.15, 1)`. `skill_score = matched / (job_skills + 1)`. **Sorted by `match_score`, not `improved_score`.** Password removed from `main.py`. |
| `5d3ae43` | Current. `skill_score = matched / job_skills` (0 if none). `hybrid_score = 0.7 * match + 0.3 * skill`. **Sorted by `hybrid_score`.** |

`index.html` was last changed in `a9434f7` and still expects that older response shape.

---

## 5. Current architecture

The running system is a single-module monolith.

```
index.html  --POST multipart-->  FastAPI (main.py)
                                      |
                                      +--> PyPDF2 (temp.pdf on disk)
                                      +--> skills.py substring scan
                                      +--> psycopg2 --> PostgreSQL.jobs
                                      +--> sklearn TF-IDF + cosine (per job pair)
                                      +--> hybrid_score sort
                                      |
                                      v
                                 JSON { jobs: [...] }
```

There is no retrieval stage. Every job in the table is scored in Python on every request.

There is no configuration object. `DATABASE_URL` is read at import time via `python-dotenv`. If it is missing, importing `main` raises `Exception("DATABASE_URL not set")`.

There is no repository layer, no schema models, no service layer, and no health endpoint.

`test_api.py` is a separate one-shot ingestion script. It is not wired into the app.

---

## 6. Current functionality

### Working, if environment is configured

- `POST /upload-resume` accepts a multipart file field named `file`
- PDF text extraction with PyPDF2
- Skill extraction against `SKILLS`
- Load all jobs: `SELECT id, title, company, location, description FROM jobs`
- Per-job TF-IDF cosine (`match_score`)
- Per-job skill overlap (`skill_score`)
- Hybrid ranking (`hybrid_score`)
- Return job metadata, job skills, and missing skills
- CORS enabled for all origins
- FastAPI auto docs at `/docs` if the app starts

### Not implemented

- Health, jobs list, filters, résumé-parse-only, skills, or analytics endpoints
- File type/size validation
- Résumé persistence policy / cleanup
- Skill aliases / canonical names
- Job ingestion as an application feature
- Deduplication that actually works
- Embeddings / pgvector
- Experience, location, or recency signals
- Ranking explanations beyond raw component numbers
- Market analytics
- Evaluation framework
- Docker / CI
- Automated tests

### Frontend behavior

`index.html` can upload a PDF to `http://127.0.0.1:8000/upload-resume` and render cards. Because it still reads fields the API no longer returns, the UI will show `undefined` for TF-IDF and “Potential Score”. The bar chart uses `match_score` (TF-IDF only), not `hybrid_score`. Repeat uploads create additional Chart.js instances on the same canvas.

---

## 7. Current data flow

```
1. Browser selects a PDF and calls uploadResume()
2. POST http://127.0.0.1:8000/upload-resume  (multipart field: file)
3. main.upload_resume reads the entire file into memory
4. Bytes are written to ./temp.pdf in the process working directory
5. extract_text("temp.pdf"):
     - PdfReader over every page
     - concatenate extract_text()
     - lowercase the result
6. extract_skills(resume_text):
     - for each string in SKILLS, if skill in text, keep it
7. get_connection() using DATABASE_URL
8. SELECT id, title, company, location, description FROM jobs
9. For each job:
     a. job_text = description.lower()
     b. match_score = TF-IDF cosine(resume_text, job_text)   # new vectorizer per pair
     c. job_skills = extract_skills(job_text)
     d. matched_skills = resume_skills ∩ job_skills          # computed, not returned
     e. missing_skills = job_skills − resume_skills
     f. skill_score = |matched| / |job_skills| else 0
     g. hybrid_score = round(0.7 * match_score + 0.3 * skill_score, 3)
10. Sort by hybrid_score descending
11. Return {"jobs": [...]}   or   {"error": "<exception string>"} with HTTP 200
12. temp.pdf is not deleted
13. Frontend renders cards from the JSON
```

Ingestion (separate, manual):

```
test_api.py
  -> Adzuna /v1/api/jobs/in/search/{1,2,3}
  -> parse title/company/location/description/created
  -> INSERT INTO jobs (...) ON CONFLICT DO NOTHING
```

The insert cannot reliably ignore duplicates unless a unique constraint exists. The README schema does not define one. `created_at` is written by the script but never read by matching.

Résumés are not stored in PostgreSQL. They are stored on disk as `temp.pdf` for the life of the working directory.

---

## 8. Current ranking logic

### 8.1 Fields that exist today

| Field | Meaning | Used to sort? |
|---|---|---|
| `match_score` | Pairwise TF-IDF cosine, rounded to 2 decimals | No |
| `skill_score` | `len(matched_skills) / len(job_skills)`, or `0` if no job skills; rounded to 2 decimals in the response | No (raw value is used inside hybrid before rounding display) |
| `hybrid_score` | `round(0.7 * match_score + 0.3 * skill_score, 3)` | **Yes** |

`improved_score` is absent.

`tfidf_score` and `projected_score` are absent.

`matched_skills` is computed and discarded.

### 8.2 TF-IDF (`calculate_match`)

```python
vectorizer = TfidfVectorizer()
vectors = vectorizer.fit_transform([resume_text, job_text])
score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
return round(score, 2)
```

This fits a new vocabulary on exactly two documents. It is not corpus TF-IDF.

Historical `a9434f7` fitted one vectorizer on `[resume] + all job descriptions` with English stop words, which is a stronger lexical baseline. Commit `54fe0bb` replaced that with pairwise fitting. Isolated reproduction on three sample jobs produced different similarities (example: 0.29 pairwise vs 0.41 corpus for the same pair).

DESIGN.md §13 says to retain TF-IDF/cosine as a reproducible baseline and not silently replace it. The current pairwise function **is** the live baseline. Restoring corpus-level TF-IDF would change ranking semantics.

### 8.3 Hybrid formula

```
hybrid_score = 0.7 * match_score + 0.3 * skill_score
```

Weights do not come from config. There is no experience, recency, location, or semantic component. DESIGN.md §15 example weights are different and are explicitly “not final.” The current 0.7 / 0.3 split is an un-evaluated heuristic and must not be described as optimal.

### 8.4 What actually orders results

```python
results = sorted(results, key=lambda x: x["hybrid_score"], reverse=True)
```

This is confirmed in `main.py` and in commit `5d3ae43`. Before that commit, results were sorted by `match_score` even though `improved_score` was returned.

README.md still says jobs are “ranked by cosine similarity” / “ranked by resume similarity” and documents `improved_score`. That is wrong for HEAD.

The frontend bar chart also ranks visually by `match_score`, so the UI order (from the JSON) and the UI bars can disagree.

---

## 9. `skill_score` investigation

### 9.1 Current formula

```python
skill_score = (
    len(matched_skills) / len(job_skills)
    if job_skills
    else 0
)
```

This matches DESIGN.md §15.2:

```
matched_skills / required_job_skills
```

### 9.2 Empty-skill fallback

If a job has no extracted skills, `skill_score = 0`.

DESIGN.md says the empty case needs a **documented neutral/fallback**, and “Do not arbitrarily reward jobs with missing skill data.”

`0` does not reward those jobs. It also is not neutral: those jobs can only receive `0.7 * match_score`. That systematically demotes jobs whose descriptions do not contain any of the 21 vocabulary strings. The behavior is implemented but not documented.

### 9.3 Previous incorrect formula

Until `5d3ae43`:

```python
skill_score = len(matched_skills) / (len(job_skills) + 1)
```

The `+ 1` permanently understated overlap (4/4 became 0.8). That is fixed.

### 9.4 Extraction correctness

```python
def extract_skills(text):
    found = []
    for skill in SKILLS:
        if skill in text:
            found.append(skill)
    return found
```

This is raw substring matching after `text.lower()`. There are no word boundaries and no aliases.

Confirmed false positives from isolated runs:

| Text | Extracted |
|---|---|
| `experienced with postgresql and mysql` | `sql` |
| `worked on nosql and sqlite` | `sql` |
| `laws and awesome clouds` | `aws` |

`javascript` correctly matches itself. There is no `java` entry, so that particular collision does not occur.

Other extraction limits:

- vocabulary is 21 lowercase strings
- no `postgres` → `PostgreSQL` style normalization
- multi-word skills (`machine learning`, `rest api`) only match that exact phrase
- résumé skills and job skills use the same function, so false positives affect both sides and can inflate `skill_score`

`skill_score` arithmetic is implemented correctly against whatever `extract_skills` returns. The inputs to that arithmetic are not reliable.

---

## 10. `improved_score` vs `hybrid_score`

| Question | Answer |
|---|---|
| Does `improved_score` exist in HEAD? | **No** |
| Does `hybrid_score` exist in HEAD? | **Yes** |
| Do both exist? | **No** |
| What orders results? | **`hybrid_score` descending** |
| What did `improved_score` do? | `round(min(match_score + 0.15, 1), 2)` — a constant boost, not a hybrid |
| Was `improved_score` ever used to sort? | **No.** Sort key was `match_score` |
| Does README still mention `improved_score`? | **Yes** (API note and limitations) |
| Does the frontend use `hybrid_score`? | **No** |

`Untitled` is the prompt that requested the `5d3ae43` change. That change is already on `main`.

---

## 11. Test results

### 11.1 What exists

There is no `tests/` directory. There is no `pytest` dependency. `README.md` calls `test_api.py` “API tests.” That is incorrect.

`test_api.py` is a 3-page Adzuna ingestion script. It:

- reads `APP_ID` / `APP_KEY` from the environment
- connects to `localhost` / `job_market` / `postgres` with a hardcoded password
- inserts rows with `ON CONFLICT DO NOTHING`

### 11.2 Commands run

| Command | Result |
|---|---|
| `git status` | Clean tracked tree; untracked `docs/`, `Untitled`, `.DS_Store` |
| `git branch -vv` | `main` tracking `origin/main`, up to date |
| `git log --oneline --decorate -15` | 8 commits; HEAD `5d3ae43` |
| `python3 -m py_compile main.py skills.py test_api.py` | OK (after sandbox cache permission issue; reran unsandboxed) |
| `ast.parse` on the three Python files | OK |
| `python3 -m pytest --collect-only` | Failed: `No module named pytest` |
| Isolated ranking / skill-extraction script | Completed; results in §8 and §9 |
| `test_api.py` | **Not executed** (live network + DB writes + committed password) |
| `uvicorn main:app` | **Not executed** (no `DATABASE_URL`, no venv, FastAPI not installed on system Python) |

### 11.3 System Python packages (3.9.6)

| Package | Present |
|---|---|
| fastapi | no |
| uvicorn | no |
| psycopg2 | no |
| sklearn | yes |
| dotenv | no |
| PyPDF2 | no |
| multipart | no |
| requests | yes |
| pytest | no |

Syntax is valid. There is no test suite to pass or fail.

---

## 12. Runtime and environment

### How the app is supposed to run (README)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# create .env with DATABASE_URL=postgresql://username:password@localhost:5432/job_market
# create jobs table
uvicorn main:app --reload
# API: http://127.0.0.1:8000
# docs: http://127.0.0.1:8000/docs
# open index.html separately in a browser
```

Deleted `readme.txt` also mentioned `http://127.0.0.1:8000/jobs`, which has never existed as a route in the inspected `main.py` history after the rewrite.

### Actual requirements to run locally

1. Python 3.10.13 according to `runtime.txt`. This machine’s default is Apple CLT Python 3.9.6. No 3.10 binary was found on common paths. No project `venv/` exists.
2. Dependencies from `requirements.txt`:
   - `fastapi`, `uvicorn`, `psycopg2-binary`, `scikit-learn`, `python-dotenv`, `PyPDF2`
3. **Also required but not listed:** `python-multipart` (FastAPI `UploadFile` / `File(...)`).
4. **Also required by `test_api.py` but not listed:** `requests`.
5. A `.env` file with `DATABASE_URL`. None exists in the workspace. `.env.example` does not exist.
6. A reachable PostgreSQL database named in that URL.
7. A `jobs` table. README documents:

   ```sql
   CREATE TABLE jobs (
       id SERIAL PRIMARY KEY,
       title TEXT,
       company TEXT,
       location TEXT,
       description TEXT
   );
   ```

   The ingestion script also writes `created_at`. Matching does not use it.

8. Seed data. There is no sample fixture. The only loader is `test_api.py`, which needs Adzuna `APP_ID` / `APP_KEY`.
9. Frontend: open `index.html` as a static file. It hardcodes `http://127.0.0.1:8000`.

`main.py` cannot be imported without `DATABASE_URL`, so unit-testing helpers in that file is currently blocked.

---

## 13. Technical debt

- All business logic lives in the `/upload-resume` handler (`PRD` NFR-2 violation).
- Import-time database requirement blocks tests and docs generation.
- New DB connection per request; no pooling; connections closed only on the success path after the loop.
- Pairwise TF-IDF is a degraded lexical baseline versus the earlier corpus implementation.
- Skill vocabulary is a Python list, not a taxonomy with aliases and categories.
- Scores every job in Python (`PRD` NFR-6).
- Errors are swallowed and returned as HTTP 200 `{"error": str(e)}`, leaking exception text (`PRD` NFR-5).
- Upload path writes a shared `temp.pdf` with no locking and no deletion (`DESIGN` §11.2).
- Unpinned requirements; missing `python-multipart`.
- `test_api.py` name, purpose, and credentials are all wrong for a portfolio repo.
- README describes ranking, response fields, and `test_api.py` incorrectly.
- Frontend and backend diverged in `54fe0bb` and were never reconciled.
- CORS is `allow_origins=["*"]` plus `allow_credentials=True`.
- No structured logging, request IDs, or timings.
- No typed request/response schemas.
- `index.html` title is “AI Job Matcher”, not Job Market Intel.
- Chart.js is created again on every search.

---

## 14. Confirmed bugs

These are observable from the current code and isolated checks. They are reported, not fixed.

1. **Committed secret.** `test_api.py` contains a plaintext PostgreSQL password. The same password was previously in `main.py` (`a9434f7`) and remains in git history.
2. **`temp.pdf` is never deleted.** Résumé bytes remain on disk. Concurrent uploads overwrite the same path.
3. **Frontend/API contract is broken.** Backend returns `hybrid_score`. Frontend reads `tfidf_score` and `projected_score`.
4. **README is wrong about ranking.** It documents `improved_score` and cosine-only ranking.
5. **`test_api.py` is not a test.** Dedup via `ON CONFLICT DO NOTHING` does nothing useful without a unique constraint, so re-runs can insert duplicates.
6. **Skill substring false positives.** `sql` matches `postgresql` / `mysql` / `nosql` / `sqlite`. `aws` matches inside `laws`.
7. **Upload dependency gap.** `python-multipart` is required for the only endpoint and is absent from `requirements.txt`.
8. **Exceptions do not fail the request.** Clients and the frontend (`data.jobs.forEach`) will throw if the handler returns `{"error": ...}` instead of `{"jobs": ...}`.
9. **No file validation.** Non-PDF uploads, empty PDFs, and large files are not rejected up front. Empty-ish text can produce a zero score or an exception depending on sklearn’s vocabulary.
10. **`matched_skills` is dropped.** The API cannot show “why it matched” the way the PRD explainability story requires.

---

## 15. Differences from PRD.md / DESIGN.md

DESIGN.md §2 described the MVP as “TF-IDF → skill overlap → rank” and said that representation must be verified. The verification result:

| DESIGN / PRD assumption | Actual repository |
|---|---|
| Existing ranker is TF-IDF then skill overlap | True, and they are already combined into `hybrid_score` |
| `improved_score` is the experimental field (README) | Removed; replaced by `hybrid_score` |
| Modular monolith under `app/` | Flat `main.py` + `skills.py` |
| Centralized typed config | Single `os.getenv("DATABASE_URL")` at import |
| `/health` and `/api/v1/...` | Only `POST /upload-resume` |
| Canonical job schema with provenance and timestamps | Five columns used at match time; `created_at` only in the ingest script |
| Taxonomy skill extraction | 21-item substring list |
| TF-IDF baseline independently callable | Function exists but is pairwise, not corpus-level, and is embedded in the route |
| Hybrid signals: semantic, skill, experience, recency, location | Only TF-IDF + skill overlap |
| Do not persist résumés | `temp.pdf` persisted |
| Parameterized SQL / no secrets | Matching query is safe; ingest script has a hardcoded password |
| Tests for ranking and extraction | None |
| `.env.example`, Docker, CI | None |
| Frontend dashboard with analytics | Static `index.html` upload page |
| `test_api.py` is API tests (README) | Adzuna loader |

No code was changed to force the repo to match the design assumptions.

---

## 16. Prioritized issues

### P0 — security / cannot run safely

- Rotate the committed PostgreSQL password. Treat it as public. Remove it from `test_api.py`.
- Do not run `test_api.py` until credentials are env-only.
- Add `.env.example` (no secrets) and document required variables.
- Stop writing durable résumé files, or delete `temp.pdf` after use.
- Record that this workspace cannot start the app today (no `.env`, no venv, missing packages, Python version mismatch).

### P1 — correctness / Phase 1 foundation

- Split `main.py` into `app/` modules without changing ranking math.
- Centralize config; stop requiring `DATABASE_URL` at import just to collect tests.
- Add `python-multipart` and pytest to dependencies.
- Write unit tests for `extract_skills`, `calculate_match`, `skill_score`, `hybrid_score`, and sort order.
- Add `GET /health`.
- Fix README: `hybrid_score` is the sort key; `improved_score` is gone; `test_api.py` is an ingest script.
- Decide whether a **minimal** frontend field update is allowed so the existing page does not show `undefined` (see decisions).
- Replace hardcoded ingest credentials with env vars; do not silently “fix” ranking while doing that.

### P2 — quality, after Phase 1 structure exists

- Word-boundary / alias skill extraction (Phase 3 in the design, not Phase 1).
- Document or change the empty-`job_skills` fallback.
- HTTP error mapping instead of `{"error": str(e)}`.
- Upload type and size limits.
- Return `matched_skills`.
- Unique constraint + real ingest idempotency (Phase 2).
- CORS configuration.
- Pin dependency versions.

### P3 — later phases

- Embeddings, pgvector, hybrid signals beyond TF-IDF + skills (Phase 4).
- Evaluation set and metrics (Phase 5).
- Analytics API and dashboard (Phases 6–7).
- Docker / CI (Phase 7).
- Delete `Untitled` and `.DS_Store`.
- Rename product chrome from “AI Job Matcher”.

---

## 17. Recommended Phase 1 changes

Phase 1 is “Modular Foundation.” Behavior should stay substantially equivalent to this MVP.

Recommended work, in order:

1. Introduce an `app/` package and move existing functions into `core`, `db`, `schemas`, `services`, and `api` routes.
2. Keep these semantics unless a confirmed bug fix is explicitly approved:
   - pairwise TF-IDF `match_score`
   - `skill_score = matched / job_skills` else `0`
   - `hybrid_score = 0.7 * match_score + 0.3 * skill_score`
   - sort by `hybrid_score` descending
   - same `SKILLS` list and substring matching
   - same `POST /upload-resume` response field names (`match_score`, `skill_score`, `hybrid_score`, `skills`, `missing_skills`)
3. Add Pydantic settings / `.env.example` for `DATABASE_URL` (and later match weights as config, defaulting to 0.7 / 0.3).
4. Add a DB session helper that does not crash import when `DATABASE_URL` is missing in test contexts, or inject the connection.
5. Add `GET /health`.
6. Add unit tests that lock current ranking order on a fixture résumé + jobs.
7. Add `python-multipart` and `pytest` to requirements.
8. Rewrite README so it matches HEAD.
9. Quarantine `test_api.py`: rename toward `scripts/`, remove the password, load DB settings from env. Do not expand Adzuna ingestion into Phase 2 scope beyond making it safe.
10. Do **not** add embeddings, pgvector, analytics, or a frontend redesign.

Safe bug fixes that do not change ranking math and are reasonable in Phase 1 if approved:

- delete `temp.pdf` after parsing
- validate PDF content type / size
- map exceptions to HTTP 4xx/5xx without stack traces
- return `matched_skills` as an extra field (additive)

These need an explicit decision because DESIGN.md says not to change behavior unless required.

---

## 18. Files expected to change in Phase 1

| Path | Expected change |
|---|---|
| `main.py` | Shrink to app entrypoint or move to `app/main.py` |
| `skills.py` | Move behind a service; keep the same list |
| `test_api.py` | Credential removal; likely relocate to `scripts/` |
| `requirements.txt` | Add `python-multipart`, `pytest`; optionally pin versions |
| `README.md` | Correct ranking, runbook, structure, and file roles |
| `.gitignore` | Keep `.env`; ignore `.DS_Store` |
| `docs/PRD.md`, `docs/DESIGN.md` | Commit as source of truth (currently untracked) |
| `docs/PHASE_0_AUDIT.md` | This file; already created |

Expected new files (DESIGN.md Phase 1, not all of the final tree):

```
app/main.py
app/api/dependencies.py
app/api/routes/health.py
app/api/routes/resumes.py          # or matching.py wrapping upload-resume
app/core/config.py
app/core/exceptions.py
app/db/session.py
app/schemas/resume.py
app/schemas/match.py
app/services/resume_parser.py
app/services/skill_extractor.py
app/services/ranking.py
.env.example
tests/unit/test_ranking.py
tests/unit/test_skill_extractor.py
tests/unit/test_resume_parser.py
```

`index.html` should stay as-is unless a minimal contract fix is approved. `runtime.txt` can stay unless Phase 1 standardizes the Python version in the README.

Do not create ingestion, embeddings, analytics, taxonomy, evaluation, Docker, or CI files in Phase 1.

---

## 19. Decisions needed

1. **TF-IDF baseline.** Keep current pairwise `TfidfVectorizer()` (preserves live semantics) or restore corpus-level TF-IDF from `a9434f7` (better baseline, changes ranking)? Recommendation: keep pairwise in Phase 1; restore only as an explicit later baseline task.
2. **Empty `job_skills` fallback.** Keep `skill_score = 0` or switch to a documented neutral value (for example omit the skill term and renormalize)? Recommendation: keep `0` in Phase 1.
3. **Frontend.** Leave `index.html` broken until Phase 7, or allow a small field-name patch (`hybrid_score` instead of `tfidf_score` / `projected_score`)? Recommendation: small patch is not a redesign and unblocks demo, but it is your call.
4. **Additive API fields.** May Phase 1 add `matched_skills` without removing existing fields?
5. **Secret rotation.** Confirm the committed Postgres password is rotated and that Adzuna keys were never committed (they are env-only in current `test_api.py`).
6. **Ingest script.** Keep Adzuna as a manual script in Phase 1, or freeze it until Phase 2 source-adapter work?
7. **Untracked docs.** Should `docs/PRD.md`, `docs/DESIGN.md`, and this audit be committed when you next ask for a commit?

---

## 20. Assumptions

- PostgreSQL is the only datastore. No evidence of another database in the repo.
- The live `jobs` table shape is at least `(id, title, company, location, description)` because that is what matching selects. Extra columns such as `created_at` may exist.
- `ON CONFLICT DO NOTHING` in `test_api.py` is ineffective unless a unique constraint was created outside the repo.
- `Untitled` is not product source.
- Isolated ranking numbers in §8–§9 use synthetic text, not production job rows.

No Phase 1 code was written. No commit or push was made.
