#!/usr/bin/env python3
"""Thin CLI for the Adzuna ingestion pipeline.

Business logic lives in app.ingestion. This script only parses arguments
and environment variables.

  python scripts/ingest_adzuna.py --query "python developer" --country in --location bangalore --pages 2

Required environment variables:
  DATABASE_URL
  ADZUNA_APP_ID
  ADZUNA_APP_KEY

Optional:
  ADZUNA_COUNTRY
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError, JobSourceError
from app.db.database import get_connection
from app.db.migrate import apply_migrations
from app.db.repositories.ingestion_runs import IngestionRunRepository
from app.db.repositories.jobs import JobRepository
from app.ingestion.service import IngestionService
from app.ingestion.sources.adzuna import AdzunaSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest jobs from Adzuna into PostgreSQL.")
    parser.add_argument("--query", default="python developer")
    parser.add_argument("--country", default=None, help="Adzuna country code, default ADZUNA_COUNTRY or in")
    parser.add_argument("--location", default=None)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--results-per-page", type=int, default=10)
    parser.add_argument(
        "--skip-migrate",
        action="store_true",
        help="Do not apply pending SQL migrations before ingesting.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    clear_settings_cache()
    settings = get_settings()

    if not settings.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        print("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set.", file=sys.stderr)
        return 1

    country = args.country or settings.adzuna_country

    try:
        if not args.skip_migrate:
            apply_migrations()
        with get_connection() as conn:
            source = AdzunaSource(
                app_id=settings.adzuna_app_id,
                app_key=settings.adzuna_app_key,
                country=country,
                query=args.query,
                location=args.location,
                pages=args.pages,
                results_per_page=args.results_per_page,
            )
            service = IngestionService(
                job_repository=JobRepository(conn),
                run_repository=IngestionRunRepository(conn),
            )
            try:
                counts = service.run(source)
            except (JobSourceError, DatabaseUnavailableError):
                conn.commit()
                raise
            conn.commit()
    except (JobSourceError, DatabaseUnavailableError) as exc:
        print(exc.message, file=sys.stderr)
        return 1

    print(
        "Ingestion {status}: fetched={fetched} inserted={inserted} "
        "updated={updated} unchanged={unchanged} skipped={skipped} failed={failed}".format(
            status=counts.status,
            fetched=counts.records_fetched,
            inserted=counts.records_inserted,
            updated=counts.records_updated,
            unchanged=counts.records_unchanged,
            skipped=counts.records_skipped,
            failed=counts.records_failed,
        )
    )
    return 0 if counts.status in {"completed", "completed_with_errors"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
