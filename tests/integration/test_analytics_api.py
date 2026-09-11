from __future__ import annotations

from datetime import datetime, timezone

from app.db.repositories.analytics import get_analytics_repository
from app.db.repositories.jobs import get_job_repository


class FakeAnalyticsRepository:
    def overview(self, **_kwargs):
        return {
            "active_jobs": 10,
            "jobs_with_skills": 8,
            "canonical_skills": 160,
            "latest_ingestion_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
            "latest_job_seen_at": datetime(2026, 9, 2, tzinfo=timezone.utc),
            "top_skill": {
                "skill": "Python",
                "category": "Programming",
                "job_count": 6,
                "job_share": 0.6,
            },
        }

    def skill_demand(self, **_kwargs):
        return {
            "total_jobs": 10,
            "jobs_with_skills": 8,
            "skills": [
                {
                    "skill": "Python",
                    "category": "Programming",
                    "job_count": 6,
                    "job_share": 0.6,
                }
            ],
        }

    def skill_categories(self, **_kwargs):
        return {
            "total_jobs": 10,
            "metric": "jobs_with_at_least_one_skill_in_category",
            "categories": [{"category": "Programming", "job_count": 7, "job_share": 0.7}],
        }

    def experience_counts(self, **_kwargs):
        return {
            "total_jobs": 10,
            "items": [
                {"experience_level": "mid", "job_count": 6},
                {"experience_level": "unknown", "job_count": 4},
            ],
        }

    def locations(self, **_kwargs):
        return {
            "total_jobs": 10,
            "note": "Locations are COALESCE(location_normalized, location_raw) strings, not geocoded regions.",
            "items": [{"location": "Bengaluru", "job_count": 5}],
        }

    def companies(self, **_kwargs):
        return {
            "total_jobs": 10,
            "jobs_without_company": 1,
            "items": [{"company": "Example", "job_count": 9}],
        }

    def freshness(self, **_kwargs):
        return {
            "total_jobs": 10,
            "as_of": datetime(2026, 9, 11, tzinfo=timezone.utc),
            "basis": "posted_at",
            "items": [
                {"bucket": "0-7 days", "job_count": 3},
                {"bucket": "8-30 days", "job_count": 2},
                {"bucket": "31-60 days", "job_count": 1},
                {"bucket": "61+ days", "job_count": 1},
                {"bucket": "unknown", "job_count": 3},
            ],
        }


class DetailRepo:
    def get_job_detail(self, job_id):
        if job_id != 7:
            return None
        return {
            "id": 7,
            "title": "Data Engineer",
            "company": "Example",
            "location": "Bengaluru",
            "description": "python sql",
            "source": "adzuna",
            "source_url": "https://example.com/jobs/7",
            "employment_type": "full_time",
            "experience_level": "mid",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": None,
            "posted_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
            "skill_names": ["Python", "SQL"],
        }


def test_overview_schema(client, app):
    app.dependency_overrides[get_analytics_repository] = FakeAnalyticsRepository
    try:
        response = client.get("/api/v1/analytics/overview")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["active_jobs"] == 10
    assert body["jobs_with_skills"] == 8
    assert body["top_skill"]["skill"] == "Python"
    assert "latest_ingestion_at" in body


def test_analytics_collection_schemas(client, app):
    app.dependency_overrides[get_analytics_repository] = FakeAnalyticsRepository
    try:
        skills = client.get("/api/v1/analytics/skills").json()
        experience = client.get("/api/v1/analytics/experience").json()
        locations = client.get("/api/v1/analytics/locations").json()
        companies = client.get("/api/v1/analytics/companies").json()
        freshness = client.get("/api/v1/analytics/freshness").json()
        categories = client.get("/api/v1/analytics/categories").json()
    finally:
        app.dependency_overrides.clear()
    assert skills["skills"][0]["job_share"] == 0.6
    assert experience["items"][1]["experience_level"] == "unknown"
    assert "not geocoded" in locations["note"]
    assert companies["jobs_without_company"] == 1
    assert {item["bucket"] for item in freshness["items"]} >= {
        "0-7 days",
        "unknown",
    }
    assert categories["metric"] == "jobs_with_at_least_one_skill_in_category"


def test_new_analytics_require_database(client):
    for path in (
        "/api/v1/analytics/overview",
        "/api/v1/analytics/experience",
        "/api/v1/analytics/locations",
        "/api/v1/analytics/companies",
        "/api/v1/analytics/freshness",
        "/api/v1/analytics/categories",
    ):
        response = client.get(path)
        assert response.status_code == 503
        assert "detail" in response.json()


def test_job_detail_schema(client, app):
    app.dependency_overrides[get_job_repository] = DetailRepo
    try:
        response = client.get("/jobs/7")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "adzuna"
    assert body["experience_level"] == "mid"
    assert body["salary_min"] is None
    assert body["skills"][0]["name"] == "Python"


def test_ranking_status_works_without_database(client):
    response = client.get("/api/v1/ranking/status")
    assert response.status_code == 200
    body = response.json()
    assert body["tfidf_label"] == "Pairwise TF-IDF baseline"
    assert body["embedding_kind"] in {"lexical_hashing", "semantic"}
