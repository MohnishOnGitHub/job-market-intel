from __future__ import annotations

from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Sequence

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.services.taxonomy import SkillTaxonomy, slugify


class SkillRepository:
    def __init__(self, connection=None) -> None:
        self._connection = connection

    @contextmanager
    def _conn(self) -> Iterator:
        if self._connection is not None:
            yield self._connection
            return
        with get_connection() as conn:
            yield conn

    def sync_taxonomy(self, taxonomy: SkillTaxonomy) -> Dict[str, int]:
        """Upsert skills and aliases from the file. Does not delete extras."""
        inserted = 0
        updated = 0
        aliases_upserted = 0
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    for skill in taxonomy.skills:
                        slug = slugify(skill.canonical_name)
                        cursor.execute(
                            "SELECT id, category, slug FROM skills WHERE canonical_name = %s",
                            (skill.canonical_name,),
                        )
                        row = cursor.fetchone()
                        if row is None:
                            cursor.execute(
                                """
                                INSERT INTO skills (canonical_name, slug, category)
                                VALUES (%s, %s, %s)
                                RETURNING id
                                """,
                                (skill.canonical_name, slug, skill.category),
                            )
                            skill_id = cursor.fetchone()[0]
                            inserted += 1
                        else:
                            skill_id = row[0]
                            if row[1] != skill.category or row[2] != slug:
                                cursor.execute(
                                    "UPDATE skills SET category = %s, slug = %s WHERE id = %s",
                                    (skill.category, slug, skill_id),
                                )
                                updated += 1

                        for alias in skill.aliases:
                            normalized = (
                                alias
                                if skill.match_strategy == "isolated_letter"
                                else alias.lower()
                            )
                            cursor.execute(
                                """
                                INSERT INTO skill_aliases (skill_id, alias, normalized_alias)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (normalized_alias) DO UPDATE
                                SET skill_id = EXCLUDED.skill_id,
                                    alias = EXCLUDED.alias
                                """,
                                (skill_id, alias, normalized),
                            )
                            aliases_upserted += 1
                if self._connection is None:
                    conn.commit()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

        return {
            "skills_inserted": inserted,
            "skills_updated": updated,
            "aliases_upserted": aliases_upserted,
            "skills_total": len(taxonomy),
        }

    def id_by_canonical_name(self) -> Dict[str, int]:
        with self._conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, canonical_name FROM skills")
                return {row[1]: row[0] for row in cursor.fetchall()}

    def replace_job_skills(
        self,
        job_id: int,
        canonical_names: Sequence[str],
        extraction_source: str = "taxonomy_v1",
    ) -> int:
        names = list(dict.fromkeys(canonical_names))
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    mapping = {}
                    if names:
                        cursor.execute(
                            "SELECT id, canonical_name FROM skills WHERE canonical_name = ANY(%s)",
                            (names,),
                        )
                        mapping = {row[1]: row[0] for row in cursor.fetchall()}
                    cursor.execute("DELETE FROM job_skills WHERE job_id = %s", (job_id,))
                    inserted = 0
                    for name in names:
                        skill_id = mapping.get(name)
                        if skill_id is None:
                            continue
                        cursor.execute(
                            """
                            INSERT INTO job_skills (job_id, skill_id, extraction_source)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (job_id, skill_id) DO NOTHING
                            """,
                            (job_id, skill_id, extraction_source),
                        )
                        inserted += 1
                    if self._connection is None:
                        conn.commit()
                    return inserted
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

    def list_taxonomy(self) -> List[dict]:
        with self._conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT canonical_name, category, slug
                    FROM skills
                    ORDER BY canonical_name
                    """
                )
                return [
                    {"skill": row[0], "category": row[1], "slug": row[2]}
                    for row in cursor.fetchall()
                ]


def get_skill_repository() -> SkillRepository:
    return SkillRepository()
