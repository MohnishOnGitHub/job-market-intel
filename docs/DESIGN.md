# Job Market Intel — Technical Design Document

**Project:** Job Market Intel  
**Document version:** 1.0  
**Status:** Proposed architecture for staged implementation  
**Related document:** `PRD.md`

---

# 1. Purpose

This document defines the technical architecture for upgrading Job Market Intel from its current FastAPI + PostgreSQL + TF-IDF MVP into a modular job-market data, analytics, and ranking platform.

The design favors:

- simple components;
- measurable ML improvements;
- PostgreSQL as the primary system of record;
- batch ingestion over unnecessary streaming;
- a modular monolith instead of microservices;
- reproducibility;
- explicit data lineage;
- testable ranking logic.

---

# 2. Existing System

The current repository must be audited before implementation.

Based on the known MVP, the existing path is approximately:

```
Résumé PDF
    |
    v
PyPDF2 text extraction
    |
    v
hardcoded skill extraction
    |
    +-----------------------+
    |                       |
    v                       v
TF-IDF résumé vector     PostgreSQL jobs
    |                       |
    +----------+------------+
               |
               v
        cosine similarity
               |
               v
         skill overlap
               |
               v
          job ranking
               |
               v
           FastAPI
```

The exact implementation must be verified during Phase 0.

No migration should assume this representation is fully correct until the repository audit is complete.

---

# 3. Target Architecture

```
                           ┌──────────────────────┐
                           │   Résumé Upload      │
                           └──────────┬───────────┘
                                      │
                                      v
                           ┌──────────────────────┐
                           │ Résumé Processing    │
                           │ text + skill extract │
                           └──────────┬───────────┘
                                      │
                                      v
                           ┌──────────────────────┐
                           │ Résumé Embedding     │
                           └──────────┬───────────┘
                                      │
                                      │
┌─────────────────────┐               │
│ Public ATS / Sources│               │
└──────────┬──────────┘               │
           │                          │
           v                          │
┌─────────────────────┐               │
│ Source Adapters     │               │
└──────────┬──────────┘               │
           │                          │
           v                          │
┌─────────────────────┐               │
│ Raw Job Records     │               │
└──────────┬──────────┘               │
           │                          │
           v                          │
┌─────────────────────┐               │
│ Normalize / Dedupe  │               │
└──────────┬──────────┘               │
           │                          │
           v                          │
┌─────────────────────┐               │
│ Skill Enrichment    │               │
└──────────┬──────────┘               │
           │                          │
           v                          │
┌──────────────────────────────────────────────┐
│            PostgreSQL + pgvector             │
│ jobs | skills | job_skills | ingestion_runs │
│ embeddings | historical metadata            │
└──────────────┬──────────────────┬────────────┘
               │                  │
               │                  │
               v                  v
      ┌────────────────┐   ┌──────────────────┐
      │ Hybrid Ranking │   │ Market Analytics │
      └───────┬────────┘   └────────┬─────────┘
              │                     │
              +----------+----------+
                         |
                         v
                  ┌─────────────┐
                  │   FastAPI   │
                  └──────┬──────┘
                         |
                         v
                  ┌─────────────┐
                  │ Dashboard   │
                  └─────────────┘
```

---

# 4. Architectural Style

Use a **modular monolith**.

Rationale:

- repository scale does not justify distributed services;
- easier local setup;
- simpler testing;
- easier portfolio review;
- avoids fake production complexity;
- modules can still have explicit boundaries.

Do not introduce microservices unless a real operational need appears.

---

# 5. Proposed Repository Structure

The final structure should evolve toward:

```
job-market-intel/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── jobs.py
│   │       ├── resumes.py
│   │       ├── matching.py
│   │       ├── skills.py
│   │       └── analytics.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── repositories/
│   │       ├── jobs.py
│   │       ├── skills.py
│   │       └── analytics.py
│   │
│   ├── schemas/
│   │   ├── job.py
│   │   ├── resume.py
│   │   ├── match.py
│   │   ├── skill.py
│   │   └── analytics.py
│   │
│   ├── services/
│   │   ├── resume_parser.py
│   │   ├── skill_extractor.py
│   │   ├── embedding_service.py
│   │   ├── ranking.py
│   │   └── analytics.py
│   │
│   ├── ingestion/
│   │   ├── base.py
│   │   ├── normalize.py
│   │   ├── dedupe.py
│   │   └── sources/
│   │       ├── greenhouse.py
│   │       └── lever.py
│   │
│   └── domain/
│       ├── ranking.py
│       └── skills.py
│
├── data/
│   ├── taxonomy/
│   │   └── skills.yml
│   └── evaluation/
│       └── relevance_labels.csv
│
├── scripts/
│   ├── ingest_jobs.py
│   ├── enrich_jobs.py
│   ├── generate_embeddings.py
│   └── evaluate_ranking.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│   ├── PRD.md
│   ├── DESIGN.md
│   └── EVALUATION.md
│
├── frontend/
│   └── ...
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml or requirements files
└── README.md
```

