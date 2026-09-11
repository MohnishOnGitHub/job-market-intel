from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.embeddings import EmbeddingRepository
from app.db.repositories.jobs import JobRepository
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job
from app.services.embedding_provider import HashingEmbeddingProvider
from app.services.job_embeddings import JobEmbeddingService
from app.services.matching import RETRIEVAL_IN_MEMORY, RETRIEVAL_PGVECTOR, match_resume_hybrid


def _upsert(repo: JobRepository, **kwargs) -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    repo.upsert(normalize_job(RawJob(source="adzuna", **kwargs)), now=now)


def test_hybrid_match_uses_pgvector_when_vectors_exist(migrated_db):
    jobs = JobRepository(migrated_db)
    embeddings = EmbeddingRepository(migrated_db)
    provider = HashingEmbeddingProvider(dimension=32)
    _upsert(
        jobs,
        source_job_id="pgv-1",
        source_url="https://example.com/jobs/pgv-1",
        company="Example",
        title="Data Engineer",
        description="python spark airflow warehouse sql",
        location="Bengaluru",
        experience_level="mid",
    )
    _upsert(
        jobs,
        source_job_id="pgv-2",
        source_url="https://example.com/jobs/pgv-2",
        company="Other",
        title="Registered Nurse",
        description="patient care bedside nursing hospital ward",
        location="Pune",
    )
    stored = jobs.list_jobs()
    JobEmbeddingService(embeddings, provider).embed_jobs(stored)

    response = match_resume_hybrid(
        "python spark airflow data warehouse",
        job_repository=jobs,
        embedding_repository=embeddings,
        provider=provider,
        preferred_location="Bengaluru",
        preferred_experience="mid",
        limit=1,
        candidate_count=1,
    )
    assert response.retrieval == RETRIEVAL_PGVECTOR
    assert response.ranking == "hybrid"
    assert response.embedding_model == provider.name
    assert response.candidate_count == 1
    assert len(response.results) == 1
    assert response.results[0].title == "Data Engineer"
    assert "Python" in response.results[0].matched_skills
    assert response.results[0].components.semantic >= 0


def test_pgvector_skips_inactive_jobs_and_falls_back_without_vectors(migrated_db):
    jobs = JobRepository(migrated_db)
    embeddings = EmbeddingRepository(migrated_db)
    provider = HashingEmbeddingProvider(dimension=16)
    _upsert(
        jobs,
        source_job_id="pgv-3",
        source_url="https://example.com/jobs/pgv-3",
        title="Inactive Engineer",
        description="python sql spark",
    )
    listed = jobs.list_jobs()
    JobEmbeddingService(embeddings, provider).embed_jobs(listed)
    jobs.set_active(listed[0].id, False)

    empty = match_resume_hybrid(
        "python sql spark",
        job_repository=jobs,
        embedding_repository=embeddings,
        provider=provider,
        jobs=[],
        limit=5,
        candidate_count=5,
    )
    assert empty.results == [] or empty.retrieval == RETRIEVAL_IN_MEMORY

    _upsert(
        jobs,
        source_job_id="pgv-4",
        source_url="https://example.com/jobs/pgv-4",
        title="Active Engineer",
        description="python sql spark",
    )
    active = [job for job in jobs.list_jobs() if job.title == "Active Engineer"]
    JobEmbeddingService(embeddings, provider).embed_jobs(active)
    response = match_resume_hybrid(
        "python sql spark",
        job_repository=jobs,
        embedding_repository=embeddings,
        provider=provider,
        limit=5,
        candidate_count=5,
    )
    assert response.retrieval == RETRIEVAL_PGVECTOR
    assert all(item.title != "Inactive Engineer" for item in response.results)
    assert any(item.title == "Active Engineer" for item in response.results)
