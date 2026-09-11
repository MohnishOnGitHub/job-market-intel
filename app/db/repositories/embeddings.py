from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence

import psycopg2

from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.schemas.job import Job

logger = logging.getLogger("app.db.embeddings")


@dataclass
class RetrievedCandidate:
    job: Job
    semantic_score: float


class EmbeddingRepository:
    def __init__(self, connection=None) -> None:
        self._connection = connection

    @contextmanager
    def _conn(self) -> Iterator:
        if self._connection is not None:
            yield self._connection
            return
        with get_connection() as conn:
            yield conn

    def upsert(
        self,
        job_id: int,
        embedding_model: str,
        embedding: Sequence[float],
        content_hash: str,
    ) -> None:
        literal = _vector_literal(embedding)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO job_embeddings (
                            job_id, embedding_model, embedding, content_hash
                        )
                        VALUES (%s, %s, %s::vector, %s)
                        ON CONFLICT (job_id, embedding_model)
                        DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            content_hash = EXCLUDED.content_hash,
                            updated_at = NOW()
                        """,
                        (job_id, embedding_model, literal, content_hash),
                    )
                if self._connection is None:
                    conn.commit()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

    def get_hashes(self, embedding_model: str) -> Dict[int, str]:
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT job_id, content_hash
                        FROM job_embeddings
                        WHERE embedding_model = %s
                        """,
                        (embedding_model,),
                    )
                    return {row[0]: row[1] for row in cursor.fetchall()}
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error as exc:
            raise DatabaseUnavailableError("Database is unavailable.") from exc

    def retrieve_candidates(
        self,
        query_embedding: Sequence[float],
        embedding_model: str,
        limit: int,
    ) -> List[RetrievedCandidate]:
        if limit <= 0:
            return []
        literal = _vector_literal(query_embedding)
        try:
            with self._conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            j.id,
                            j.title,
                            j.company,
                            COALESCE(j.location_normalized, j.location_raw) AS location,
                            j.description,
                            j.experience_level,
                            j.posted_at,
                            COALESCE(
                                ARRAY_AGG(s.canonical_name ORDER BY s.id)
                                FILTER (WHERE s.canonical_name IS NOT NULL),
                                ARRAY[]::text[]
                            ) AS skill_names,
                            GREATEST(
                                0.0,
                                LEAST(1.0, 1 - (e.embedding <=> %s::vector))
                            ) AS semantic_score
                        FROM job_embeddings e
                        JOIN jobs j ON j.id = e.job_id
                        LEFT JOIN job_skills js ON js.job_id = j.id
                        LEFT JOIN skills s ON s.id = js.skill_id
                        WHERE j.active = TRUE
                          AND e.embedding_model = %s
                        GROUP BY
                            j.id, e.embedding
                        ORDER BY e.embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (literal, embedding_model, literal, limit),
                    )
                    rows = cursor.fetchall()
        except DatabaseUnavailableError:
            raise
        except psycopg2.Error:
            logger.warning("event=vector_retrieval_failed", exc_info=True)
            return []

        candidates: List[RetrievedCandidate] = []
        for row in rows:
            skill_names = list(row[7] or [])
            candidates.append(
                RetrievedCandidate(
                    job=Job(
                        id=row[0],
                        title=row[1],
                        company=row[2],
                        location=row[3],
                        description=row[4] or "",
                        persisted_skills=skill_names or None,
                        experience_level=row[5],
                        posted_at=row[6],
                    ),
                    semantic_score=float(row[8] or 0.0),
                )
            )
        return candidates


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def get_embedding_repository() -> EmbeddingRepository:
    return EmbeddingRepository()
