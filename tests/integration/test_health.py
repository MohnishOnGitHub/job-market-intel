from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_starts_without_database_url(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "DATABASE_URL" not in response.text
