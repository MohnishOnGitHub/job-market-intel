from __future__ import annotations

from pathlib import Path

import scripts.ingest_adzuna as ingest_adzuna

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ingest_adzuna.py"


def test_ingest_script_is_environment_driven():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "DATABASE_URL" in source
    assert "ADZUNA_APP_ID" in source
    assert "ADZUNA_APP_KEY" in source
    assert "password=" not in source
    assert "host=" not in source
    assert "user=" not in source


def test_main_exits_without_connecting_when_env_is_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
    monkeypatch.delenv("APP_ID", raising=False)
    monkeypatch.delenv("APP_KEY", raising=False)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("missing configuration must not open a database connection")

    monkeypatch.setattr(ingest_adzuna.psycopg2, "connect", fail_connect)
    assert ingest_adzuna.main() == 1
