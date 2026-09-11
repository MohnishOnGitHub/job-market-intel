from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SkillDemandItem(BaseModel):
    skill: str
    category: str
    job_count: int
    job_share: float = Field(
        description="active jobs containing the skill / filtered active jobs"
    )


class SkillAnalyticsResponse(BaseModel):
    total_jobs: int
    jobs_with_skills: int
    skills: List[SkillDemandItem]


class CategoryDemandItem(BaseModel):
    category: str
    job_count: int
    job_share: float = Field(
        description="active jobs with at least one skill in this category / filtered active jobs"
    )


class CategoryAnalyticsResponse(BaseModel):
    total_jobs: int
    metric: str = "jobs_with_at_least_one_skill_in_category"
    categories: List[CategoryDemandItem]


class CountItem(BaseModel):
    key: str
    job_count: int


class ExperienceItem(BaseModel):
    experience_level: str
    job_count: int


class ExperienceAnalyticsResponse(BaseModel):
    total_jobs: int
    items: List[ExperienceItem]


class LocationItem(BaseModel):
    location: str
    job_count: int


class LocationAnalyticsResponse(BaseModel):
    total_jobs: int
    note: str = (
        "Locations are COALESCE(location_normalized, location_raw) strings, "
        "not geocoded regions."
    )
    items: List[LocationItem]


class CompanyItem(BaseModel):
    company: str
    job_count: int


class CompanyAnalyticsResponse(BaseModel):
    total_jobs: int
    jobs_without_company: int
    items: List[CompanyItem]


class FreshnessItem(BaseModel):
    bucket: str
    job_count: int


class FreshnessAnalyticsResponse(BaseModel):
    total_jobs: int
    as_of: datetime
    basis: str = "posted_at"
    items: List[FreshnessItem]


class TopSkillSummary(BaseModel):
    skill: str
    category: Optional[str] = None
    job_count: int
    job_share: float


class OverviewResponse(BaseModel):
    active_jobs: int
    jobs_with_skills: int
    canonical_skills: int
    latest_ingestion_at: Optional[datetime] = None
    latest_job_seen_at: Optional[datetime] = None
    top_skill: Optional[TopSkillSummary] = None
