# Ranking Evaluation

Directional evaluation of the v1 synthetic fixture. Three held-out profiles are not enough for statistical significance. Production ranking formulas were not changed.

## Dataset

| Item | Value |
|---|---|
| Version | v1 |
| Profiles | 8 synthetic résumés |
| Jobs | 32 authored fixtures |
| Judgments | 256 (complete profile × job matrix) |
| Split | profile-level: 5 validation / 3 test |
| Binary threshold | relevance ≥ 2 |

Label distribution: **200** zeros, **15** ones, **25** twos, **16** threes.

Profiles and jobs are synthetic. They are not real applicants and not live Adzuna rows. Labels follow `docs/EVALUATION_GUIDE.md` and were not copied from TF-IDF, hashing-v1, or hybrid scores.

## Labeling Method

Author rubric on role family and seniority, plus documented overrides (clinical “python sql” bait, marketing intern, Go/Java backend, NLP research). See `docs/EVALUATION_GUIDE.md`.

## Candidate Profiles

| ID | Profile | Seniority | Split | Location pref |
|---|---|---|---|---|
| r_da_junior | Data Analyst | junior | validation | Bengaluru |
| r_ds_mid | Data Scientist | mid | validation | Remote |
| r_de_senior | Data Engineer | senior | validation | Remote |
| r_mle_mid | ML Engineer | mid | validation | Bengaluru |
| r_da_mid | Analyst / Analytics Engineer | mid | validation | Pune |
| r_de_mid | Data Engineer | mid | test | Bengaluru |
| r_ds_senior | Data Scientist (NLP) | senior | test | Remote |
| r_be_mid | Backend Engineer | mid | test | Hyderabad |

## Job Sample

32 fixtures covering DE, DA, DS, MLE, backend, analytics, plus irrelevant and lexical-bait postings (nurse, sales, PM, clinical coordinator, marketing intern). Some postings omit `experience_level`. One strong Bengaluru DE role is 180 days old.

## Systems Compared

| Method | What it is |
|---|---|
| skills | Canonical skill-overlap ratio only |
| tfidf | Pairwise TF-IDF cosine only (not the 0.7/0.3 upload-resume mix) |
| hashing | hashing-v1 cosine: **lexical hashing retrieval**, not semantic |
| semantic | sentence-transformer cosine (`all-MiniLM-L6-v2`, Phase 7) |
| hybrid | Phase 4 DESIGN weights; embedding slot is hashing-v1 unless MiniLM is configured |

The production hybrid ranker’s embedding slot defaults to hashing-v1. This report therefore does **not** call that hybrid “semantic hybrid.”

## Metrics

Implemented in `app/evaluation/metrics.py`. Precision/Recall/MRR use relevance ≥ 2. NDCG uses graded 0–3 gains `(2^rel - 1) / log2(rank+1)`.

Primary table: **held-out test (3 queries)**.

## Retrieval Recall

Live pgvector SQL retrieval was run in Phase 7 on stored MiniLM vectors. See the Phase 7 table below.

In-memory cosine top-N on the 32 labeled jobs, hashing-v1, test split:

| Candidate N | Mean recall of relevant jobs |
|---|---|
| 20 | 0.917 |
| 50 | 1.000 |
| 100 | 1.000 |

The fixture has only 32 jobs, so N=50 and N=100 include the entire pool.

Phase 7 in-memory MiniLM cosine (test): Recall@20 = 1.000. Validation: Recall@20 = 0.931.

Phase 7 live PostgreSQL pgvector (`sentence-transformers:all-MiniLM-L6-v2`, 32 stored vectors):

| Split | Recall@20 | Recall@50 | Recall@100 |
|---|---|---|---|
| test | 1.000 | 1.000 | 1.000 |
| validation | 0.931 | 1.000 | 1.000 |

Sample match metadata: `retrieval = pgvector`. This is not the in-memory ranker.

## Aggregate Results

Held-out **test** (3 profiles):

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| skills | 0.467 | 0.589 | 0.586 | 0.778 |
| tfidf | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 (lexical) | 0.533 | 0.633 | 0.691 | 1.000 |
| semantic (`all-MiniLM-L6-v2`) | 0.667 | 0.811 | 0.833 | 1.000 |
| hybrid (DESIGN + hashing-v1) | 0.600 | 0.933 | 0.852 | 1.000 |
| hybrid (DESIGN + MiniLM) | 0.667 | 0.878 | 0.892 | 1.000 |

**Validation** (5 profiles) does not agree on the winner:

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| skills | 0.320 | 0.612 | 0.551 | 0.850 |
| tfidf | 0.520 | 0.634 | 0.685 | 1.000 |
| hashing-v1 (lexical) | 0.480 | 0.629 | 0.663 | 1.000 |
| semantic (`all-MiniLM-L6-v2`) | 0.560 | 0.767 | 0.769 | 1.000 |
| hybrid (DESIGN + hashing-v1) | 0.440 | 0.589 | 0.677 | 1.000 |
| hybrid (DESIGN + MiniLM) | 0.520 | 0.629 | 0.713 | 1.000 |

