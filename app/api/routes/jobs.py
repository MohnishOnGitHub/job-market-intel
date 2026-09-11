from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.db.repositories.jobs import JobRepository, get_job_repository
from app.schemas.job import JobDetail, JobListItem, JobListResponse, JobSkill
from app.services.skill_extractor import extract_skill_records
from app.services.taxonomy import load_skill_taxonomy

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobListResponse, summary="List active jobs")
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


@router.get("/jobs/{job_id}", response_model=JobDetail, summary="Job detail")
def get_job(job_id: int, repo: JobRepository = Depends(get_job_repository)) -> JobDetail:
    detail = repo.get_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail(
        id=detail["id"],
        title=detail["title"],
        company=detail["company"],
        location=detail["location"],
        description=detail["description"],
        source=detail["source"],
        source_url=detail["source_url"],
        employment_type=detail["employment_type"],
        experience_level=detail["experience_level"],
        salary_min=detail["salary_min"],
        salary_max=detail["salary_max"],
        salary_currency=detail["salary_currency"],
        posted_at=detail["posted_at"],
        skills=_job_skills(detail["skill_names"] or None, detail["description"]),
    )


def _job_skills(persisted: Optional[List[str]], description: str) -> List[JobSkill]:
    taxonomy = load_skill_taxonomy()
    names = persisted if persisted is not None else [
        item.canonical_name for item in extract_skill_records(description)
    ]
    result = []
    for name in names:
        skill = taxonomy.by_canonical.get(name)
        result.append(JobSkill(name=name, category=skill.category if skill else None))
    return result
