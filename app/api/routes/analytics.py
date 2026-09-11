from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db.repositories.analytics import AnalyticsRepository, get_analytics_repository
from app.schemas.analytics import (
    CategoryAnalyticsResponse,
    CompanyAnalyticsResponse,
    ExperienceAnalyticsResponse,
    FreshnessAnalyticsResponse,
    LocationAnalyticsResponse,
    OverviewResponse,
    SkillAnalyticsResponse,
)

router = APIRouter(tags=["analytics"])


@router.get(
    "/analytics/overview",
    response_model=OverviewResponse,
    summary="Market overview counts",
)
def analytics_overview(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> OverviewResponse:
    return OverviewResponse(
        **repo.overview(title=title, location=location, experience=experience)
    )


@router.get(
    "/analytics/skills",
    response_model=SkillAnalyticsResponse,
    summary="Skill demand among active jobs",
)
def skill_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> SkillAnalyticsResponse:
    payload = repo.skill_demand(
        title=title, location=location, experience=experience, limit=limit
    )
    return SkillAnalyticsResponse(**payload)


@router.get(
    "/analytics/categories",
    response_model=CategoryAnalyticsResponse,
    summary="Jobs containing at least one skill in each category",
)
def category_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> CategoryAnalyticsResponse:
    return CategoryAnalyticsResponse(
        **repo.skill_categories(title=title, location=location, experience=experience)
    )


@router.get(
    "/analytics/experience",
    response_model=ExperienceAnalyticsResponse,
    summary="Active jobs by stored experience_level",
)
def experience_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> ExperienceAnalyticsResponse:
    return ExperienceAnalyticsResponse(**repo.experience_counts(title=title, location=location))


@router.get(
    "/analytics/locations",
    response_model=LocationAnalyticsResponse,
    summary="Top posting locations (normalized string, not geocoded)",
)
def location_analytics(
    title: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> LocationAnalyticsResponse:
    return LocationAnalyticsResponse(
        **repo.locations(title=title, experience=experience, limit=limit)
    )


@router.get(
    "/analytics/companies",
    response_model=CompanyAnalyticsResponse,
    summary="Top companies by active job count",
)
def company_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> CompanyAnalyticsResponse:
    return CompanyAnalyticsResponse(
        **repo.companies(
            title=title, location=location, experience=experience, limit=limit
        )
    )


@router.get(
    "/analytics/freshness",
    response_model=FreshnessAnalyticsResponse,
    summary="Active jobs by posted_at age buckets",
)
def freshness_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> FreshnessAnalyticsResponse:
    return FreshnessAnalyticsResponse(
        **repo.freshness(title=title, location=location, experience=experience)
    )
