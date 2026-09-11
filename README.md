# Job Market Intel

A job-market intelligence app: ingest Adzuna postings, measure skill demand in SQL, and rank jobs against a résumé with explainable scores.

## What it does

1. **Market intelligence** — active jobs, skill demand, category mix, experience, locations, companies, and posting age.
2. **Résumé matching** — upload a PDF and compare the pairwise TF-IDF baseline with a structured hybrid ranker.
3. **Evaluation** — a committed 256-judgment fixture reports directional ranking quality.

Open http://127.0.0.1:8000 after ingesting jobs. The UI uses same-origin APIs.

## Architecture

```text
Adzuna → normalize → dedupe → PostgreSQL jobs
       → job_skills (taxonomy)
       → job_embeddings (optional pgvector)

Browser
  Market  → /api/v1/analytics/*
  Match   → POST /upload-resume  or  POST /api/v1/matches/upload
  Eval    → static measured Phase 5 numbers
```

hashing-v1 is **lexical hashing retrieval**. sentence-transformers, when installed, are **semantic embeddings**. Hybrid is a **structured weighted ranker**. TF-IDF is the **pairwise lexical baseline**.

## Demo / screenshots

The dashboard is laid out for four later screenshots: market overview, skill-demand table/chart, résumé results, and score breakdown. This repository does not include generated screenshots.

## Market intelligence

Filters: title contains, location contains, optional stored experience level.

| View | Meaning |
|---|---|
| Active jobs | Filtered `active = TRUE` rows |
| Jobs with skill data | Active jobs with ≥1 `job_skills` row |
| Skill share | Jobs containing the skill / filtered active jobs |
| Categories | Jobs with ≥1 skill in that category |
| Experience | Stored `experience_level` only; blanks are `unknown` |
| Locations | `COALESCE(location_normalized, location_raw)` strings, not geocodes |
| Freshness | `posted_at` age buckets, including unknown |

Definitions: `docs/METRICS.md`. No growth or forecast claims.

## Résumé matching

- **Pairwise TF-IDF baseline** — `POST /upload-resume`
- **Lexical vector + structured hybrid** — default hashing-v1 via `POST /api/v1/matches/upload`
- **Semantic + structured hybrid** — only if `EMBEDDING_PROVIDER=sentence-transformers`

Cards show match score, method, matched/missing skills, and component bars. Unused location or experience preferences display as **N/A**, not 0. The score is not a hiring probability. The PDF is parsed in memory and not stored.

## Ranking systems

```text
TF-IDF:  0.7 * pairwise cosine + 0.3 * skill overlap
Hybrid:  0.50 * similarity + 0.25 * skills + 0.10 * experience + 0.10 * recency + 0.05 * location
```

Hybrid weights renormalize when a preference is omitted. These weights are DESIGN defaults, not a tuned production optimum.

## Evaluation

v1 fixture: **8 synthetic profiles × 32 jobs = 256 judgments**. Directional benchmark; not statistically significant.

Held-out test (3 profiles):

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| Skill overlap | 0.467 | 0.589 | 0.586 | 0.778 |
| Pairwise TF-IDF | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 (lexical) | 0.533 | 0.633 | 0.691 | 1.000 |
| Hybrid (DESIGN + hashing-v1) | 0.600 | 0.933 | 0.852 | 1.000 |

On validation, TF-IDF NDCG@10 was 0.685 vs hybrid 0.677. Sentence-transformer evaluation was **not run**. Production weights were not changed. See `/evaluation.html` and `docs/EVALUATION.md`.

## Data pipeline

```bash
python scripts/migrate.py
python scripts/sync_skills.py
python scripts/ingest_adzuna.py --query "data engineer" --pages 2
python scripts/enrich_job_skills.py --only-missing
python scripts/generate_embeddings.py --only-missing
```

Adzuna is the only source. One request is not the whole market. Jobs are not auto-deactivated when missing from a single page.

## Skill intelligence

`data/taxonomy/skills.yml` is the source of truth (~160 technical skills). Extraction is deterministic and alias-aware. `sql` inside `postgresql` does not count as SQL.

## API

Documented in `/docs`. Implemented endpoints include:

- `GET /health`
- `GET /jobs`, `GET /jobs/{id}`
- `GET /api/v1/skills`
- `GET /api/v1/ranking/status`
- `GET /api/v1/analytics/overview`
- `GET /api/v1/analytics/skills`
- `GET /api/v1/analytics/categories`
- `GET /api/v1/analytics/experience`
- `GET /api/v1/analytics/locations`
- `GET /api/v1/analytics/companies`
- `GET /api/v1/analytics/freshness`
- `POST /upload-resume`
- `POST /api/v1/matches`, `POST /api/v1/matches/upload`

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL and optional Adzuna keys
python scripts/migrate.py
python scripts/sync_skills.py
uvicorn app.main:app --reload
```

Python 3.10+ recommended. PostgreSQL needs pgvector for stored embeddings. Charts use Chart.js 4.4.1 from jsDelivr.

## Tests

```bash
pytest
```

Repository tests skip without `TEST_DATABASE_URL` or a ready Docker daemon.

## Limitations

- hashing-v1 is not a semantic model.
- Hybrid defaults are unevaluated for production changes.
- Location strings are not geocoded.
- Experience is not inferred from prose.
- No historical skill-growth claims.
- No Docker Compose app stack or CI yet.
- A past commit leaked a database password in git history; rotate it outside git.

## Roadmap

Possible later work: historical trends, a larger labeled set, optional sentence-transformer evaluation, Docker/CI. Not in this phase: LLM ranking, new job boards, Kafka/Redis.

## Documents

| Document | Role |
|---|---|
| `docs/PRD.md` | Product requirements |
| `docs/DESIGN.md` | Target architecture |
| `docs/METRICS.md` | Dashboard metric definitions |
| `docs/EVALUATION.md` | Ranking evaluation report |
| `docs/PHASE_6_SUMMARY.md` | This phase |

## Author

**Mohnish Gurramkonda** · [MohnishOnGitHub](https://github.com/MohnishOnGitHub)