This is a target, not a requirement to create every file immediately.

---

# 6. Component Design

## 6.1 Configuration

All runtime configuration should be centralized.

Example settings:

```
DATABASE_URL
APP_ENV
LOG_LEVEL

EMBEDDING_PROVIDER
EMBEDDING_MODEL
EMBEDDING_DIMENSION

MATCH_WEIGHT_SEMANTIC
MATCH_WEIGHT_SKILL
MATCH_WEIGHT_EXPERIENCE
MATCH_WEIGHT_RECENCY
MATCH_WEIGHT_LOCATION

MAX_UPLOAD_MB
```

Use a typed configuration mechanism such as Pydantic Settings.

No secrets in source code.

---

# 7. Database Design

PostgreSQL remains the primary datastore.

Add pgvector when semantic retrieval is introduced.

## 7.1 jobs

Suggested fields:

```
id UUID / BIGINT PK
source TEXT NOT NULL
source_job_id TEXT
source_url TEXT
company TEXT NOT NULL
title TEXT NOT NULL
description TEXT NOT NULL

location_raw TEXT
location_normalized TEXT
employment_type TEXT
experience_level TEXT

salary_min NUMERIC
salary_max NUMERIC
salary_currency TEXT

posted_at TIMESTAMPTZ
first_seen_at TIMESTAMPTZ NOT NULL
last_seen_at TIMESTAMPTZ NOT NULL

active BOOLEAN NOT NULL DEFAULT TRUE

content_hash TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

Indexes should include:

- source/source_job_id unique where reliable;
- posted_at;
- active;
- normalized location;
- normalized title or role family where introduced.

---

## 7.2 skills

```
id
canonical_name
category
slug
```

Examples:

```
Python               Programming
PostgreSQL           Databases
Spark                Data Engineering
scikit-learn         Machine Learning
AWS                  Cloud
```

---

## 7.3 skill_aliases

```
id
skill_id
alias
normalized_alias
```

Examples:

```
postgres       -> PostgreSQL
postgresql     -> PostgreSQL
sklearn        -> scikit-learn
apache spark   -> Spark
```

---

## 7.4 job_skills

Many-to-many relationship.

```
job_id
skill_id
confidence
extraction_source
```

Composite unique key on `(job_id, skill_id)`.

---

## 7.5 job_embeddings

Could be embedded directly on `jobs` or separated.

Suggested:

```
job_id
embedding_model
embedding vector(...)
content_hash
created_at
```

Separating embeddings makes model/version upgrades easier.

---

## 7.6 ingestion_runs

```
id
source
started_at
completed_at
status
records_fetched
records_inserted
records_updated
records_skipped
records_failed
error_summary
```

This is important for data engineering observability.

---

# 8. Ingestion Pipeline

## 8.1 Adapter contract

Each source should implement a common interface:

```python
class JobSource(Protocol):
    def fetch_jobs(self) -> Iterable[RawJob]:
        ...
```

`RawJob` represents source-specific content before normalization.

---

## 8.2 Pipeline stages

```
fetch
  ->
validate
  ->
normalize
  ->
deduplicate
  ->
upsert
  ->
extract skills
  ->
generate/update embedding
  ->
record metrics
```

Early phases may run enrichment separately.

Do not make ingestion dependent on embedding availability.

---

## 8.3 Normalization

Normalize:

- whitespace;
- URLs;
- company names where safe;
- job title;
- location;
- employment type;
- timestamp formats.

Do not infer missing salary or experience values.

---

# 9. Deduplication Design

Use deterministic duplicate handling first.

Priority:

1. `(source, source_job_id)`
2. canonical source URL
3. content fingerprint

Fingerprint example:

```
lower(normalized_company)
+
lower(normalized_title)
+
lower(normalized_location)
+
stable_description_hash
```

Do not introduce fuzzy ML duplicate detection until deterministic duplicate handling is measured.

---

# 10. Skill Extraction Design

## 10.1 Taxonomy-first approach

Use a curated taxonomy file such as:

```
Python:
  category: programming
  aliases:
    - python

