from __future__ import annotations

from app.schemas.job import Job
from app.services.embedding_provider import HashingEmbeddingProvider
from app.services.embedding_text import build_embedding_text, embedding_content_hash
from app.services.job_embeddings import JobEmbeddingService


class FakeEmbeddingRepository:
    def __init__(self) -> None:
        self.rows = {}

    def get_hashes(self, embedding_model: str):
        return {
            job_id: row["content_hash"]
            for (job_id, model), row in self.rows.items()
            if model == embedding_model
        }

    def upsert(self, job_id, embedding_model, embedding, content_hash):
        self.rows[(job_id, embedding_model)] = {
            "embedding": list(embedding),
            "content_hash": content_hash,
        }

    def retrieve_candidates(self, query_embedding, embedding_model, limit):
        return []


def test_embedding_generation_is_idempotent_until_content_changes():
    repo = FakeEmbeddingRepository()
    provider = HashingEmbeddingProvider(dimension=16)
    service = JobEmbeddingService(repo, provider)
    job = Job(
        id=7,
        title="Data Engineer",
        company="Example",
        location="Bengaluru",
        description="python sql spark",
        persisted_skills=["Python", "SQL"],
    )
    first = service.embed_jobs([job])
    second = service.embed_jobs([job])
    assert first.jobs_written == 1
    assert second.jobs_written == 0
    assert second.jobs_unchanged == 1

    changed = Job(
        id=7,
        title="Data Engineer",
        company="Example",
        location="Bengaluru",
        description="python sql airflow",
        persisted_skills=["Python", "SQL"],
    )
    third = service.embed_jobs([changed])
    assert third.jobs_written == 1
    text = build_embedding_text(
        title=changed.title,
        company=changed.company,
        location=changed.location,
        description=changed.description,
        skills=changed.persisted_skills,
    )
    assert repo.rows[(7, provider.name)]["content_hash"] == embedding_content_hash(
        text, provider.name
    )
