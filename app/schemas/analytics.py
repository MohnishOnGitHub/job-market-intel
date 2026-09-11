from __future__ import annotations

from typing import List

from pydantic import BaseModel


class SkillDemandItem(BaseModel):
    skill: str
    category: str
    job_count: int
    job_share: float


class SkillAnalyticsResponse(BaseModel):
    total_jobs: int
    jobs_with_skills: int
    skills: List[SkillDemandItem]
