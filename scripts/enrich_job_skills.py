#!/usr/bin/env python3
"""Extract canonical skills from job descriptions into job_skills.

  python scripts/enrich_job_skills.py --all
  python scripts/enrich_job_skills.py --only-missing --limit 100
  python scripts/enrich_job_skills.py --job-id 12
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.db.migrate import apply_migrations
from app.db.repositories.jobs import JobRepository
from app.db.repositories.skills import SkillRepository
from app.services.skill_enrichment import SkillEnrichmentService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enrich jobs with canonical skills.")
    parser.add_argument("--all", action="store_true", help="Re-enrich every active job.")
    parser.add_argument("--only-missing", action="store_true")
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
        with get_connection() as conn:
            service = SkillEnrichmentService(
                job_repository=JobRepository(conn),
                skill_repository=SkillRepository(conn),
            )
            report = service.enrich_jobs(
                job_id=args.job_id,
                only_missing=args.only_missing and args.job_id is None,
                limit=args.limit,
            )
            conn.commit()
    except DatabaseUnavailableError as exc:
        print(exc.message, file=sys.stderr)
        return 1

    print(
        "Enrichment report: jobs={total} with_skills={with_skills} "
        "zero_skills={zero} relationships={rels} avg={avg}".format(
            total=report.total_jobs,
            with_skills=report.jobs_with_skills,
            zero=report.jobs_with_zero_skills,
            rels=report.total_job_skill_relationships,
            avg=report.average_skills_per_enriched_job,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
