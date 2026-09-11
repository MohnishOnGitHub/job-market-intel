from __future__ import annotations

from app.db.repositories.analytics import AnalyticsRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.skills import SkillRepository
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job
from app.services.skill_enrichment import SkillEnrichmentService
from app.services.taxonomy import load_skill_taxonomy


def test_taxonomy_sync_is_idempotent(migrated_db):
    taxonomy = load_skill_taxonomy(force_reload=True)
    repo = SkillRepository(migrated_db)
    first = repo.sync_taxonomy(taxonomy)
    second = repo.sync_taxonomy(taxonomy)
    assert first["skills_inserted"] == len(taxonomy)
    assert second["skills_inserted"] == 0
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM skills")
        assert cursor.fetchone()[0] == len(taxonomy)
        cursor.execute("SELECT COUNT(*) FROM skill_aliases")
        alias_count = cursor.fetchone()[0]
        assert alias_count >= len(taxonomy)


def test_job_skill_enrichment_and_analytics(migrated_db):
    taxonomy = load_skill_taxonomy(force_reload=True)
    skills = SkillRepository(migrated_db)
    skills.sync_taxonomy(taxonomy)
    jobs = JobRepository(migrated_db)
    jobs.upsert(
        normalize_job(
            RawJob(
                source="adzuna",
                source_job_id="1",
                title="Data Engineer",
                description="Python SQL Spark AWS",
                location="Bengaluru",
                company="Example",
            )
        )
    )
    existing = jobs.find_existing(
        normalize_job(
            RawJob(
                source="adzuna",
                source_job_id="1",
                title="Data Engineer",
                description="Python SQL Spark AWS",
                company="Example",
            )
        )
    )
    assert existing is not None
    enricher = SkillEnrichmentService(jobs, skills)
    first = enricher.enrich_job(existing["id"], "Python SQL Spark AWS")
    second = enricher.enrich_job(existing["id"], "Python SQL Spark AWS")
    assert first == second
    with migrated_db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM job_skills WHERE job_id = %s", (existing["id"],))
        assert cursor.fetchone()[0] == first

    enricher.enrich_job(existing["id"], "Python and Spark")
    with migrated_db.cursor() as cursor:
        cursor.execute(
            """
            SELECT s.canonical_name
            FROM job_skills js
            JOIN skills s ON s.id = js.skill_id
            WHERE js.job_id = %s
            ORDER BY s.canonical_name
            """,
            (existing["id"],),
        )
        names = [row[0] for row in cursor.fetchall()]
    assert names == ["Apache Spark", "Python"]

    analytics = AnalyticsRepository(migrated_db).skill_demand(title="Data Engineer")
    assert analytics["total_jobs"] == 1
    assert analytics["jobs_with_skills"] == 1
    skill_names = {item["skill"] for item in analytics["skills"]}
    assert "Python" in skill_names
    assert analytics["skills"][0]["job_share"] == 1.0
