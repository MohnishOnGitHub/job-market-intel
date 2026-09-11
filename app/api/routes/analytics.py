from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.db.repositories.analytics import AnalyticsRepository, get_analytics_repository
from app.schemas.analytics import SkillAnalyticsResponse

router = APIRouter()


@router.get("/analytics/skills", response_model=SkillAnalyticsResponse)
def skill_analytics(
    title: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> SkillAnalyticsResponse:
    payload = repo.skill_demand(title=title, location=location, limit=limit)
    return SkillAnalyticsResponse(**payload)
