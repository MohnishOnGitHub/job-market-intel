from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import ResumeParseError
from app.db.repositories.embeddings import (
    EmbeddingRepository,
    get_embedding_repository,
)
from app.db.repositories.jobs import JobRepository, get_job_repository
from app.schemas.hybrid_match import HybridMatchRequest, HybridMatchResponse
from app.services.matching import match_resume_hybrid
from app.services.resume_parser import parse_resume

router = APIRouter()


@router.post("/matches", response_model=HybridMatchResponse)
def create_matches(
    payload: HybridMatchRequest,
    job_repo: JobRepository = Depends(get_job_repository),
    embedding_repo: EmbeddingRepository = Depends(get_embedding_repository),
) -> HybridMatchResponse:
    resume_text = (payload.resume_text or "").strip()
    if not resume_text:
        raise ResumeParseError("resume_text is required.")
    return match_resume_hybrid(
        resume_text,
        job_repository=job_repo,
        embedding_repository=embedding_repo,
        preferred_location=payload.preferred_location,
        preferred_experience=payload.preferred_experience,
        limit=payload.limit,
        candidate_count=payload.candidate_count,
    )


@router.post("/matches/upload", response_model=HybridMatchResponse)
async def upload_matches(
    file: UploadFile = File(...),
    preferred_location: Optional[str] = Form(default=None),
    preferred_experience: Optional[str] = Form(default=None),
    limit: int = Form(default=20),
    job_repo: JobRepository = Depends(get_job_repository),
    embedding_repo: EmbeddingRepository = Depends(get_embedding_repository),
) -> HybridMatchResponse:
    contents = await file.read()
    resume_text = parse_resume(
        contents,
        filename=file.filename,
        content_type=file.content_type,
    )
    return match_resume_hybrid(
        resume_text,
        job_repository=job_repo,
        embedding_repository=embedding_repo,
        preferred_location=preferred_location,
        preferred_experience=preferred_experience,
        limit=limit,
    )
