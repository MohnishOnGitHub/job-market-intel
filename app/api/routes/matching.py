from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.db.repositories.jobs import JobRepository, get_job_repository
from app.schemas.match import MatchResponse
from app.services.ranking import rank_jobs
from app.services.resume_parser import parse_resume

router = APIRouter()


@router.post("/upload-resume", response_model=MatchResponse)
async def upload_resume(
    file: UploadFile = File(...),
    repo: JobRepository = Depends(get_job_repository),
) -> MatchResponse:
    contents = await file.read()
    resume_text = parse_resume(
        contents,
        filename=file.filename,
        content_type=file.content_type,
    )
    jobs = repo.list_jobs()
    return MatchResponse(jobs=rank_jobs(resume_text, jobs))
