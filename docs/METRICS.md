# Metric definitions

All market counts are SQL aggregates over **active** jobs (`jobs.active = TRUE`). Title and location filters are case-insensitive `ILIKE` contains matches. They are not a job-family classifier.

Experience filters, when present, match the stored `experience_level` string. `unknown` means the column is null or blank. Experience is never inferred from the description.

## Overview

| Field | Definition |
|---|---|
| Active jobs | `COUNT(*)` of filtered active jobs |
| Jobs with skill data | Active jobs with at least one `job_skills` row |
| Canonical skills | `COUNT(*)` from the `skills` table (synced taxonomy). 0 if `sync_skills` has not been run |
| Most demanded skill | Skill with the highest distinct-job count after filters |
| Latest ingestion | `MAX(completed_at)` on `ingestion_runs` in `completed` or `completed_with_errors` |
| Latest job seen | `MAX(last_seen_at)` on filtered active jobs |

## Skill demand

| Field | Definition |
|---|---|
| Job count | Distinct active jobs linked to that canonical skill |
| Job share | `job_count / filtered active jobs` |

This is a snapshot, not a growth rate.

## Skill categories

A job is counted once in a category if it has **at least one** canonical skill in that category. Share uses the same filtered active-job denominator.

This is not a count of skill mentions (a job with Python and Java still counts once for Programming).

## Experience mix

`GROUP BY` stored `experience_level`. Blank or null → `unknown`. No years are parsed from prose.

## Locations

`COALESCE(location_normalized, location_raw)` after trim. Blank → `unknown`. These are source strings, not geocoded metro areas.

## Companies

Active jobs grouped by trimmed `company`. Blank companies are excluded from the table and counted separately as `jobs_without_company`.

## Posting age

Uses `posted_at` only.

| Bucket | Age |
|---|---|
| 0–7 days | `posted_at` within 7 days of query time |
| 8–30 days | 8 to 30 days |
| 31–60 days | 31 to 60 days |
| 61+ days | older than 60 days |
| unknown | `posted_at` is null |

This is not a forecast and not a trend.

## Match scores

| Score | Meaning |
|---|---|
| TF-IDF match score | `0.7 * pairwise TF-IDF cosine + 0.3 * skill overlap` |
| Hybrid match score | Weighted sum of similarity, skills, recency, experience, location |
| Skill overlap | `matched / job_skills`, else 0 |

Neither score is a hiring probability. hashing-v1 similarity is lexical hashing retrieval. Unused hybrid preferences are omitted from the weight mix and shown as N/A in the UI.
