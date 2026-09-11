# Evaluation fixtures

Versioned, committed ranking judgments. Evaluation does not need production PostgreSQL.

```text
data/evaluation/v1/
  dataset.json      resumes, jobs, labels, metadata
  labels.csv        resume_id, job_id, relevance_label, notes, labeler, split
```

Regenerate from the authoring module:

```bash
python scripts/evaluate_ranking.py --write-fixture
```

v1 profiles and jobs are synthetic fixtures. They are not live Adzuna rows and not real applicants.

See `docs/EVALUATION_GUIDE.md` for label definitions.
