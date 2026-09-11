from __future__ import annotations

from app.schemas.job import Job
from app.services.skill_enrichment import SkillEnrichmentService


class FakeSkillRepository:
    def __init__(self) -> None:
        self.links = {}

    def replace_job_skills(self, job_id, canonical_names, extraction_source="taxonomy_v1"):
        self.links[job_id] = list(canonical_names)
        return len(self.links[job_id])


class FakeJobRepository:
    def __init__(self, jobs):
        self.jobs = jobs

    def list_jobs_for_enrichment(self, job_id=None, only_missing=False, limit=None, active_only=True):
        rows = self.jobs
        if job_id is not None:
            rows = [job for job in rows if job.id == job_id]
        if limit:
            rows = rows[:limit]
        return rows


def test_enrichment_is_idempotent_and_replaces_stale_skills():
    jobs = [
        Job(id=1, title="DE", description="Python and SQL"),
    ]
    skills = FakeSkillRepository()
    service = SkillEnrichmentService(FakeJobRepository(jobs), skills)
    first = service.enrich_jobs()
    second = service.enrich_jobs()
    assert first.jobs_enriched == 1
    assert first.jobs_with_skills == 1
    assert second.total_job_skill_relationships == first.total_job_skill_relationships
    assert skills.links[1] == ["Python", "SQL"]

    jobs[0].description = "Python and Spark"
    service.enrich_jobs()
    assert skills.links[1] == ["Python", "Apache Spark"]
    assert "SQL" not in skills.links[1]


def test_zero_skill_jobs_are_counted():
    jobs = [Job(id=2, title="HR", description="team player needed")]
    service = SkillEnrichmentService(FakeJobRepository(jobs), FakeSkillRepository())
    report = service.enrich_jobs()
    assert report.jobs_with_zero_skills == 1
    assert report.jobs_with_skills == 0
    assert report.average_skills_per_enriched_job == 0
