from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from app.evaluation.dataset import EvaluationResume
from app.schemas.job import Job
from app.services.embedding_provider import (
    EmbeddingProvider,
    HashingEmbeddingProvider,
    SentenceTransformerProvider,
    cosine_similarity,
)
from app.services.embedding_text import build_embedding_text
from app.services.hybrid_ranking import RankingWeights, rank_hybrid_jobs
from app.services.ranking import pairwise_tfidf_score
from app.services.skill_extractor import (
    compute_skill_score,
    extract_skills,
    skill_overlap,
)

DESIGN_WEIGHTS = RankingWeights(0.50, 0.25, 0.10, 0.10, 0.05)


@dataclass(frozen=True)
class RankedItem:
    job_id: int
    score: float


@dataclass
class MethodResult:
    name: str
    display_name: str
    ranked: List[RankedItem]
    ran: bool = True
    skip_reason: Optional[str] = None
    latency_ms: Optional[float] = None


def stable_rank(pairs: Sequence[Tuple[int, float]]) -> List[RankedItem]:
    """Sort by score descending, job_id ascending for ties."""
    ordered = sorted(pairs, key=lambda item: (-item[1], item[0]))
    return [RankedItem(job_id=job_id, score=score) for job_id, score in ordered]


def job_skills(job: Job) -> List[str]:
    if job.persisted_skills is not None:
        return list(job.persisted_skills)
    return extract_skills(job.description)


def rank_skills(resume: EvaluationResume, jobs: Sequence[Job]) -> List[RankedItem]:
    resume_skills = extract_skills(resume.text)
    pairs = []
    for job in jobs:
        skills = job_skills(job)
        matched, _missing = skill_overlap(resume_skills, skills)
        pairs.append((job.id, compute_skill_score(matched, skills)))
    return stable_rank(pairs)


def rank_tfidf(resume: EvaluationResume, jobs: Sequence[Job]) -> List[RankedItem]:
    pairs = [
        (job.id, pairwise_tfidf_score(resume.text, (job.description or "").lower()))
        for job in jobs
    ]
    return stable_rank(pairs)


def rank_embedding(
    resume: EvaluationResume,
    jobs: Sequence[Job],
    provider: EmbeddingProvider,
) -> List[RankedItem]:
    query = provider.embed_query(resume.text)
    texts = [
        build_embedding_text(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            skills=job_skills(job),
        )
        for job in jobs
    ]
    vectors = provider.embed_documents(texts)
    pairs = [
        (job.id, cosine_similarity(query, vector))
        for job, vector in zip(jobs, vectors)
    ]
    return stable_rank(pairs)


def rank_hybrid(
    resume: EvaluationResume,
    jobs: Sequence[Job],
    provider: EmbeddingProvider,
    *,
    weights: Optional[RankingWeights] = None,
    now: Optional[datetime] = None,
    use_skills: bool = True,
    use_recency: bool = True,
    use_experience: bool = True,
    use_location: bool = True,
) -> List[RankedItem]:
    query = provider.embed_query(resume.text)
    semantic_scores: Dict[int, float] = {}
    for job in jobs:
        text = build_embedding_text(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            skills=job_skills(job),
        )
        semantic_scores[job.id] = cosine_similarity(
            query, provider.embed_documents([text])[0]
        )
    resolved = (weights or DESIGN_WEIGHTS)
    resolved = RankingWeights(
        semantic=resolved.semantic,
        skill=resolved.skill if use_skills else 0.0,
        experience=resolved.experience if use_experience else 0.0,
        recency=resolved.recency if use_recency else 0.0,
        location=resolved.location if use_location else 0.0,
    ).normalized()
    preferred_location = resume.preferred_location if use_location else None
    preferred_experience = resume.preferred_experience if use_experience else None
    ranked = rank_hybrid_jobs(
        resume.text,
        jobs,
        semantic_scores,
        preferred_location=preferred_location,
        preferred_experience=preferred_experience,
        weights=resolved,
        now=now,
    )
    return [RankedItem(job_id=item.job_id, score=item.hybrid_score) for item in ranked]


def hashing_provider() -> HashingEmbeddingProvider:
    return HashingEmbeddingProvider(dimension=256)


def try_sentence_transformer(
    model_name: str = "all-MiniLM-L6-v2",
) -> Tuple[Optional[SentenceTransformerProvider], Optional[str]]:
    try:
        provider = SentenceTransformerProvider(model_name)
    except Exception as exc:
        return None, str(exc)
    return provider, None


def candidate_ids(ranked: Sequence[RankedItem], limit: int) -> List[int]:
    return [item.job_id for item in ranked[:limit]]
