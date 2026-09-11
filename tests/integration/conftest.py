from __future__ import annotations

import os
import subprocess
import time

import pytest

from app.core.config import clear_settings_cache

CONTAINER_NAME = "jmi-phase4-pg"
IMAGE = "pgvector/pgvector:pg16"
TEST_PORT = "55432"
TEST_URL = f"postgresql://test:test@127.0.0.1:{TEST_PORT}/job_market_test"


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _wait_for_postgres(url: str) -> bool:
    import psycopg2

    for _ in range(40):
        try:
            conn = psycopg2.connect(url)
            conn.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def postgres_url():
    env_url = os.getenv("TEST_DATABASE_URL")
    if env_url:
        if not _wait_for_postgres(env_url):
            pytest.skip("TEST_DATABASE_URL is set but PostgreSQL is not reachable")
        yield env_url
        return

    if not _docker_available():
        pytest.skip("PostgreSQL is unavailable (no TEST_DATABASE_URL and Docker is not ready)")

    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True, check=False)
    started = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-e",
            "POSTGRES_USER=test",
            "-e",
            "POSTGRES_PASSWORD=test",
            "-e",
            "POSTGRES_DB=job_market_test",
            "-p",
            f"{TEST_PORT}:5432",
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if started.returncode != 0:
        pytest.skip(f"Could not start test PostgreSQL: {started.stderr.strip()}")

    try:
        if not _wait_for_postgres(TEST_URL):
            pytest.skip("Test PostgreSQL container did not become ready")
        yield TEST_URL
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True, check=False)


@pytest.fixture
def migrated_db(postgres_url, monkeypatch):
    import psycopg2

    from app.db.migrate import apply_migrations

    monkeypatch.setenv("DATABASE_URL", postgres_url)
    clear_settings_cache()
    conn = psycopg2.connect(postgres_url)
    apply_migrations(conn)
    conn.autocommit = True
    with conn.cursor() as cursor:
        cursor.execute("TRUNCATE ingestion_runs RESTART IDENTITY CASCADE")
        cursor.execute("TRUNCATE jobs RESTART IDENTITY CASCADE")
    yield conn
    conn.close()
    clear_settings_cache()
