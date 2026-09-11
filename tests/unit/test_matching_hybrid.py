from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.job import Job
from app.services.embedding_provider import HashingEmbeddingProvider
from app.services.matching import RETRIEVAL_IN_MEMORY, RETRIEVAL_PGVECTOR, match_resume_hybrid
from tests.unit.test_job_embeddings import FakeEmbeddingRepository


class FakeJobRepository:
    def __init__(self, jobs):
        self._jobs = jobs

    def list_jobs(self):
        return self._jobs


class StoredEmbeddingRepository(FakeEmbeddingRepository):
    def __init__(self, candidates):
        super().__init__()
        self._candidates = candidates

    def retrieve_candidates(self, query_embedding, embedding_model, limit):
        return self._candidates[:limit]


def test_hybrid_match_falls_back_to_in_memory_when_no_vectors():
    jobs = [
        Job(id=1, title="Python Developer", description="python sql fastapi pandas"),
        Job(id=2, title="People Partner", description="collaborative team looking for a motivated person"),
    ]
    response = match_resume_hybrid(
        "python sql fastapi pandas",
        job_repository=FakeJobRepository(jobs),
        embedding_repository=FakeEmbeddingRepository(),
        provider=HashingEmbeddingProvider(dimension=32),
        limit=10,
    )
    assert response.retrieval == RETRIEVAL_IN_MEMORY
    assert response.ranking == "hybrid"
    assert response.results[0].job_id == 1
    assert response.results[0].components.semantic >= 0
    assert response.results[0].components.skills > 0
    assert "hiring" not in response.ranking


def test_hybrid_match_uses_retrieved_candidates_without_rescoring_all_jobs():
    kept = Job(
        id=9,
        title="Data Engineer",
        description="python spark sql",
        persisted_skills=["Python", "SQL", "Apache Spark"],
    )
    ignored = Job(
        id=10,
        title="Should not appear unless retrieved",
        description="python spark sql pandas airflow aws",
        persisted_skills=["Python", "SQL", "Apache Spark", "Airflow", "AWS"],
    )

    class Candidate:
        def __init__(self, job, semantic_score):
            self.job = job
            self.semantic_score = semantic_score

    listed = FakeJobRepository([kept, ignored])

    def fail_if_listed(*_args, **_kwargs):
        raise AssertionError("pgvector hits must not score the full job list")

    listed.list_jobs = fail_if_listed
    response = match_resume_hybrid(
        "python spark",
        job_repository=listed,
        embedding_repository=StoredEmbeddingRepository(
            [Candidate(kept, 0.88)]
        ),
        provider=HashingEmbeddingProvider(dimension=16),
        limit=5,
        now=datetime(2026, 9, 11, tzinfo=timezone.utc),
    )
    assert response.retrieval == RETRIEVAL_PGVECTOR
    assert [item.job_id for item in response.results] == [9]
    assert response.results[0].components.semantic == 0.88
    assert response.candidate_count == 1
