# Job Market Intel

A job-market intelligence app: ingest Adzuna postings into PostgreSQL, measure skill demand in SQL, and rank a résumé with explainable lexical or semantic scores.

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) after Postgres is up. The UI is same-origin HTML/CSS/JS — no React.

## Demo

Three pages, two user workflows:

| Page | What a reviewer sees |
|---|---|
| `/` Market | Active jobs, skill demand, categories, experience, locations, companies, posting age |
| `/match.html` | PDF upload, TF-IDF vs hybrid, match score breakdown, matched/missing skills, job detail |
| `/evaluation.html` | Measured v1 benchmark (256 judgments), including MiniLM |

Screenshot-ready states (capture locally; this repo does not ship fabricated images):

1. Market overview cards
2. Skill-demand table and Chart.js bars
3. Résumé match result cards
4. Explainable component bars and expandable weights

Charts use **Chart.js 4.4.1** (jsDelivr). Numbers come from APIs — nothing is hardcoded.

## What it does

1. **Ingest** Adzuna jobs: validate → normalize → content-hash dedupe → PostgreSQL upsert → `ingestion_runs`.
2. **Extract skills** from a 160-skill taxonomy and persist `job_skills`.
3. **Measure demand** with SQL aggregates (title / location / experience filters).
4. **Match a résumé** with a pairwise TF-IDF baseline or a structured hybrid ranker.
5. **Retrieve candidates** with hashing-v1 (default) or MiniLM + pgvector.
6. **Evaluate** rankers on a committed labeled fixture.

The score is a **match score**, not a chance of being hired. The PDF is parsed in memory and is not stored.

## Architecture

```mermaid
flowchart LR
  Adzuna --> Ingest[Normalize and dedupe]
  Ingest --> PG[(PostgreSQL + pgvector)]
  PG --> Enrich[Taxonomy skill enrichment]
  Enrich --> PG
  PG --> Embed[hashing-v1 or MiniLM]
  Embed --> PG

  Resume[Résumé PDF] --> Parse[Parse + extract skills]
  Parse --> Embed
  Embed --> Retrieve[pgvector or in-memory fallback]
  Retrieve --> Hybrid[Structured hybrid ranker]
  Hybrid --> API[FastAPI]

  PG --> Analytics[SQL analytics]
  Analytics --> Dash[Dashboard]
  API --> Dash
```

Terminology (kept exact):

| Term | Meaning |
|---|---|
| **TF-IDF** | Pairwise lexical baseline (`POST /upload-resume`) |
| **hashing-v1** | Lexical hashing retrieval — not semantic |
| **sentence-transformers / MiniLM** | Semantic embeddings (`all-MiniLM-L6-v2`, 384-d) |
| **hybrid** | Structured weighted ranker over similarity, skills, recency, experience, location |

Default Docker/CI ranking uses hashing-v1 so the image stays ~633 MB. MiniLM is an optional local extra (`requirements-semantic.txt`).

## Market intelligence

SQL over `jobs.active = TRUE`. Title and location filters are conservative `ILIKE` contains matches, not a job-family classifier.

| View | Definition |
|---|---|
| Active jobs | Filtered active rows |
| Jobs with skill data | Active jobs with ≥1 `job_skills` row |
| Skill share | Jobs containing the skill / filtered active jobs |
| Categories | Jobs with ≥1 skill in that category (not mention count) |
| Experience | Stored `experience_level` only; blanks stay `unknown` |
| Locations | `COALESCE(location_normalized, location_raw)` strings — not geocoded |
| Freshness | `posted_at` age buckets only — not a forecast |

Full definitions: `docs/METRICS.md`. No growth claims.

## Résumé matching

| Mode | Endpoint | Label in the UI |
|---|---|---|
| Pairwise TF-IDF | `POST /upload-resume` | Pairwise TF-IDF baseline |
| Hashing hybrid | `POST /api/v1/matches` | Lexical vector + structured hybrid |
| MiniLM hybrid | same, `EMBEDDING_PROVIDER=sentence-transformers` | Semantic + structured hybrid |

Each card shows title, company, location, **match score**, ranking method, matched/missing skills, and component bars:

- similarity (lexical or semantic)
- skills
- recency
- experience
- location

If a preference was omitted, that weight is dropped and renormalized. The UI shows **N/A**, not 0. Job detail loads `GET /jobs/{id}` and only displays fields that exist (salary is omitted when unknown).

## Ranking architecture

```text
TF-IDF:   0.7 * pairwise cosine + 0.3 * skill overlap
Hybrid:   0.50 * similarity + 0.25 * skills + 0.10 * experience + 0.10 * recency + 0.05 * location
```

Skill overlap is `matched / job_skills`, else 0. Recency is `exp(-age_days / 30)`; missing `posted_at` → 0.5. Experience and location apply only when the user sends a preference.

These DESIGN weights were **kept** after evaluation. They are not a tuned production optimum.

When stored vectors exist for the active model, hybrid retrieval is **pgvector** (`ORDER BY embedding <=> query`). Otherwise the API reports `in_memory_fallback`.

## Evaluation

v1 fixture: **8 synthetic profiles × 32 jobs = 256 judgments**. Profile-level split (5 validation / 3 test). Relevant = label ≥ 2. Directional benchmark; **not statistically significant**. Labels were not derived from model scores.

Held-out test:

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| Skill overlap | 0.467 | 0.589 | 0.586 | 0.778 |
| Pairwise TF-IDF | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 (lexical) | 0.533 | 0.633 | 0.691 | 1.000 |
| MiniLM semantic | 0.667 | 0.811 | 0.833 | 1.000 |
| Hybrid (DESIGN + hashing-v1) | 0.600 | 0.933 | 0.852 | 1.000 |
| Hybrid (DESIGN + MiniLM) | 0.667 | 0.878 | 0.892 | 1.000 |

