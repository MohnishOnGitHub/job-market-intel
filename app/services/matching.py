from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from app.core.config import get_settings
from app.db.repositories.embeddings import EmbeddingRepository
from app.db.repositories.jobs import JobRepository
from app.schemas.hybrid_match import HybridMatchResponse
from app.schemas.job import Job
from app.services.embedding_provider import (
    EmbeddingProvider,
    cosine_similarity,
    get_embedding_provider,
)
from app.services.embedding_text import build_embedding_text
from app.services.hybrid_ranking import (
    default_ranking_weights,
    normalize_experience_level,
    rank_hybrid_jobs,
)

RETRIEVAL_PGVECTOR = "pgvector"
RETRIEVAL_IN_MEMORY = "in_memory_fallback"


def match_resume_hybrid(
    resume_text: str,
    *,
    job_repository: JobRepository,
    embedding_repository: Optional[EmbeddingRepository] = None,
    provider: Optional[EmbeddingProvider] = None,
    jobs: Optional[Sequence[Job]] = None,
    preferred_location: Optional[str] = None,
    preferred_experience: Optional[str] = None,
    limit: int = 20,
    candidate_count: Optional[int] = None,
    now: Optional[datetime] = None,
) -> HybridMatchResponse:
    """Retrieve candidates, then rerank with structured hybrid features."""
    embedder = provider or get_embedding_provider()
    settings = get_settings()
    retrieval_limit = candidate_count or settings.candidate_count
    retrieval_limit = max(retrieval_limit, limit)
    query_vector = embedder.embed_query(resume_text)

    candidates: List[Job] = []
    semantic_scores = {}
    retrieval = RETRIEVAL_IN_MEMORY

    if embedding_repository is not None:
        retrieved = embedding_repository.retrieve_candidates(
            query_vector,
            embedder.name,
            retrieval_limit,
        )
        if retrieved:
            retrieval = RETRIEVAL_PGVECTOR
            candidates = [item.job for item in retrieved]
            semantic_scores = {
                item.job.id: item.semantic_score for item in retrieved
            }

    if not candidates:
        candidates = list(jobs if jobs is not None else job_repository.list_jobs())
        retrieval = RETRIEVAL_IN_MEMORY
        texts = [
            build_embedding_text(
                title=job.title,
                company=job.company,
                location=job.location,
                description=job.description,
                skills=job.persisted_skills or [],
            )
            for job in candidates
        ]
        vectors = embedder.embed_documents(texts)
        semantic_scores = {
            job.id: cosine_similarity(query_vector, vector)
            for job, vector in zip(candidates, vectors)
        }

    weights = default_ranking_weights().without_unused(
        use_experience=normalize_experience_level(preferred_experience) is not None,
        use_location=bool((preferred_location or "").strip()),
    )
    results = rank_hybrid_jobs(
        resume_text,
        candidates,
        semantic_scores,
        preferred_location=preferred_location,
        preferred_experience=preferred_experience,
        weights=weights,
        now=now,
        limit=limit,
    )
    return HybridMatchResponse(
        results=results,
        ranking="hybrid",
        embedding_model=embedder.name,
        retrieval=retrieval,
        candidate_count=len(candidates),
        weights=weights.as_dict(),
    )
