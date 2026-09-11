#!/usr/bin/env python3
"""Load the committed v1 evaluation jobs into PostgreSQL for local demos.

These 32 rows are synthetic fixtures, not Adzuna postings.

  python scripts/load_evaluation_jobs.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.db.migrate import apply_migrations
from app.db.repositories.jobs import JobRepository
from app.evaluation.dataset import default_dataset_path, load_evaluation_dataset
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    clear_settings_cache()
    if not get_settings().database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    dataset = load_evaluation_dataset(default_dataset_path())
    try:
        apply_migrations()
        counts = {"inserted": 0, "updated": 0, "unchanged": 0}
        with get_connection() as conn:
            repo = JobRepository(conn)
            for job in dataset.jobs:
                result = repo.upsert(
                    normalize_job(
                        RawJob(
                            source="evaluation",
                            source_job_id=str(job.id),
                            source_url=f"https://evaluation.local/v1/jobs/{job.id}",
                            company=job.company,
                            title=job.title,
                            description=job.description,
                            location=job.location,
                            experience_level=job.experience_level,
                            posted_at=job.posted_at,
                        )
                    )
                )
                counts[result] = counts.get(result, 0) + 1
            conn.commit()
    except DatabaseUnavailableError as exc:
        print(exc.message, file=sys.stderr)
        return 1

    print(
        "Loaded evaluation fixtures: inserted={inserted} updated={updated} "
        "unchanged={unchanged} total={total}".format(
            inserted=counts.get("inserted", 0),
            updated=counts.get("updated", 0),
            unchanged=counts.get("unchanged", 0),
            total=len(dataset.jobs),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
