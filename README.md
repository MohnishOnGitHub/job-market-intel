# Job Market Intel

Ingest job postings, measure skill demand in SQL, and rank a résumé with explainable lexical and semantic scores.

## Demo

The UI is screenshot-ready at:

1. `http://127.0.0.1:8000/` — market overview cards
2. same page, Skill demand — table + Chart.js bars
3. `/match.html` — ranked match cards
4. a result card — component bars and expandable weights

This repository does not include generated screenshot files. Use a local database (evaluation fixtures or Adzuna) so the numbers are real.

## What it does

- **Market intelligence** — active jobs, skill demand, categories, experience mix, locations, companies, posting age
- **Résumé matching** — pairwise TF-IDF baseline and a structured hybrid ranker
- **Evaluation** — 256 labeled judgments, including measured MiniLM results

## Architecture

```mermaid
flowchart LR
  Adzuna --> Ingest[Normalize and dedupe]
  Ingest --> PG[(PostgreSQL)]
  PG --> Enrich[Skill enrichment]
  Enrich --> PG
  PG --> MiniLM[MiniLM embeddings]
  MiniLM --> Vectors[pgvector]

  Resume[Résumé PDF] --> Parse[Parse and extract skills]
  Parse --> MiniLM
  MiniLM --> Retrieve[pgvector retrieval]
  Retrieve --> Hybrid[Structured hybrid ranker]
  Hybrid --> API[FastAPI]

  PG --> Analytics[SQL analytics]
  Analytics --> Dash[Dashboard]
  API --> Dash
```

hashing-v1 is **lexical hashing retrieval**. `all-MiniLM-L6-v2` is **semantic embeddings**. Hybrid is a **structured weighted ranker**. TF-IDF is the **pairwise lexical baseline**.

## Market intelligence

SQL aggregates over `active = TRUE` jobs. Filters are conservative `ILIKE` contains matches.

Definitions: `docs/METRICS.md`. No growth or forecast claims. Locations are stored strings, not geocodes.

## Résumé matching

| Mode | Endpoint | What it is |
|---|---|---|
| Pairwise TF-IDF baseline | `POST /upload-resume` | Two-document TF-IDF + skill overlap |
| Lexical vector + structured hybrid | `POST /api/v1/matches` with hashing-v1 | Default in Docker/CI |
| Semantic + structured hybrid | same API with MiniLM | Optional extra |

The overall value is a **match score**, not a hiring probability. Unused location or experience preferences display as **N/A**. The PDF is parsed in memory and not stored.

## Ranking architecture

```text
TF-IDF:   0.7 * pairwise cosine + 0.3 * skill overlap
Hybrid:   0.50 * similarity + 0.25 * skills + 0.10 * experience + 0.10 * recency + 0.05 * location
```

DESIGN hybrid weights renormalize when a preference is omitted. They are defaults, not a tuned production optimum.

## Evaluation

v1 fixture: **8 synthetic profiles × 32 jobs = 256 judgments**. Directional; not statistically significant.

Held-out test (3 profiles):

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| Skill overlap | 0.467 | 0.589 | 0.586 | 0.778 |
| Pairwise TF-IDF | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 (lexical) | 0.533 | 0.633 | 0.691 | 1.000 |
| MiniLM semantic | 0.667 | 0.811 | 0.833 | 1.000 |
| Hybrid (DESIGN + hashing-v1) | 0.600 | 0.933 | 0.852 | 1.000 |
| Hybrid (DESIGN + MiniLM) | 0.667 | 0.878 | 0.892 | 1.000 |

Validation NDCG@10: MiniLM-only 0.769, TF-IDF 0.685, MiniLM hybrid 0.713, hashing hybrid 0.677. Production weights were not changed. See `/evaluation.html` and `docs/EVALUATION.md`.

## Data engineering

Adzuna adapter → validate → normalize → content-hash dedupe → PostgreSQL upsert → `ingestion_runs`. Predicted Adzuna salaries are discarded. Jobs are not auto-deactivated when missing from one page.

```bash
python scripts/migrate.py
python scripts/sync_skills.py
python scripts/ingest_adzuna.py --query "data engineer" --pages 2
python scripts/enrich_job_skills.py --only-missing
python scripts/generate_embeddings.py --only-missing
```

Without Adzuna keys, load the synthetic fixture for a local demo:

```bash
python scripts/load_evaluation_jobs.py
python scripts/enrich_job_skills.py --all
```

## Skill intelligence

`data/taxonomy/skills.yml` is the source of truth: **160** canonical technical skills, 252 aliases, 13 categories. Extraction is deterministic. `sql` inside `postgresql` does not count as SQL.

## API

Documented at `/docs`. Implemented endpoints include `/health`, `/jobs`, `/jobs/{id}`, `/api/v1/skills`, `/api/v1/ranking/status`, `/api/v1/analytics/*`, `POST /upload-resume`, `POST /api/v1/matches`.

## Local setup

Supported Python: **3.10+** (`runtime.txt` = 3.10.13). Unit tests also run on 3.9.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
python scripts/migrate.py
python scripts/sync_skills.py
uvicorn app.main:app --reload
```

Optional MiniLM (large download; not in the Docker image):

```bash
pip install -r requirements-semantic.txt
# EMBEDDING_PROVIDER=sentence-transformers
```

## Docker

```bash
docker compose up --build
docker compose exec app python scripts/migrate.py
docker compose exec app python scripts/sync_skills.py
```

The app image is a slim **Python 3.10.13** FastAPI container (~600 MB). It does **not** install torch / sentence-transformers. Default ranking is hashing-v1. Compose Postgres is `pgvector/pgvector:pg16` on host port **5433** with development placeholders `jmi` / `jmi_dev_only`.

## Testing

```bash
export TEST_DATABASE_URL=postgresql://jmi:jmi_dev_only@localhost:5433/job_market_test
pytest
```

Without `TEST_DATABASE_URL` or Docker, PostgreSQL tests skip. They are not counted as passes.

## CI

GitHub Actions installs dependencies, starts `pgvector/pgvector:pg16`, migrates, and runs the full suite. Adzuna keys and MiniLM downloads are not required.

## Limitations

- hashing-v1 is not semantic
- MiniLM is optional and not in the default image
- Hybrid DESIGN weights are unevaluated for a production change
- Location strings are not geocoded
- Experience is not inferred from prose
- No historical skill-growth claims
- One Adzuna query is not the whole market
- A past commit leaked a database password in git history; rotate it outside git

## Future work

Historical trends, a larger labeled set, optional default MiniLM in a separate fat image. Not planned here: LLM ranking, new job boards, Kafka/Redis.

## Documents

| Document | Role |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/DESIGN.md` | Target architecture |
| `docs/METRICS.md` | Dashboard metric definitions |
| `docs/EVALUATION.md` | Ranking evaluation report |
| `docs/PHASE_7_SUMMARY.md` | Packaging and validation |

## Author

**Mohnish Gurramkonda** · [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
