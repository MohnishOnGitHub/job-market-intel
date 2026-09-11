from __future__ import annotations

from pathlib import Path

import scripts.generate_embeddings as generate_embeddings

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_embeddings.py"


def test_generate_embeddings_script_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("missing configuration must not open a database connection")

    monkeypatch.setattr("app.db.database.psycopg2.connect", fail_connect)
    monkeypatch.setattr("app.db.migrate.psycopg2.connect", fail_connect)
    assert generate_embeddings.main(["--all"]) == 1


def test_generate_embeddings_help_lists_options():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "DATABASE_URL" in source
    help_text = generate_embeddings.build_parser().format_help()
    assert "--all" in help_text
    assert "--only-missing" in help_text
    assert "--job-id" in help_text
