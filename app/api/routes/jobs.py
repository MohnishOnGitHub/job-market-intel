from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.db.repositories.jobs import JobRepository, get_job_repository
from app.schemas.job import JobListItem, JobListResponse
from app.services.skill_extractor import extract_skill_records
from app.services.taxonomy import load_skill_taxonomy

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


@router.get("/jobs/{job_id}")
def get_job(job_id: int, repo: JobRepository = Depends(get_job_repository)) -> dict:
    job = repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "skills": _job_skills(job.persisted_skills, job.description),
    }


def _job_skills(persisted: Optional[List[str]], description: str) -> List[dict]:
    taxonomy = load_skill_taxonomy()
    names = persisted if persisted is not None else [
        item.canonical_name for item in extract_skill_records(description)
    ]
    result = []
    for name in names:
        skill = taxonomy.by_canonical.get(name)
        result.append({"name": name, "category": skill.category if skill else None})
    return result
