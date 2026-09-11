from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.db.repositories.jobs import JobRepository
from app.db.repositories.skills import SkillRepository
from app.services.skill_extractor import extract_skill_records


@dataclass
class EnrichmentReport:
    total_jobs: int
    jobs_enriched: int
    jobs_with_skills: int
    jobs_with_zero_skills: int
    total_job_skill_relationships: int
    average_skills_per_enriched_job: float


class SkillEnrichmentService:
    def __init__(
        self,
        job_repository: Optional[JobRepository] = None,
        skill_repository: Optional[SkillRepository] = None,
    ) -> None:
        self.job_repository = job_repository or JobRepository()
        self.skill_repository = skill_repository or SkillRepository()

    def enrich_job(self, job_id: int, description: str) -> int:
        names = [skill.canonical_name for skill in extract_skill_records(description)]
        return self.skill_repository.replace_job_skills(job_id, names)

    def enrich_jobs(
        self,
        job_id: Optional[int] = None,
        only_missing: bool = False,
        limit: Optional[int] = None,
    ) -> EnrichmentReport:
        jobs = self.job_repository.list_jobs_for_enrichment(
            job_id=job_id,
            only_missing=only_missing,
            limit=limit,
        )
        jobs_with_skills = 0
        jobs_with_zero = 0
        relationships = 0
        for job in jobs:
            count = self.enrich_job(job.id, job.description)
            relationships += count
            if count:
                jobs_with_skills += 1
            else:
                jobs_with_zero += 1

        enriched = len(jobs)
        average = (relationships / enriched) if enriched else 0.0
        return EnrichmentReport(
            total_jobs=enriched,
            jobs_enriched=enriched,
            jobs_with_skills=jobs_with_skills,
            jobs_with_zero_skills=jobs_with_zero,
            total_job_skill_relationships=relationships,
            average_skills_per_enriched_job=round(average, 2),
        )
