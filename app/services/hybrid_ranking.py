from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Mapping, Optional, Sequence

from app.core.config import get_settings
from app.schemas.hybrid_match import HybridMatchedJob, ScoreBreakdown
from app.schemas.job import Job
from app.services.skill_extractor import (
    compute_skill_score,
    extract_skills,
    skill_overlap,
)

EXPERIENCE_LEVELS = (
    "internship",
    "entry",
    "junior",
    "mid",
    "senior",
    "lead",
)

REMOTE_TOKENS = ("remote", "anywhere", "work from home", "wfh")
DEFAULT_TAU_DAYS = 30.0
MISSING_RECENCY_SCORE = 0.5
MISSING_EXPERIENCE_SCORE = 0.5
MISSING_LOCATION_SCORE = 0.5


@dataclass(frozen=True)
class RankingWeights:
    semantic: float
    skill: float
    experience: float
    recency: float
    location: float

    def normalized(self) -> "RankingWeights":
        total = (
            self.semantic
            + self.skill
            + self.experience
            + self.recency
            + self.location
        )
        if total <= 0:
            raise ValueError("ranking weights must sum to a positive number")
        return RankingWeights(
            semantic=self.semantic / total,
            skill=self.skill / total,
            experience=self.experience / total,
            recency=self.recency / total,
            location=self.location / total,
        )

    def without_unused(
        self,
        *,
        use_experience: bool,
        use_location: bool,
    ) -> "RankingWeights":
        return RankingWeights(
            semantic=self.semantic,
            skill=self.skill,
            experience=self.experience if use_experience else 0.0,
            recency=self.recency,
            location=self.location if use_location else 0.0,
        ).normalized()

    def as_dict(self) -> dict[str, float]:
        return {
            "semantic": round(self.semantic, 4),
            "skill": round(self.skill, 4),
            "experience": round(self.experience, 4),
            "recency": round(self.recency, 4),
            "location": round(self.location, 4),
        }


def default_ranking_weights() -> RankingWeights:
    settings = get_settings()
    return RankingWeights(
        semantic=settings.rank_weight_semantic,
        skill=settings.rank_weight_skill,
        experience=settings.rank_weight_experience,
        recency=settings.rank_weight_recency,
        location=settings.rank_weight_location,
    ).normalized()


def normalize_experience_level(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip().lower()
    aliases = {
        "intern": "internship",
        "entry-level": "entry",
        "entry level": "entry",
        "jr": "junior",
        "mid-level": "mid",
        "mid level": "mid",
        "intermediate": "mid",
        "sr": "senior",
        "staff": "lead",
        "principal": "lead",
    }
    cleaned = aliases.get(cleaned, cleaned)
    if cleaned in EXPERIENCE_LEVELS:
        return cleaned
    return None


def recency_score(
    posted_at: Optional[datetime],
    now: Optional[datetime] = None,
    tau_days: float = DEFAULT_TAU_DAYS,
) -> float:
    """Bounded exponential decay. Missing dates are a documented 0.5 fallback."""
    if posted_at is None:
        return MISSING_RECENCY_SCORE
    moment = now or datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (moment - posted_at).total_seconds() / 86400.0)
    return _clip_unit(math.exp(-age_days / tau_days))


def experience_score(
    job_level: Optional[str],
    preferred_level: Optional[str],
) -> Optional[float]:
    """Return None when the user did not provide a usable preference."""
    preferred = normalize_experience_level(preferred_level)
    if preferred is None:
        return None
    job = normalize_experience_level(job_level)
    if job is None:
        return MISSING_EXPERIENCE_SCORE
    distance = abs(EXPERIENCE_LEVELS.index(job) - EXPERIENCE_LEVELS.index(preferred))
    if distance == 0:
        return 1.0
    if distance == 1:
        return 0.75
    if distance == 2:
        return 0.5
    return 0.25


def location_score(
    job_location: Optional[str],
    preferred_location: Optional[str],
) -> Optional[float]:
    """Return None when the user did not provide a location preference."""
    preferred = (preferred_location or "").strip().lower()
    if not preferred:
        return None
    job = (job_location or "").strip().lower()
    if not job:
        return MISSING_LOCATION_SCORE
    if job == preferred:
        return 1.0
    if _is_remote(preferred) and _is_remote(job):
        return 1.0
    if preferred in job or job in preferred:
        return 0.5
    if "hybrid" in job:
        return 0.5
    return 0.0


def compute_hybrid_rank_score(
    *,
    semantic_score: float,
    skill_score: float,
    experience_score_value: float,
    recency_score_value: float,
    location_score_value: float,
    weights: RankingWeights,
) -> float:
    return round(
        weights.semantic * semantic_score
        + weights.skill * skill_score
        + weights.experience * experience_score_value
        + weights.recency * recency_score_value
        + weights.location * location_score_value,
        3,
    )


def rank_hybrid_jobs(
    resume_text: str,
    jobs: Sequence[Job],
    semantic_scores: Mapping[int, float],
    *,
    preferred_location: Optional[str] = None,
    preferred_experience: Optional[str] = None,
    weights: Optional[RankingWeights] = None,
    now: Optional[datetime] = None,
    tau_days: Optional[float] = None,
    limit: Optional[int] = None,
) -> List[HybridMatchedJob]:
    resume_skills = extract_skills(resume_text)
    loc_pref = (preferred_location or "").strip() or None
    exp_pref = normalize_experience_level(preferred_experience)
    use_location = loc_pref is not None
    use_experience = exp_pref is not None
    resolved_weights = (weights or default_ranking_weights()).without_unused(
        use_experience=use_experience,
        use_location=use_location,
    )
    decay = get_settings().recency_tau_days if tau_days is None else tau_days

    results: List[HybridMatchedJob] = []
    for job in jobs:
        if job.persisted_skills is not None:
            job_skills = list(job.persisted_skills)
        else:
            job_skills = extract_skills(job.description)
        matched_skills, missing_skills = skill_overlap(resume_skills, job_skills)
        skill_value = compute_skill_score(matched_skills, job_skills)
        semantic_value = _clip_unit(float(semantic_scores.get(job.id, 0.0)))
        recency_value = recency_score(job.posted_at, now=now, tau_days=decay)
        if use_experience:
            experience_value = experience_score(job.experience_level, exp_pref) or 0.0
        else:
            experience_value = 0.0
        if use_location:
            location_value = location_score(job.location, loc_pref) or 0.0
        else:
            location_value = 0.0
        hybrid = compute_hybrid_rank_score(
            semantic_score=semantic_value,
            skill_score=skill_value,
            experience_score_value=experience_value,
            recency_score_value=recency_value,
            location_score_value=location_value,
            weights=resolved_weights,
        )
        results.append(
            HybridMatchedJob(
                job_id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                hybrid_score=hybrid,
                components=ScoreBreakdown(
                    semantic=round(semantic_value, 3),
                    skills=round(skill_value, 3),
                    experience=round(experience_value, 3),
                    recency=round(recency_value, 3),
                    location=round(location_value, 3),
                ),
                skills=job_skills,
                matched_skills=matched_skills,
                missing_skills=missing_skills,
            )
        )

    ranked = sorted(results, key=lambda item: item.hybrid_score, reverse=True)
    if limit is not None:
        return ranked[:limit]
    return ranked


def _is_remote(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in REMOTE_TOKENS)


def _clip_unit(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)