Validation NDCG@10: MiniLM-only **0.769**, TF-IDF **0.685**, MiniLM hybrid **0.713**, hashing hybrid **0.677**. Test and validation do not agree on a winner.

Candidate recall (32-job pool; N=50 and N=100 cover every job):

| Retrieval | Split | R@20 |
|---|---|---|
| In-memory hashing-v1 | test | 0.917 |
| In-memory MiniLM | test | 1.000 |
| pgvector MiniLM | test | 1.000 |
| pgvector MiniLM | validation | 0.931 |

See `/evaluation.html` and `docs/EVALUATION.md`.

## Data pipeline

```text
Adzuna adapter
  → RawJob → validate → normalize → SHA-256 content hash
  → upsert on (source, source_job_id) / (source, source_url)
  → best-effort skill enrichment
  → best-effort embedding generation
```

Predicted Adzuna salaries are discarded. A job missing from one page is not auto-deactivated. One query is not the whole market.

```bash
python scripts/migrate.py
python scripts/sync_skills.py
python scripts/ingest_adzuna.py --query "data engineer" --pages 2
python scripts/enrich_job_skills.py --only-missing
python scripts/generate_embeddings.py --only-missing
```

Without Adzuna keys, load the committed synthetic fixture for a working dashboard:

```bash
python scripts/load_evaluation_jobs.py
python scripts/enrich_job_skills.py --all
```

## Skill intelligence

`data/taxonomy/skills.yml` is the source of truth: **160** canonical technical skills, **252** aliases, **13** categories (Programming, Data Engineering, Machine Learning, Cloud, MLOps, Analytics / BI, …). No soft skills.

Extraction is deterministic and alias-aware. Precision aliases: no standalone `C` / `Go`; `sql` is not an alias of PostgreSQL. `sql` inside `postgresql` does not count as SQL.

## API

Interactive docs: `/docs`.

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/jobs` | Active job list |
| GET | `/jobs/{id}` | Detail; nulls stay null |
| GET | `/api/v1/skills` | Taxonomy (YAML fallback if DB is down) |
| GET | `/api/v1/ranking/status` | Provider + hybrid label; no DB |
| GET | `/api/v1/analytics/overview` | Counts + top skill + latest ingest |
| GET | `/api/v1/analytics/skills` | Demand table |
| GET | `/api/v1/analytics/categories` | Jobs with ≥1 skill in category |
| GET | `/api/v1/analytics/experience` | Stored levels |
| GET | `/api/v1/analytics/locations` | String locations |
| GET | `/api/v1/analytics/companies` | Active job counts |
| GET | `/api/v1/analytics/freshness` | `posted_at` buckets |
| POST | `/upload-resume` | TF-IDF baseline |
| POST | `/api/v1/matches` | Hybrid from résumé text |
| POST | `/api/v1/matches/upload` | Hybrid from PDF |

## Local setup

Supported Python: **3.10+** (`runtime.txt` = 3.10.13). Tests also run on 3.9.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
python scripts/migrate.py
python scripts/sync_skills.py
python scripts/load_evaluation_jobs.py
python scripts/enrich_job_skills.py --all
uvicorn app.main:app --reload
```

Compose defaults (development placeholders only):

```text
DATABASE_URL=postgresql://jmi:jmi_dev_only@localhost:5433/job_market
TEST_DATABASE_URL=postgresql://jmi:jmi_dev_only@localhost:5433/job_market_test
```

Optional MiniLM (large download; not in Docker/CI):

```bash
pip install -r requirements-semantic.txt
# in .env: EMBEDDING_PROVIDER=sentence-transformers
python scripts/generate_embeddings.py --only-missing
```

## Docker

```bash
docker compose up --build
docker compose exec app python scripts/migrate.py
docker compose exec app python scripts/sync_skills.py
```

- App: Python **3.10.13-slim**, non-root user, no secrets, `/health` check (~633 MB)
- Postgres: `pgvector/pgvector:pg16` on host **5433**
- Default ranking: hashing-v1. Torch is not installed in the image.

## Testing

```bash
export TEST_DATABASE_URL=postgresql://jmi:jmi_dev_only@localhost:5433/job_market_test
pytest
```

Latest local run with Postgres: **163 passed, 0 skipped**. Without `TEST_DATABASE_URL` or Docker, PostgreSQL tests skip and are not counted as passes.

```bash
python scripts/evaluate_ranking.py --split test
python scripts/evaluate_pgvector.py --split test   # needs stored vectors
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) installs dependencies, starts `pgvector/pgvector:pg16`, migrates, and runs the full suite. Adzuna keys and MiniLM downloads are not required.

## Limitations

- hashing-v1 is lexical, not semantic
- MiniLM is optional and not in the default image
- Hybrid DESIGN weights were measured and **kept**; they are not a production optimum
- Location strings are not geocoded
- Experience is not inferred from job prose
- No historical skill-growth or forecast claims
- One Adzuna query is not the whole market
- Evaluation is a small synthetic set (8 profiles)
- A past commit leaked a database password in git history; rotate it outside git

## Future work

Historical trends, a larger labeled set, an optional fat image with MiniLM. Not in this project: LLM ranking, new job boards, Kafka, Redis, Celery, Kubernetes.

## Documents

| Document | Role |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/DESIGN.md` | Target architecture |
| `docs/METRICS.md` | Dashboard metric definitions |
| `docs/EVALUATION.md` | Ranking evaluation report |
| `docs/EVALUATION_GUIDE.md` | Labeling rubric |
| `docs/PHASE_7_SUMMARY.md` | Validation, Docker, CI |

## Author

**Mohnish Gurramkonda** · [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
