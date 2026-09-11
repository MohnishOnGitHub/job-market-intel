from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.analytics import AnalyticsRepository
from app.db.repositories.jobs import JobRepository
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job


def test_analytics_counts_unknowns_and_freshness(migrated_db):
    jobs = JobRepository(migrated_db)
    now = datetime(2026, 9, 11, tzinfo=timezone.utc)
    jobs.upsert(
        normalize_job(
            RawJob(
                source="adzuna",
                source_job_id="a1",
                source_url="https://example.com/a1",
                company="Example",
                title="Data Engineer",
                description="python spark",
                location="Bengaluru",
                experience_level="mid",
                posted_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
            )
        ),
        now=now,
    )
    jobs.upsert(
        normalize_job(
            RawJob(
                source="adzuna",
                source_job_id="a2",
                source_url="https://example.com/a2",
                company=None,
                title="Analyst",
                description="sql tableau",
                location="Pune",
                posted_at=None,
            )
        ),
        now=now,
    )
    repo = AnalyticsRepository(migrated_db)
    overview = repo.overview()
    assert overview["active_jobs"] == 2
    experience = repo.experience_counts()
    levels = {item["experience_level"]: item["job_count"] for item in experience["items"]}
    assert levels.get("mid") == 1
    assert levels.get("unknown") == 1
    locations = repo.locations()
    names = {item["location"] for item in locations["items"]}
    assert "Bengaluru" in names
    companies = repo.companies()
    assert companies["jobs_without_company"] == 1
    assert companies["items"][0]["company"] == "Example"
    freshness = repo.freshness(now=now)
    buckets = {item["bucket"]: item["job_count"] for item in freshness["items"]}
    assert buckets["0-7 days"] == 1
    assert buckets["unknown"] == 1
    assert buckets["8-30 days"] == 0
