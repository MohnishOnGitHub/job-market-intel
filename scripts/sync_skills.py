#!/usr/bin/env python3
"""Sync data/taxonomy/skills.yml into PostgreSQL skills and skill_aliases.

The YAML file is the source of truth. Sync is idempotent and does not
delete database skills that are absent from the file.

  python scripts/sync_skills.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError, TaxonomyError
from app.db.database import get_connection
from app.db.migrate import apply_migrations
from app.db.repositories.skills import SkillRepository
from app.services.taxonomy import load_skill_taxonomy


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    clear_settings_cache()
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    try:
        taxonomy = load_skill_taxonomy(force_reload=True)
        apply_migrations()
        with get_connection() as conn:
            repo = SkillRepository(conn)
            first = repo.sync_taxonomy(taxonomy)
            second = repo.sync_taxonomy(taxonomy)
            conn.commit()
    except (DatabaseUnavailableError, TaxonomyError) as exc:
        print(getattr(exc, "message", str(exc)), file=sys.stderr)
        return 1

    print(
        "Taxonomy sync: skills={total} inserted={inserted} updated={updated} aliases={aliases}".format(
            total=first["skills_total"],
            inserted=first["skills_inserted"],
            updated=first["skills_updated"],
            aliases=first["aliases_upserted"],
        )
    )
    print(
        "Idempotent re-sync: inserted={inserted} updated={updated}".format(
            inserted=second["skills_inserted"],
            updated=second["skills_updated"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
