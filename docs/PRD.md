# Job Market Intel — Product Requirements Document (PRD)

**Project:** Job Market Intel  
**Owner:** Mohnish Gurramkonda  
**Status:** Planned upgrade of existing MVP  
**Document version:** 1.0  
**Primary target roles demonstrated:** Data Scientist, Data Engineer, ML/AI Engineer  
**Primary users:** Students, new graduates, and early-career professionals searching for technical roles

---

# 1. Executive Summary

Job Market Intel is an end-to-end job-market intelligence and candidate-job matching platform.

The current project is a small FastAPI application that accepts a résumé PDF, extracts text and skills, compares the résumé against jobs stored in PostgreSQL using TF-IDF/cosine similarity, and returns matched and missing skills.

The upgraded project will evolve this MVP into a production-oriented data and machine-learning system that:

1. Collects and normalizes job postings from supported public job/ATS sources.
2. Stores historical job-market data.
3. Extracts and normalizes skills from job descriptions and résumés.
4. Measures skill demand and market trends.
5. Semantically matches candidates to jobs using embeddings and structured features.
6. Produces explainable ranking results.
7. Evaluates ranking quality against reproducible baselines.
8. Presents market intelligence and personalized recommendations through an API and dashboard.

The project is intentionally designed to demonstrate Data Engineering, Data Science, NLP, Information Retrieval, Ranking, SQL, FastAPI, PostgreSQL, testing, and production-oriented engineering in one coherent product.

---

# 2. Problem Statement

Job seekers face two related problems.

## 2.1 Finding relevant jobs

Traditional keyword matching performs poorly when a résumé and job description describe the same concept using different wording.

Examples:

- "Postgres" vs "PostgreSQL"
- "distributed data processing" vs "Apache Spark"
- "machine-learning pipelines" vs "ML workflows"

A candidate may therefore be a strong fit even when lexical overlap is weak.

## 2.2 Understanding the market

Job seekers also lack structured answers to questions such as:

- Which skills are most demanded for Data Scientist roles?
- Which skills are growing fastest?
- What technologies are commonly requested together?
- Which cities have the most entry-level ML jobs?
- What skills am I missing from jobs that otherwise match my profile?
- What should I learn next to qualify for more jobs?

Most job portals return listings rather than actionable labor-market intelligence.

Job Market Intel aims to solve both problems using a single data platform.

---

# 3. Product Vision

Build a system that can answer:

> “What jobs fit me, why do they fit me, and what does the current job market tell me I should learn next?”

The final product should combine:

- job ingestion
- data cleaning
- structured skill extraction
- historical analytics
- résumé understanding
- semantic retrieval
- hybrid ranking
- explainability
- evaluation
- interactive exploration

---

# 4. Goals

## 4.1 Product goals

The system must:

- ingest job postings from permitted public sources;
- normalize heterogeneous job records into a canonical schema;
- detect duplicate job listings;
- maintain job history using first-seen and last-seen timestamps;
- extract skills from job descriptions and résumés;
- normalize aliases to canonical skill names;
- compute market-level skill statistics;
- match a résumé to relevant jobs;
- provide matched and missing skills;
- provide an interpretable ranking score;
- support filtering by role, location, experience level, company, and recency;
- expose functionality through FastAPI;
- provide an analytics/dashboard experience;
- quantitatively evaluate ranking quality.

## 4.2 Portfolio goals

The repository should clearly demonstrate:

### Data Engineering
- ingestion
- ETL/ELT
- normalization
- deduplication
- PostgreSQL modeling
- historical snapshots
- reproducible jobs

### Data Science
- exploratory analysis
- hiring trends
- skill demand
- distributions
- market comparisons
- derived metrics

### NLP / ML
- résumé parsing
- skill extraction
- embeddings
- similarity search
- ranking

### Information Retrieval
- TF-IDF baseline
- vector retrieval
- hybrid ranking
- ranking metrics

### Software Engineering
- FastAPI
- modular architecture
- typed schemas
- tests
- Docker
- CI
- configuration management
- documentation

---

# 5. Non-Goals

The initial upgraded product will NOT attempt to:

- become a full job board;
- automatically submit job applications;
- scrape websites in violation of terms of service;
- build a distributed microservice architecture;
- require Kubernetes;
- introduce Kafka unless a justified streaming use case later emerges;
- use an LLM merely as a marketing feature;
- train a large proprietary embedding model;
- predict hiring outcomes;
- claim that ranking scores represent a candidate's actual hiring probability;
- replace human judgment in recruiting.

---

# 6. Target Users

## Persona A — Final-year student

Needs:
- entry-level jobs;
- role-specific skill gaps;
- location filtering;
- an answer to “what should I learn next?”

## Persona B — Early-career data professional

Needs:
- jobs matching their experience;
- semantic matching beyond exact keywords;
- skill demand trends;
- comparison across Data Science / Data Engineering / ML roles.

## Persona C — Recruiter or analyst exploring the repository

