from __future__ import annotations

from fastapi import APIRouter

from app.schemas.status import RankingStatusResponse
from app.services.ranking_labels import ranking_status_payload

router = APIRouter(tags=["ranking"])


@router.get(
    "/ranking/status",
    response_model=RankingStatusResponse,
    summary="Active embedding provider and hybrid label (no scoring change)",
)
def ranking_status() -> RankingStatusResponse:
    return RankingStatusResponse(**ranking_status_payload())
