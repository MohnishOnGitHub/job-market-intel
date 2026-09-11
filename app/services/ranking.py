from __future__ import annotations

from typing import List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.job import Job
from app.schemas.match import MatchedJob
from app.services.skill_extractor import (
    compute_skill_score,
    extract_skills,
    skill_overlap,
)

# Phase 1 preserves the current un-evaluated heuristic weights.
TFIDF_WEIGHT = 0.7
SKILL_WEIGHT = 0.3


def pairwise_tfidf_score(resume_text: str, job_text: str) -> float:
    """Pairwise TF-IDF cosine similarity.

    Fits a new vectorizer on exactly two documents. This is the current
    working baseline and must not be replaced with corpus-level TF-IDF
    during Phase 1.
    """
    left = resume_text or ""
    right = job_text or ""
    if not left.strip() or not right.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([left, right])
        score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    except ValueError:
        return 0.0

    return round(float(score), 2)


def compute_hybrid_score(match_score: float, skill_score: float) -> float:
    return round(TFIDF_WEIGHT * match_score + SKILL_WEIGHT * skill_score, 3)


def rank_tfidf(resume_text: str, jobs: Sequence[Job]) -> List[MatchedJob]:
    """Independent lexical baseline. Do not replace this with hybrid ranking."""
    return rank_jobs(resume_text, jobs)


def rank_jobs(resume_text: str, jobs: Sequence[Job]) -> List[MatchedJob]:
    resume_skills = extract_skills(resume_text)
    results: List[MatchedJob] = []

    for job in jobs:
        job_text = (job.description or "").lower()
        match_score = pairwise_tfidf_score(resume_text, job_text)
        if job.persisted_skills is not None:
            job_skills = list(job.persisted_skills)
        else:
            job_skills = extract_skills(job.description)
        matched_skills, missing_skills = skill_overlap(resume_skills, job_skills)
        skill_score = compute_skill_score(matched_skills, job_skills)
        hybrid_score = compute_hybrid_score(match_score, skill_score)

        results.append(
            MatchedJob(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                match_score=match_score,
                skill_score=round(skill_score, 2),
                hybrid_score=hybrid_score,
                skills=job_skills,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
            )
        )

    return sorted(results, key=lambda item: item.hybrid_score, reverse=True)