Needs:
- clear architecture;
- reproducible data pipeline;
- measurable ranking evaluation;
- understandable engineering tradeoffs.

The repository itself is also a product surface.

---

# 7. Core User Stories

## Resume matching

As a user, I can upload a résumé so that the system can identify jobs relevant to my background.

As a user, I can see:

- overall match score;
- semantic similarity;
- skill overlap;
- matched skills;
- missing skills;
- job recency;
- relevant job metadata.

As a user, I can filter recommendations by:

- role;
- location;
- experience;
- recency;
- employment type.

## Skill-gap analysis

As a user, I can see the missing skills that occur most frequently across jobs I otherwise match well.

The system should prioritize missing skills using market demand rather than merely listing every absent keyword.

## Market intelligence

As a user, I can explore:

- top skills;
- fastest-growing skills;
- jobs by location;
- jobs by experience level;
- role-specific skill demand;
- company hiring activity;
- job counts over time.

## Explainability

As a user, I can understand why a job ranked highly.

Example:

```
Match score: 82%

Semantic similarity: 0.84
Skill overlap: 75%
Experience fit: Strong
Location fit: Exact
Recency: Posted 2 days ago

Matched:
Python
SQL
Spark
PostgreSQL

Missing:
Airflow
AWS
```

---

# 8. Functional Requirements

## FR-1 — Job ingestion

The system shall ingest jobs from supported sources using adapters.

Each ingestion run shall record:

- source;
- source job ID;
- source URL;
- ingestion timestamp.

Ingestion must be idempotent where possible.

---

## FR-2 — Canonical job schema

Each normalized job shall support:

- id
- source
- source_job_id
- source_url
- company
- title
- description
- location
- normalized_location
- employment_type
- experience_level
- salary_min
- salary_max
- salary_currency
- posted_at
- first_seen_at
- last_seen_at
- active
- created_at
- updated_at

Optional data must remain nullable rather than being invented.

---

## FR-3 — Deduplication

The system shall identify obvious duplicates using deterministic fields where available:

- source + source_job_id
- canonical URL
- company/title/location fingerprint

A fuzzy duplicate detector may be added later.

---

## FR-4 — Skill extraction

The system shall identify technical skills in résumés and job descriptions.

The extractor shall support:

- canonical names;
- aliases;
- categories;
- normalized output.

Examples:

```
postgres -> PostgreSQL
postgresql -> PostgreSQL
sklearn -> scikit-learn
amazon web services -> AWS
apache spark -> Spark
```

---

## FR-5 — Résumé ingestion

The user shall be able to upload a supported résumé document.

At minimum:

- PDF support
- text extraction
- clear error handling
- extracted skills
- no silent failure

The product should not permanently store user résumés unless explicitly required.

---

## FR-6 — Lexical ranking baseline

The existing TF-IDF/cosine similarity implementation shall be retained as a reproducible baseline.

This is important for evaluation.

---

## FR-7 — Semantic matching

A résumé and normalized job description shall receive vector representations using an embedding model.

The system shall support similarity retrieval using PostgreSQL + pgvector or an equivalent local vector index.

---

## FR-8 — Hybrid ranking

The ranking service shall combine multiple signals.

Initial candidate signals:

- semantic similarity;
- skill overlap;
- experience fit;
- location fit;
- recency.

Weights shall be configurable.

Example only:

```
score =
    0.50 * semantic_similarity +
    0.25 * skill_overlap +
    0.10 * experience_fit +
    0.10 * recency_score +
    0.05 * location_fit
```

These values are not final and must not be presented as empirically optimal until evaluated.

---

## FR-9 — Ranking explanation

Each recommendation shall return the components used to derive its ranking.

The API shall avoid returning only an unexplained aggregate score.

---

## FR-10 — Market analytics

The system shall calculate at least:

- active job count;
- jobs over time;
- top skills;
- skills by role;
- skills by location;
- experience distribution;
- company hiring counts.

After sufficient historical data exists, it shall support:

- skill growth;
- skill decline;
- hiring growth by role/location.

---

## FR-11 — Skill-gap recommendations

Given a résumé and a relevant job set, the system shall determine high-value missing skills.

A useful skill-gap metric should consider:

- frequency among relevant jobs;
- number of additional jobs unlocked;
- optional role-specific weighting.

---

## FR-12 — API

The FastAPI backend shall expose logically separated endpoints.

Expected capabilities include:

- health
- jobs
- filters
- résumé parsing
- matching
- skills
- analytics

Exact paths belong in the Design Doc/API specification.

---

## FR-13 — Evaluation

The repository shall include an offline ranking evaluation framework.

Baselines:

1. keyword/skill overlap;
2. TF-IDF;
3. embedding similarity;
4. hybrid ranking.

Metrics:

- Precision@K
- Recall@K
- NDCG@K
- MRR

A labeled relevance dataset must distinguish benchmark labels from production data.

---