PostgreSQL:
  category: database
  aliases:
    - postgres
    - postgresql

scikit-learn:
  category: machine_learning
  aliases:
    - sklearn
    - scikit learn
```

The first implementation can use deterministic extraction with normalized boundaries and alias matching.

This is preferable to immediately adding a complex NER model.

---

## 10.2 Extraction interface

```python
@dataclass
class ExtractedSkill:
    canonical_name: str
    category: str
    evidence: str | None
    confidence: float
```

Service:

```python
extract_skills(text: str) -> list[ExtractedSkill]
```

---

## 10.3 Evaluation

Create tests for:

- aliases;
- word boundaries;
- capitalization;
- false-positive substrings;
- multiple aliases mapping to one canonical skill.

---

# 11. Résumé Processing

## 11.1 Flow

```
upload
  ->
validate file
  ->
extract text
  ->
normalize text
  ->
extract skills
  ->
optionally embed text
  ->
match
```

## 11.2 Privacy

Prefer in-memory or temporary processing.

Do not persist résumé files by default.

If temporary files are used, remove them after processing.

---

# 12. Retrieval and Ranking

Ranking must be separated into two concepts:

1. candidate retrieval;
2. final ranking.

This prevents expensive scoring across the entire database.

---

# 13. Lexical Baseline

Preserve TF-IDF/cosine similarity as a baseline.

The baseline implementation should be callable independently:

```python
rank_tfidf(resume_text, jobs)
```

This becomes part of the evaluation framework.

Do not silently replace it.

---

# 14. Semantic Retrieval

## 14.1 Embedding abstraction

```python
class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...
```

This prevents the application from becoming tightly coupled to one model/vendor.

For a portfolio project, a local sentence-transformer model is preferred initially unless another choice is justified.

---

## 14.2 Job embedding content

Create a deterministic text representation:

```
Title: Data Engineer
Company: Example
Location: Bengaluru
Description:
...
Skills:
Python, SQL, Spark, AWS
```

Store a content hash.

Regenerate embedding only when the content hash or embedding model changes.

---

## 14.3 Vector retrieval

Use pgvector cosine distance/similarity.

Conceptually:

```sql
SELECT ...
FROM job_embeddings
JOIN jobs ...
WHERE jobs.active = TRUE
ORDER BY embedding <=> :resume_embedding
LIMIT :candidate_count;
```

Candidate count could begin around 50-200 and should be benchmarked.

---

# 15. Hybrid Ranking

## 15.1 Ranking signals

Each candidate receives normalized component scores:

```
semantic_score   [0,1]
skill_score      [0,1]
experience_score [0,1]
recency_score    [0,1]
location_score   [0,1]
```

Final:

```
hybrid_score =
  w_semantic   * semantic_score +
  w_skill      * skill_score +
  w_experience * experience_score +
  w_recency    * recency_score +
  w_location   * location_score
```

Weights must sum to 1 or be normalized.

---

## 15.2 Skill score

Initial simple version:

```
matched_skills / required_job_skills
```

If no job skills are extracted, the component should have a documented neutral/fallback behavior.

Do not arbitrarily reward jobs with missing skill data.

---

## 15.3 Recency

Example bounded decay:

```
score = exp(-age_days / tau)
```

or a simple piecewise function.

Choose a transparent implementation first.

---

## 15.4 Experience fit

Experience parsing is unreliable.

Begin with explicit normalized levels when available:

- internship
- entry
- junior
- mid
- senior
- lead

Avoid pretending to infer precise years from ambiguous descriptions until tested.

---

## 15.5 Location fit

Initial states:

```
1.0 exact preferred city / remote preference
0.5 acceptable / nearby / hybrid-compatible
0.0 incompatible
```

Only use if the user provides location preference.

---

# 16. Ranking Explanation

Response object:

```json
{
  "job_id": "...",
  "hybrid_score": 0.82,
  "components": {
    "semantic": 0.86,
    "skills": 0.76,
    "experience": 0.80,
    "recency": 0.91,
    "location": 1.0
  },
  "matched_skills": ["Python", "SQL", "Spark"],
  "missing_skills": ["Airflow", "AWS"]
}
```

The exact aggregate score should never be labeled as “probability of getting hired.”

---

# 17. Skill-Gap Intelligence

For the top-N otherwise relevant jobs:

```
missing_skill_frequency(skill) =
    jobs_missing_skill / relevant_jobs
