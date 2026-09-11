from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok"}
