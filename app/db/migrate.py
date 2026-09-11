from __future__ import annotations

import logging
from pathlib import Path

import psycopg2

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError

logger = logging.getLogger("app.db.migrate")
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _connect():
    settings = get_settings()
    if not settings.database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not set.")
    try:
        return psycopg2.connect(settings.database_url)
    except psycopg2.Error as exc:
        raise DatabaseUnavailableError("Database is unavailable.") from exc


def _legacy_jobs_columns(cursor) -> set[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs'
        """
    )
    return {row[0] for row in cursor.fetchall()}


def _archive_legacy_jobs(cursor) -> None:
    cols = _legacy_jobs_columns(cursor)
    if not cols:
        return
    if "source" in cols and "location_raw" in cols:
        return
    if "title" not in cols:
        return

    logger.info("event=legacy_jobs_archive")
    cursor.execute("ALTER TABLE jobs RENAME TO jobs_legacy")
    cursor.execute(
        """
        INSERT INTO schema_migrations (version)
        VALUES ('legacy_jobs_archived')
        ON CONFLICT (version) DO NOTHING
        """
    )


def _copy_legacy_jobs(cursor) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'jobs_legacy'
        """
    )
    if cursor.fetchone() is None:
        return

    cursor.execute(
        "SELECT 1 FROM schema_migrations WHERE version = %s",
        ("legacy_jobs_copied",),
    )
    if cursor.fetchone() is not None:
        return

    legacy_cols = set()
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'jobs_legacy'
        """
    )
    legacy_cols = {row[0] for row in cursor.fetchall()}
    seen_expr = "NOW()"
    if "created_at" in legacy_cols:
        seen_expr = "COALESCE(created_at, NOW())"

    cursor.execute(
        f"""
        INSERT INTO jobs (
            source, source_job_id, company, title, description,
            location_raw, location_normalized,
            first_seen_at, last_seen_at, active
        )
        SELECT
            'legacy',
            id::text,
            NULLIF(BTRIM(company), ''),
            BTRIM(title),
            BTRIM(description),
            NULLIF(BTRIM(location), ''),
            NULLIF(BTRIM(location), ''),
            {seen_expr},
            {seen_expr},
            TRUE
        FROM jobs_legacy
        WHERE title IS NOT NULL AND BTRIM(title) <> ''
          AND description IS NOT NULL AND BTRIM(description) <> ''
        """
    )
    cursor.execute(
        "INSERT INTO schema_migrations (version) VALUES (%s)",
        ("legacy_jobs_copied",),
    )
    logger.info("event=legacy_jobs_copied")


def apply_migrations(conn=None) -> list[str]:
    own_connection = conn is None
    if own_connection:
        conn = _connect()

    applied: list[str] = []
    try:
        conn.autocommit = False
        with conn.cursor() as cursor:
            bootstrap = (MIGRATIONS_DIR / "001_schema_migrations.sql").read_text(
                encoding="utf-8"
            )
            cursor.execute(bootstrap)
            conn.commit()

            _archive_legacy_jobs(cursor)
            conn.commit()

            cursor.execute("SELECT version FROM schema_migrations")
            done = {row[0] for row in cursor.fetchall()}

            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                version = path.name
                if version in done:
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                conn.commit()
                applied.append(version)
                logger.info("event=migration_applied version=%s", version)

            _copy_legacy_jobs(cursor)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if own_connection:
            conn.close()
    return applied


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        applied = apply_migrations()
    except DatabaseUnavailableError as exc:
        print(exc.message)
        return 1
    if applied:
        print("Applied migrations: " + ", ".join(applied))
    else:
        print("No pending migrations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
