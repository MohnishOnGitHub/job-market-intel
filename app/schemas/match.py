from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MatchedJob(BaseModel):
    id: int
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    match_score: float
    skill_score: float
    hybrid_score: float
    skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]


class MatchResponse(BaseModel):
    jobs: List[MatchedJob]
