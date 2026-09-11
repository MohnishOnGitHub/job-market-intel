#!/usr/bin/env python3
"""Generate job embeddings for vector candidate retrieval.

  python scripts/generate_embeddings.py --all
  python scripts/generate_embeddings.py --only-missing
  python scripts/generate_embeddings.py --job-id 12
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError, EmbeddingProviderError
from app.db.database import get_connection
from app.db.migrate import apply_migrations
from app.db.repositories.embeddings import EmbeddingRepository
from app.db.repositories.jobs import JobRepository
from app.services.embedding_provider import get_embedding_provider
from app.services.job_embeddings import JobEmbeddingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate stored job embeddings.")
    parser.add_argument("--all", action="store_true", help="Embed every active job.")
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Skip jobs that already have a vector for the current model.",
    )
    parser.add_argument("--job-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    clear_settings_cache()
    if not get_settings().database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not args.all and not args.only_missing and args.job_id is None:
        print("Choose --all, --only-missing, or --job-id.", file=sys.stderr)
        return 1

    try:
        apply_migrations()
        provider = get_embedding_provider()
        with get_connection() as conn:
            jobs = JobRepository(conn).list_jobs()
            if args.job_id is not None:
                jobs = [job for job in jobs if job.id == args.job_id]
            if args.limit:
                jobs = jobs[: args.limit]
            service = JobEmbeddingService(
                embedding_repository=EmbeddingRepository(conn),
                provider=provider,
            )
            report = service.embed_jobs(
                jobs,
                only_missing=args.only_missing and args.job_id is None,
            )
            conn.commit()
    except EmbeddingProviderError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    except DatabaseUnavailableError as exc:
        print(exc.message, file=sys.stderr)
        return 1

    print(
        "Embedding report: model={model} seen={seen} written={written} unchanged={unchanged}".format(
            model=report.embedding_model,
            seen=report.jobs_seen,
            written=report.jobs_written,
            unchanged=report.jobs_unchanged,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
