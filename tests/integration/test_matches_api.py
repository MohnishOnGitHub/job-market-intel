from __future__ import annotations

from app.db.repositories.embeddings import get_embedding_repository
from app.db.repositories.jobs import get_job_repository
from app.schemas.job import Job
from tests.integration.test_matching import FakeJobRepository
from tests.unit.test_job_embeddings import FakeEmbeddingRepository


def test_hybrid_matches_json_returns_score_breakdown(client, app):
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    app.dependency_overrides[get_embedding_repository] = FakeEmbeddingRepository
    try:
        response = client.post(
            "/api/v1/matches",
            json={
                "resume_text": "python sql fastapi pandas",
                "preferred_location": "Bengaluru",
                "limit": 10,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ranking"] == "hybrid"
    assert "results" in payload
    assert payload["weights"]["semantic"] > 0
    top = payload["results"][0]
    assert top["job_id"] == 1
    assert set(top["components"]) == {
        "semantic",
        "skills",
        "experience",
        "recency",
        "location",
    }
    assert "probability" not in payload
    assert top["hybrid_score"] >= payload["results"][1]["hybrid_score"]
    assert "Python" in top["matched_skills"]


def test_hybrid_matches_rejects_empty_resume_text(client, app):
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    app.dependency_overrides[get_embedding_repository] = FakeEmbeddingRepository
    try:
        response = client.post("/api/v1/matches", json={"resume_text": "   "})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400


def test_hybrid_matches_upload_uses_parser(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.matches.parse_resume",
        lambda *args, **kwargs: "python sql fastapi pandas",
    )
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    app.dependency_overrides[get_embedding_repository] = FakeEmbeddingRepository
    try:
        response = client.post(
            "/api/v1/matches/upload",
            files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"preferred_location": "Bengaluru"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["results"][0]["job_id"] == 1


def test_hybrid_matches_returns_503_without_database(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.matches.parse_resume",
        lambda *args, **kwargs: "python sql",
    )
    response = client.post(
        "/api/v1/matches",
        json={"resume_text": "python sql"},
    )
    assert response.status_code == 503
    assert "detail" in response.json()
