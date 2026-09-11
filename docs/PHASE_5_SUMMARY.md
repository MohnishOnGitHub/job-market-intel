# Phase 5 Summary

## Goal

Build a reproducible offline evaluation framework that measures TF-IDF, skill overlap, lexical hashing-v1, optional sentence-transformer similarity, and the Phase 4 hybrid ranker — without changing production scoring.

## Dataset

`data/evaluation/v1`: 8 synthetic profiles, 32 fixture jobs, 256 complete judgments. Profile-level split (5 validation, 3 test). Not live Adzuna data and not real applicants.

## Labeling Scale

0 irrelevant, 1 weak, 2 relevant, 3 highly relevant. Binary metrics use ≥ 2. Guide: `docs/EVALUATION_GUIDE.md`. Labels come from a role-family/seniority rubric plus documented overrides. They are not model scores.

## Systems Evaluated

- skills
- pairwise TF-IDF cosine
- hashing-v1 (lexical hashing retrieval)
- sentence-transformer semantic similarity (attempted; not run)
- hybrid with DESIGN weights and hashing-v1 as the embedding component

## Sentence Transformer Model

Intended: `all-MiniLM-L6-v2`, cosine, `normalize_embeddings=True`.

**NOT RUN.** `sentence-transformers` / `torch` are not installed. Hashing-v1 was not substituted into the semantic method.

## Metrics

Precision@5, Precision@10, Recall@10, NDCG@5, NDCG@10, MRR. Implemented in project code and unit-tested.

## Retrieval Evaluation

In-memory hashing-v1 cosine top-N on the 32-job fixture (test): Recall@20 = 0.917, Recall@50 = 1.0, Recall@100 = 1.0.

Live pgvector: **NOT RUN**.

## Ranking Results

Held-out test (3 queries):

| Method | P@5 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|
| skills | 0.467 | 0.589 | 0.586 | 0.778 |
| tfidf | 0.533 | 0.783 | 0.757 | 1.000 |
| hashing-v1 | 0.533 | 0.633 | 0.691 | 1.000 |
| semantic | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| hybrid | 0.600 | 0.933 | 0.852 | 1.000 |

Validation (5 queries): TF-IDF NDCG@10 0.685 > hybrid 0.677. Directional only.

## Ablation Results

Test, hashing-v1 embedding slot: hashing only 0.691 NDCG@10; +skills 0.746; +recency 0.713; full hybrid 0.852. Recency hurt this fixture. Sentence-transformer ablations NOT RUN.

## Weight Search

Optional coarse grid on validation, scored once on test. Best validation weights put recency at 0. Test NDCG@10 moved from 0.852 (DESIGN) to 0.909 (tuned). Five validation queries are too few to adopt that vector. **Production defaults unchanged.**

## Error Analysis

Skill overlap ranks clinical/marketing bait first for the senior NLP profile. TF-IDF promotes “Senior Data Engineer” for a scientist. Hashing-v1 is lexical, not semantic. Recency boosts one-day-old weak posts. Hybrid still cannot fully suppress bait. Details in `docs/EVALUATION.md`.

## Performance

On the 32-job fixture, mean per-query latency was a few milliseconds for hashing/hybrid/skills and ~29 ms for pairwise TF-IDF. Quality, not microseconds, was the objective.

## Tests

Metric identities, dataset validation, unknown/duplicate IDs, authoring rubric, method adapters, deterministic hashing order, split isolation, coverage, CLI help, committed JSON load.

## Test Results

```text
138 passed, 13 skipped, 2 warnings
```

The 13 skips are the same PostgreSQL tests as Phase 4 (no `TEST_DATABASE_URL`, Docker daemon not running). They were not treated as passes.

## Conclusions

1. On the tiny held-out test set, hybrid beat TF-IDF and lexical hashing. On validation, TF-IDF won. Do not declare a production winner.
2. hashing-v1 did not beat pairwise TF-IDF on NDCG@10 (test 0.691 vs 0.757). Lexical hashing is not a semantic model.
3. Semantic sentence-transformer comparison is unknown here.
4. Candidate-pool recall at 20 was 0.917 for hashing-v1 on 32 jobs; pgvector was not measured.
5. Skills help hashing; recency can hurt; location/experience helped the test profiles because every profile had preferences.
6. Important failures remain: taxonomy bait, seniority-blind skill overlap, lexical family confusion.

## Known Limitations

Small synthetic benchmark. No sentence-transformer. No pgvector. One labeler. Authoring rubric is structured, not a recruiter panel.

## Recommendations for Phase 6

Do not change hybrid defaults from this study. If more labels appear, re-run semantic evaluation and keep production changes explicit. Phase 6 should stay on market analytics / skill-gap product work, not silent reranker swaps.

## Files Added

```text
app/evaluation/__init__.py
app/evaluation/metrics.py
app/evaluation/dataset.py
app/evaluation/methods.py
app/evaluation/runner.py
app/evaluation/weights.py
app/evaluation/v1_authoring.py
data/evaluation/README.md
data/evaluation/v1/dataset.json
data/evaluation/v1/labels.csv
docs/EVALUATION_GUIDE.md
docs/EVALUATION.md
docs/PHASE_5_SUMMARY.md
scripts/evaluate_ranking.py
tests/unit/test_evaluation_metrics.py
tests/unit/test_evaluation_dataset.py
tests/unit/test_evaluation_methods.py
tests/unit/test_evaluation_runner.py
tests/unit/test_evaluate_script.py
artifacts/evaluation/results.json
artifacts/evaluation/per_query.csv
artifacts/evaluation/validation/
artifacts/evaluation/all/
```

## Files Modified

```text
app/main.py
scripts/generate_embeddings.py
README.md
pytest.ini
.gitignore
```
