from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db.repositories.jobs import JobRepository, get_job_repository
from app.schemas.job import JobListItem, JobListResponse

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(repo: JobRepository = Depends(get_job_repository)) -> JobListResponse:
    jobs = repo.list_jobs()
    return JobListResponse(
        jobs=[
            JobListItem(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
            )
            for job in jobs
        ]
    )
