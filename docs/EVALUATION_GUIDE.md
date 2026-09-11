# Evaluation Labeling Guide

This guide is the source of truth for v1 relevance labels. Labels are human-authored judgments. They are **not** derived from TF-IDF, hashing-v1, sentence-transformer, or hybrid scores.

All v1 résumés are **synthetic profiles**. They are not real applicants.

## Scale

| Label | Name | Meaning |
|---|---|---|
| 3 | Highly relevant | Same role family and aligned seniority. Core technical work matches the profile. A recruiter would shortlist. |
| 2 | Relevant | The candidate is reasonably qualified. One meaningful gap is acceptable (adjacent family, one seniority step, or a stack gap that can be learned). |
| 1 | Weak | Some overlap exists, but family, seniority, or core work is poorly aligned. A stretch, intern, or neighboring function. |
| 0 | Irrelevant | Wrong role family, or a non-engineering/non-analytics job, or a lexical lookalike that is not the work. |

## Binary threshold

For Precision, Recall, and MRR:

```text
relevant = relevance >= 2
```

NDCG uses the graded 0–3 scale.

## Role families used while authoring

| Family | Examples |
|---|---|
| `da` | Data Analyst, BI Developer |
| `analytics` | Analytics Engineer (adjacent to DA and DE) |
| `ds` | Data Scientist, NLP research scientist |
| `mle` | Machine Learning Engineer, MLOps |
| `de` | Data Engineer |
| `be` | Backend, platform, full-stack software engineering |
| `other` | Nurse, sales, PM, clinical admin, marketing intern, generic DevOps |

Adjacent families for the v1 rubric:

- DA ↔ analytics
- DE ↔ analytics
- DS ↔ MLE
- Backend is adjacent only to backend

Wrong family is 0 unless an explicit override is documented.

## Seniority

`internship`, `entry`, `junior`, `mid`, `senior`, `lead`

Same family:

- exact seniority → 3
- one step → 2
- two steps → 1
- farther → 0

Adjacent family:

- exact seniority → 2
- one step → 1
- farther → 0

## Overrides

A small set of pairs is overridden when the mechanical family/seniority rule would hide a real judgment. Examples:

- Clinical Data Coordinator mentioning “python sql” → 0 for every profile (lexical bait, not a software role).
- Marketing data intern → 0/1, not a data-engineering job.
- Go/Java backend for a Python API engineer → 1, not 3.
- NLP research scientist for the senior NLP profile → 3.

Overrides live in `app/evaluation/v1_authoring.py` (`LABEL_OVERRIDES`) and are copied into `data/evaluation/v1/labels.csv` notes.

## What not to do

- Do not copy production `hybrid_score`, TF-IDF cosine, or embedding cosine into the label column.
- Do not treat title keyword overlap as sufficient for 3 if the work is a different occupation.
- Do not invent years of experience that the posting does not state.
- Do not present synthetic profiles as real people.

## Split

v1 uses a **profile-level** split so a résumé never appears in both validation and test.

- validation: `r_da_junior`, `r_ds_mid`, `r_de_senior`, `r_mle_mid`, `r_da_mid`
- test: `r_de_mid`, `r_ds_senior`, `r_be_mid`

Weight search, if run, may use validation only. Test is for a single final look. The v1 query count is small; treat tuning as directional, not statistically significant.