# 9. Non-Functional Requirements

## NFR-1 — Reproducibility

A developer should be able to clone the repository, configure environment variables, initialize the database, load sample data, and run the application using documented commands.

## NFR-2 — Maintainability

The system shall avoid a monolithic `main.py`.

Business logic should not live directly inside API route handlers.

## NFR-3 — Testability

Pure ranking and extraction functions should be independently testable.

## NFR-4 — Observability

The application shall use structured logging for:

- ingestion counts;
- failed records;
- API failures;
- ranking timings;
- enrichment failures.

## NFR-5 — Security

Secrets must not be committed.

Configuration shall use environment variables.

File uploads must validate type and size.

SQL must use parameterized queries or an ORM/query layer.

## NFR-6 — Performance

For the portfolio-scale dataset, search should avoid scoring every job in Python when vector/database retrieval can reduce the candidate set.

## NFR-7 — Data provenance

Every job should retain its original source metadata.

---

# 10. Data and Ethics Requirements

- Do not fabricate job attributes.
- Respect source terms and robots/access restrictions.
- Prefer documented APIs/public ATS feeds.
- Store source URLs/provenance.
- Do not infer protected demographic attributes.
- Do not use protected attributes in ranking.
- Ranking is relevance matching, not hiring prediction.

---

# 11. Success Metrics

## Engineering

- full test suite passes;
- deterministic setup documented;
- no secrets committed;
- modular architecture;
- Docker-based local setup;
- CI validates tests and lint/type checks.

## Data pipeline

- ingestion run metrics available;
- duplicates handled;
- records carry provenance;
- historical timestamps maintained.

## Ranking

At minimum:

- baseline metrics reported;
- semantic model benchmarked against TF-IDF;
- hybrid model benchmarked against individual components.

No arbitrary improvement percentage should be claimed without evaluation.

## Product

A user should be able to:

1. open the dashboard;
2. view market analytics;
3. upload a résumé;
4. receive ranked jobs;
5. understand why each ranked result was returned;
6. see high-value missing skills.

---

# 12. Product Phases

## Phase 0 — Audit and Stabilize

Deliverables:

- repository audit;
- actual current architecture;
- scoring investigation;
- current test status;
- runtime setup;
- prioritized issues.

No feature development.

---

## Phase 1 — Modular Foundation

Deliverables:

- modular backend;
- centralized configuration;
- database layer;
- schemas;
- separated services;
- expanded tests;
- `.env.example`;
- improved README.

Behavior should remain substantially equivalent to the MVP.

---

## Phase 2 — Data Ingestion and History

Deliverables:

- source adapter interface;
- at least one permitted working source;
- canonical job schema;
- normalization;
- deduplication;
- first/last seen timestamps;
- ingestion command;
- ingestion metrics.

---

## Phase 3 — Skill Intelligence

Deliverables:

- taxonomy;
- aliases;
- categories;
- normalized skill extraction;
- job skill enrichment;
- skill analytics;
- skill-demand tests.

---

## Phase 4 — Semantic Retrieval and Hybrid Ranking

Deliverables:

- embedding provider abstraction;
- pgvector;
- job embeddings;
- semantic candidate retrieval;
- hybrid ranker;
- ranking explanations;
- configurable weights.

---

## Phase 5 — Evaluation

Deliverables:

- labeled relevance dataset;
- evaluation CLI/notebook;
- TF-IDF baseline;
- semantic benchmark;
- hybrid benchmark;
- Precision@K;
- Recall@K;
- NDCG@K;
- MRR;
- reproducible results document.

---

## Phase 6 — Market Intelligence

Deliverables:

- role analytics;
- location analytics;
- experience analytics;
- skill trends;
- candidate skill-gap analysis;
- analytics API.

---

## Phase 7 — Product and Portfolio Polish

Deliverables:

- final dashboard;
- Docker;
- CI;
- architecture diagram;
- screenshots;
- project demo;
- comprehensive README;
- known limitations;
- future work.

---

# 13. Phase Exit Criteria

A phase is complete only when:

1. required functionality exists;
2. tests are added;
3. existing tests continue to pass;
4. documentation is updated;
5. no unrelated features are silently introduced;
6. the implementation is reviewed before moving to the next phase.

Cursor or another coding assistant must stop at the requested phase.

---

# 14. Future Opportunities

Potential later improvements:

- salary normalization;
- remote/hybrid classification;
- title normalization;
- learning-path recommendations;
- skill co-occurrence graph;
- clustering job families;
- reranking models;
- temporal forecasting;
- RAG/LLM interface grounded in market analytics.

These are explicitly future scope and should not block the core project.

---

# 15. Final Product Positioning

Recommended one-line description:

> Job Market Intel is an end-to-end job-market intelligence and candidate-matching platform that ingests and normalizes job postings, tracks hiring and skill trends, and ranks opportunities against a résumé using semantic retrieval, structured skill signals, and evaluated hybrid ranking.

