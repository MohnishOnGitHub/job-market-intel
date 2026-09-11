from __future__ import annotations


def test_skills_endpoint_uses_taxonomy_file_without_database(client):
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    payload = response.json()
    names = {item["skill"] for item in payload["skills"]}
    assert "Python" in names
    assert "PostgreSQL" in names
    assert "AWS" in names


def test_analytics_requires_database(client):
    response = client.get("/api/v1/analytics/skills")
    assert response.status_code == 503
    assert "detail" in response.json()
