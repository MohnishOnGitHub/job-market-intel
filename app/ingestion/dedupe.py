from __future__ import annotations

from typing import Optional, Tuple

from app.ingestion.models import NormalizedJob

Identity = Tuple[str, Optional[str], Optional[str], Optional[str]]


def identity_keys(job: NormalizedJob) -> Identity:
    """Deterministic identity, in lookup priority order.

    1. (source, source_job_id) when source_job_id is present
    2. canonical source_url when present
    3. content_hash only when both identity keys are missing

    Company + title alone is never an identity.
    """
    return (
        job.source,
        job.source_job_id,
        job.source_url,
        job.content_hash if not job.source_job_id and not job.source_url else None,
    )


def primary_identity(job: NormalizedJob) -> Tuple[str, str]:
    if job.source_job_id:
        return ("source_job_id", job.source_job_id)
    if job.source_url:
        return ("source_url", job.source_url)
    return ("content_hash", job.content_hash)
