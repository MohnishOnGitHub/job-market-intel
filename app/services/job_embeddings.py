from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.db.repositories.embeddings import EmbeddingRepository
from app.schemas.job import Job
from app.services.embedding_provider import EmbeddingProvider, get_embedding_provider
from app.services.embedding_text import build_embedding_text, embedding_content_hash

logger = logging.getLogger("app.services.job_embeddings")


@dataclass
class EmbeddingGenerationReport:
    jobs_seen: int = 0
    jobs_written: int = 0
    jobs_unchanged: int = 0
    embedding_model: str = ""


class JobEmbeddingService:
    def __init__(
        self,
        embedding_repository: EmbeddingRepository,
        provider: Optional[EmbeddingProvider] = None,
    ) -> None:
        self.embedding_repository = embedding_repository
        self.provider = provider or get_embedding_provider()

    def embed_job(self, job: Job) -> bool:
        """Write one job embedding. Returns True when a vector was stored."""
        text = _job_embedding_text(job)
        digest = embedding_content_hash(text, self.provider.name)
        existing = self.embedding_repository.get_hashes(self.provider.name)
        if existing.get(job.id) == digest:
            return False
        vector = self.provider.embed_documents([text])[0]
        self.embedding_repository.upsert(
            job.id, self.provider.name, vector, digest
        )
        return True

    def embed_jobs(
        self,
        jobs: Sequence[Job],
        only_missing: bool = False,
    ) -> EmbeddingGenerationReport:
        report = EmbeddingGenerationReport(
            jobs_seen=len(jobs),
            embedding_model=self.provider.name,
        )
        existing = self.embedding_repository.get_hashes(self.provider.name)
        pending: List[Job] = []
        pending_hashes: List[str] = []
        for job in jobs:
            text = _job_embedding_text(job)
            digest = embedding_content_hash(text, self.provider.name)
            current = existing.get(job.id)
            if current == digest:
                report.jobs_unchanged += 1
                continue
            if only_missing and current is not None:
                report.jobs_unchanged += 1
                continue
            pending.append(job)
            pending_hashes.append(digest)

        if not pending:
            return report

        vectors = self.provider.embed_documents(
            [_job_embedding_text(job) for job in pending]
        )
        for job, vector, digest in zip(pending, vectors, pending_hashes):
            self.embedding_repository.upsert(
                job.id, self.provider.name, vector, digest
            )
            report.jobs_written += 1
        logger.info(
            "event=job_embeddings_generated model=%s written=%s unchanged=%s",
            self.provider.name,
            report.jobs_written,
            report.jobs_unchanged,
        )
        return report


def _job_embedding_text(job: Job) -> str:
    return build_embedding_text(
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        skills=job.persisted_skills or [],
    )