On the Phase 5 hashing-only comparison, validation favored pairwise TF-IDF over hashing hybrid. After Phase 7, MiniLM-only NDCG@10 (0.769) is highest on validation. Structured hybrid around MiniLM then drops to 0.713. The study remains directional.

All eight queries together: TF-IDF P@5 0.525 / NDCG@10 0.712; hybrid P@5 0.500 / NDCG@10 0.742.

## Per-Profile Results

Test NDCG@10:

| Profile | skills | tfidf | hashing-v1 | hybrid |
|---|---|---|---|---|
| r_de_mid | 0.721 | 0.821 | 0.851 | 0.866 |
| r_ds_senior | 0.483 | 0.726 | 0.663 | 0.832 |
| r_be_mid | 0.555 | 0.725 | 0.559 | 0.858 |

Skill overlap is weakest on the senior NLP profile (MRR 0.333): incidental `python` / `sql` tokens in bait postings outrank real science roles.

## Ablation Study

Test split, hashing-v1 as the embedding component, DESIGN weight proportions then renormalized when a signal is dropped:

| Combination | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| lexical hashing only | 0.533 | 0.633 | 0.691 | 1.000 |
| hashing + skills | 0.533 | 0.783 | 0.746 | 1.000 |
| hashing + skills + recency | 0.467 | 0.717 | 0.713 | 1.000 |
| full hybrid (hashing + skills + recency + experience + location) | 0.600 | 0.933 | 0.852 | 1.000 |

Phase 7 MiniLM ablations, same DESIGN proportions, test split:

| Combination | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| semantic only | 0.667 | 0.811 | 0.833 | 1.000 |
| semantic + skills | 0.600 | 0.811 | 0.843 | 1.000 |
| semantic + skills + recency | 0.533 | 0.728 | 0.806 | 1.000 |
| full hybrid (MiniLM + skills + recency + experience + location) | 0.667 | 0.878 | 0.892 | 1.000 |

Recency again lowered NDCG@10 before location/experience recovered the full hybrid. Production weights were not changed.

Adding skills to hashing improved recall. Adding recency then *lowered* NDCG@10 on this fixture (new but weak intern/clinical posts). Experience and location recovered the full hybrid score on the test profiles, which all have preferences.

## Component Coverage

Same 32 jobs for every query:

| Signal | Availability |
|---|---|
| extracted/persisted skills | 93.8% (30/32) |
| posted_at | 100% |
| experience_level | 90.6% (29/32) |
| location preference on test profiles | 100% |
| experience preference on test profiles | 100% |

Nurse and sales postings contribute the skill gaps. Missing experience is concentrated on `other` jobs.

## Error Analysis

Examples from the test split. The system was not changed in response.

1. **Skill overlap overvalues lexical bait.** For `r_ds_senior`, skills ranks Clinical Data Coordinator (#15, label 0) first and Marketing Data Intern (#29, label 0) second because the text mentions `python` and `sql`. Senior NLP roles sit at ranks 3–4.
2. **Skill overlap ignores seniority.** For `r_de_mid`, Data Engineer Intern (#14, label 0) is rank 2. The intern posting shares Spark/Airflow tokens with a mid engineer.
3. **Pairwise TF-IDF overvalues title/token overlap across families.** For `r_ds_senior`, Senior Data Engineer (#2, label 0) is rank 2, ahead of mid Data Scientist (#4, label 2). “Senior” plus “data” dominates the two-document cosine.
4. **Lexical hashing is not semantic.** For `r_ds_senior`, hashing-v1 places Junior Data Analyst (#3, label 0) at rank 2. Shared tokens beat role family.
5. **Recency can promote weak new posts.** Ablation NDCG@10 fell after adding recency. Jobs #15 and #29 are one day old.
6. **Hybrid still cannot drop bait completely.** For `r_ds_senior`, hybrid places the marketing intern and clinical coordinator at ranks 3–4 even after location/experience penalties.

## Limitations

- Eight synthetic queries, three of them held out. Directional only.
- Complete judgments on 32 jobs, not a live market snapshot.
- hashing-v1 is a lexical hashed-token vector. It is not a sentence embedding.
- sentence-transformers 3.1.1 + torch 2.8.0 + `all-MiniLM-L6-v2` (384-d, cosine, `normalize_embeddings=True`) were run in Phase 7.
- Live pgvector recall was measured on the 32 fixture jobs after storing MiniLM vectors.
- Authoring used a role-family rubric. That is independent of model scores but is still one labeler’s rule, not a multi-recruiter panel.
- Optional weight search used five validation queries. That is too small to adopt new defaults.

## Reproduction Instructions

```bash
python scripts/evaluate_ranking.py --dataset data/evaluation/v1 --split test --output artifacts/evaluation
```

Optional (does not change production weights):

```bash
python scripts/evaluate_ranking.py --split test --tune
```

Phase 7 MiniLM + pgvector:

```bash
pip install -r requirements-semantic.txt
EMBEDDING_PROVIDER=sentence-transformers python scripts/evaluate_ranking.py --split test --output artifacts/evaluation/phase7/test
EMBEDDING_PROVIDER=sentence-transformers python scripts/evaluate_pgvector.py --split test
```

If sentence-transformers is missing, the CLI still prints `NOT RUN` for the semantic method instead of substituting hashing-v1.