```

A stronger metric can estimate jobs unlocked:

```
jobs_unlocked(skill) =
    count of relevant jobs for which skill is among the remaining important gaps
```

Initial product output:

```
Airflow
Appears in 38% of your high-match Data Engineer jobs

AWS
Appears in 34%

dbt
Appears in 22%
```

This is substantially more useful than an unordered missing-skill list.

---

# 18. Analytics Layer

SQL/database aggregations should power most analytics.

Examples:

## Top skills

```sql
SELECT s.canonical_name, COUNT(*) AS jobs
FROM job_skills js
JOIN skills s ON s.id = js.skill_id
JOIN jobs j ON j.id = js.job_id
WHERE j.active = TRUE
GROUP BY s.canonical_name
ORDER BY jobs DESC;
```

## Role/location filters

Analytics should accept filters:

- normalized role;
- location;
- experience;
- date range.

Do not load the entire dataset into pandas for every API request.

Pandas is appropriate for offline analysis and evaluation.

---

# 19. Trend Calculation

Historical trend metrics require stable snapshots.

Potential metric:

```
skill_share(skill, period) =
 jobs_with_skill / total_jobs_in_period
```

Growth:

```
growth =
 current_skill_share - previous_skill_share
```

Prefer share over raw counts when ingestion volume changes over time.

Do not display “fastest growing” until enough historical data exists.

---

# 20. API Design

Proposed API namespace:

```
GET  /health

GET  /api/v1/jobs
GET  /api/v1/jobs/{id}

POST /api/v1/resumes/parse
POST /api/v1/matches

GET  /api/v1/skills
GET  /api/v1/analytics/overview
GET  /api/v1/analytics/skills
GET  /api/v1/analytics/locations
GET  /api/v1/analytics/experience
```

Administrative ingestion should initially be CLI-based rather than publicly exposed.

---

# 21. Matching Request

Example:

```json
{
  "resume_text": "...",
  "filters": {
    "roles": ["Data Engineer"],
    "locations": ["Bengaluru"],
    "max_age_days": 30
  },
  "limit": 20
}
```

For uploaded résumé files, use multipart upload at a dedicated endpoint or a combined matching endpoint.

---

# 22. Matching Response

Example:

```json
{
  "results": [
    {
      "job": {
        "id": "123",
        "title": "Data Engineer",
        "company": "Example",
        "location": "Bengaluru"
      },
      "score": 0.82,
      "score_breakdown": {
        "semantic": 0.86,
        "skills": 0.76,
        "experience": 0.80,
        "recency": 0.91,
        "location": 1.0
      },
      "matched_skills": [
        "Python",
        "SQL",
        "Spark"
      ],
      "missing_skills": [
        "Airflow",
        "AWS"
      ]
    }
  ],
  "skill_gaps": [
    {
      "skill": "Airflow",
      "relevant_job_frequency": 0.38
    }
  ]
}
```

---

# 23. Evaluation Design

This is a core requirement rather than optional polish.

## 23.1 Dataset

Create a small benchmark containing:

```
resume_id
job_id
relevance_label
notes
```

Suggested label scale:

```
0 = irrelevant
1 = weak
2 = relevant
3 = highly relevant
```

Labels must be documented.

---

## 23.2 Systems compared

Evaluate:

```
A. keyword/skill overlap
B. TF-IDF cosine similarity
C. semantic embedding similarity
D. hybrid ranker
```

---

## 23.3 Metrics

At minimum:

- Precision@5
- Recall@10
- NDCG@10
- MRR

Optional:

- latency;
- retrieval candidate recall;
- component ablations.

---

## 23.4 Ablation study

Once the hybrid ranker exists:

```
semantic only
semantic + skills
semantic + skills + recency
full hybrid
```

This demonstrates whether added features improve rankings.

---

# 24. Testing Strategy

## Unit tests

Cover:

- text normalization;
- skill alias matching;
- score calculations;
- recency;
- dedup fingerprints;
- ranking ordering;
- schema validation.

## Integration tests

Cover:

- database repository;
- ingestion upsert;
- API endpoints;
- vector retrieval where available.

## Regression tests

Protect known ranking behavior.

Example:

Given a fixed résumé and fixed jobs, ranking order must remain stable unless a deliberate scoring change is made.

---

# 25. Error Handling

Use domain-specific exceptions.

Examples:

```
ResumeParseError
UnsupportedFileTypeError
JobSourceError
EmbeddingError
DatabaseUnavailableError
```

API layer maps these to HTTP responses.

Do not leak internal stack traces to users.

---

# 26. Observability

Use logging with fields such as:

```
event
request_id
source
job_count
duration_ms
model
status
error_type
```

Important events:

- ingestion_started
- ingestion_completed
- ingestion_failed
- resume_parsed
- embedding_generated
- match_completed

Avoid logging raw résumé text.

---

# 27. Local Development

Target developer flow:

```
git clone ...
cd job-market-intel

