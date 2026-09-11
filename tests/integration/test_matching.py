from __future__ import annotations

from app.core.exceptions import DatabaseUnavailableError
from app.db.repositories.jobs import get_job_repository
from app.schemas.job import Job


class FakeJobRepository:
    def __init__(self, jobs=None):
        self._jobs = jobs or [
            Job(
                id=1,
                title="Python Developer",
                company="Example",
                location="Bengaluru",
                description="python sql fastapi pandas",
            ),
            Job(
                id=2,
                title="People Partner",
                company="Example",
                location="Remote",
                description="collaborative team looking for a motivated person",
            ),
        ]

    def list_jobs(self):
        return self._jobs


def test_upload_resume_ranks_mocked_jobs(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.matching.parse_resume",
        lambda *args, **kwargs: "python sql fastapi pandas",
    )
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    try:
        response = client.post(
            "/upload-resume",
            files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert "jobs" in payload
    jobs = payload["jobs"]
    assert jobs[0]["id"] == 1
    assert jobs[0]["hybrid_score"] >= jobs[1]["hybrid_score"]
    assert "match_score" in jobs[0]
    assert "skill_score" in jobs[0]
    assert "matched_skills" in jobs[0]
    assert "missing_skills" in jobs[0]
    assert "Python" in jobs[0]["matched_skills"]
    assert jobs[1]["skill_score"] == 0
    assert "improved_score" not in jobs[0]
    assert "projected_score" not in jobs[0]
    assert "tfidf_score" not in jobs[0]


def test_upload_resume_rejects_non_pdf(client, app):
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    try:
        response = client.post(
            "/upload-resume",
            files={"file": ("resume.txt", b"just text", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "detail" in response.json()


def test_upload_resume_returns_503_when_database_missing(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.matching.parse_resume",
        lambda *args, **kwargs: "python sql",
    )
    response = client.post(
        "/upload-resume",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake-but-valid-enough", "application/pdf")},
    )
    assert response.status_code == 503
    assert "detail" in response.json()
    assert response.json().get("error") is None


def test_jobs_endpoint_uses_repository(client, app):
    app.dependency_overrides[get_job_repository] = FakeJobRepository
    try:
        response = client.get("/jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["jobs"][0]["title"] == "Python Developer"


def test_jobs_endpoint_unavailable_without_database(client):
    response = client.get("/jobs")
    assert response.status_code == 503
    assert response.json()["detail"]


def test_database_error_does_not_leak_connection_details(client, app):
    class BrokenRepo:
        def list_jobs(self):
            raise DatabaseUnavailableError("Database is unavailable.")

    app.dependency_overrides[get_job_repository] = lambda: BrokenRepo()
    try:
        response = client.get("/jobs")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 503
    assert "password" not in str(body).lower()
    assert "postgresql://" not in str(body).lower()
