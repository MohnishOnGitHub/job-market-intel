from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    semantic: float
    skills: float
    experience: float
    recency: float
    location: float


class HybridMatchedJob(BaseModel):
    job_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    hybrid_score: float
    components: ScoreBreakdown
    skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]


class HybridMatchRequest(BaseModel):
    resume_text: str
    preferred_location: Optional[str] = None
    preferred_experience: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=200)
    candidate_count: Optional[int] = Field(default=None, ge=1, le=500)


class HybridMatchResponse(BaseModel):
    results: List[HybridMatchedJob]
    ranking: str = "hybrid"
    embedding_model: str
    retrieval: str
    candidate_count: int
    weights: Dict[str, float]
    embedding_kind: str = "lexical_hashing"
    ranking_label: str = "Lexical vector + structured hybrid"