cp .env.example .env

docker compose up -d db

python -m ...
# migration command
# sample ingestion command

uvicorn app.main:app --reload
```

Tests:

```
pytest
```

Exact package manager and commands should be standardized during Phase 1.

---

# 28. Docker

At minimum:

```
app
postgres + pgvector
```

Do not add Redis unless there is a measured cache need.

---

# 29. CI

GitHub Actions should eventually run:

- dependency installation;
- lint;
- type checks if adopted;
- unit tests;
- integration tests where practical.

CI should not require private production credentials.

---

# 30. Phase-by-Phase Technical Plan

## Phase 0 — Audit

No architecture changes.

Produce:

```
PHASE_0_AUDIT.md
```

Verify actual code, branches, ranking logic, tests and runtime.

---

## Phase 1 — Refactor

Move existing behavior into:

```
api
services
db
schemas
core
```

Do not change ranking semantics unless fixing a confirmed bug.

Deliver:

- tests;
- config;
- health endpoint;
- README.

---

## Phase 2 — Ingestion

Implement:

```
RawJob
NormalizedJob
JobSource adapter
normalizer
dedupe
repository upsert
ingestion runs
```

Add one real permitted source before adding more.

---

## Phase 3 — Skills

Implement taxonomy + aliases.

Backfill job skills.

Build skill analytics.

---

## Phase 4 — Embeddings / pgvector

Implement:

- extension/migration;
- embedding abstraction;
- embedding generation;
- vector candidate retrieval;
- hybrid ranker;
- score breakdown.

---

## Phase 5 — Evaluation

Build benchmark and report.

Do not tune weights against test data without a validation split.

---

## Phase 6 — Analytics

Build trend queries + API.

Create skill-gap intelligence.

---

## Phase 7 — Frontend / deployment / portfolio polish

Dashboard sections:

1. market overview;
2. role explorer;
3. skills explorer;
4. résumé upload;
5. ranked jobs;
6. skill-gap analysis.

Finalize README and screenshots.

---

# 31. Technical Decisions

## PostgreSQL over additional analytical stores

Reason:

- dataset size is portfolio-scale;
- simpler architecture;
- strong SQL demonstration;
- pgvector integrates retrieval.

A warehouse can be discussed as future scale work.

## Batch over Kafka

Job postings do not require sub-second ingestion.

Batch is operationally appropriate.

Kafka should not be added merely to demonstrate Kafka because SentinelPay already demonstrates streaming architecture.

## Deterministic skill taxonomy before ML NER

Reason:

- easier to evaluate;
- transparent;
- portfolio reviewers can understand it;
- technical skills have many known aliases.

ML extraction can later be compared against this baseline.

## TF-IDF retained

Reason:

- reproducible lexical baseline;
- demonstrates measured improvement;
- avoids “embeddings because AI.”

---

# 32. Important Guardrails for Coding Assistants

Any AI coding tool operating on this repository must:

1. inspect existing code before modifying;
2. follow `PRD.md` and `DESIGN.md`;
3. implement only the requested phase;
4. preserve working behavior unless change is explicitly required;
5. add tests for new functionality;
6. avoid unrelated refactors;
7. not commit or push unless requested;
8. state assumptions;
9. report files changed;
10. report tests run and their results;
11. stop after the requested phase.

Do not:

- add LLM features without an approved requirement;
- add Kafka;
- add Kubernetes;
- create microservices;
- rewrite the frontend during backend phases;
- invent performance/relevance metrics;
- silently change ranking formulas.

---

# 33. Final Technical Outcome

The finished system should have a defensible engineering story:

> Job data is ingested through source adapters, normalized and deduplicated into PostgreSQL, enriched with a canonical skill taxonomy and vector embeddings, queried through pgvector for semantic candidates, reranked using interpretable candidate/job features, evaluated against lexical baselines, and exposed through FastAPI and a market-intelligence dashboard.

This architecture is intentionally sophisticated enough to demonstrate real DS/DE/ML work without adding infrastructure that does not serve the product.
