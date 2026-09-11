from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import clear_settings_cache
from app.main import create_app


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("MAX_UPLOAD_MB", "5")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)
