from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.embeddings import EmbeddingRepository
from app.db.repositories.jobs import JobRepository
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job
from app.services.embedding_provider import HashingEmbeddingProvider
from app.services.job_embeddings import JobEmbeddingService


def test_stored_embeddings_round_trip_and_retrieve(migrated_db):
    jobs = JobRepository(migrated_db)
    embeddings = EmbeddingRepository(migrated_db)
    provider = HashingEmbeddingProvider(dimension=16)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    jobs.upsert(
        normalize_job(
            RawJob(
                source="adzuna",
                source_job_id="emb-1",
                source_url="https://example.com/jobs/emb-1",
                company="Example",
                title="Data Engineer",
                description="python sql spark",
                location="Bengaluru",
            )
        ),
        now=now,
    )
    stored = jobs.list_jobs()
    assert stored
    service = JobEmbeddingService(embeddings, provider)
    report = service.embed_jobs(stored)
    assert report.jobs_written == 1
    query = provider.embed_query("python sql spark")
    retrieved = embeddings.retrieve_candidates(query, provider.name, limit=5)
    assert retrieved
    assert retrieved[0].job.id == stored[0].id
    assert 0.0 <= retrieved[0].semantic_score <= 1.0
    again = service.embed_jobs(stored)
    assert again.jobs_written == 0
    assert again.jobs_unchanged == 1
