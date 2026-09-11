#!/usr/bin/env python3
"""Measure pgvector candidate recall on loaded evaluation jobs.

Requires a migrated PostgreSQL database that already contains the v1
evaluation jobs (source='evaluation') and stored embeddings for the
current embedding provider.

This is distinct from in-memory cosine top-N in evaluate_ranking.py.

  python scripts/evaluate_pgvector.py --split test --output artifacts/evaluation/phase7/pgvector
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import clear_settings_cache, get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.db.database import get_connection
from app.db.repositories.embeddings import EmbeddingRepository
from app.db.repositories.jobs import JobRepository
from app.evaluation.dataset import default_dataset_path, load_evaluation_dataset
from app.evaluation.metrics import binary_relevant_ids, recall_at_k
from app.services.embedding_provider import get_embedding_provider
from app.services.matching import RETRIEVAL_PGVECTOR, match_resume_hybrid

CUTOFFS = (20, 50, 100)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate live pgvector recall.")
    parser.add_argument("--dataset", default=str(default_dataset_path()))
    parser.add_argument("--split", default="test", choices=["test", "validation", "all"])
    parser.add_argument("--output", default="artifacts/evaluation/phase7/pgvector")
    return parser


def _fixture_id_map(conn) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, source_job_id
            FROM jobs
            WHERE source = 'evaluation' AND active = TRUE
              AND source_job_id IS NOT NULL
            """
        )
        mapping = {}
        for db_id, source_job_id in cursor.fetchall():
            try:
                mapping[int(db_id)] = int(source_job_id)
            except (TypeError, ValueError):
                continue
        return mapping


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    clear_settings_cache()
    if not get_settings().database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    dataset = load_evaluation_dataset(args.dataset)
    resumes = dataset.resumes_for_split(args.split)
    try:
        provider = get_embedding_provider()
        with get_connection() as conn:
            mapping = _fixture_id_map(conn)
            if len(mapping) < len(dataset.jobs):
                print(
                    "Evaluation jobs are missing. Run scripts/load_evaluation_jobs.py first.",
                    file=sys.stderr,
                )
                return 1
            embeddings = EmbeddingRepository(conn)
            jobs = JobRepository(conn)
            stored = embeddings.get_hashes(provider.name)
            if not stored:
                print(
                    f"No stored embeddings for {provider.name}. "
                    "Run scripts/generate_embeddings.py --only-missing",
                    file=sys.stderr,
                )
                return 1

            per_cutoff = {str(cutoff): [] for cutoff in CUTOFFS}
            sample = None
            for resume in resumes:
                query = provider.embed_query(resume.text)
                retrieved = embeddings.retrieve_candidates(
                    query, provider.name, max(CUTOFFS)
                )
                fixture_ids = [
                    mapping[item.job.id]
                    for item in retrieved
                    if item.job.id in mapping
                ]
                relevant = binary_relevant_ids(
                    dataset.graded_relevance(resume.id), dataset.binary_threshold
                )
                for cutoff in CUTOFFS:
                    per_cutoff[str(cutoff)].append(
                        recall_at_k(fixture_ids, relevant, cutoff)
                    )
                if sample is None:
                    match = match_resume_hybrid(
                        resume.text,
                        job_repository=jobs,
                        embedding_repository=embeddings,
                        provider=provider,
                        preferred_location=resume.preferred_location,
                        preferred_experience=resume.preferred_experience,
                        limit=5,
                        candidate_count=20,
                    )
                    sample = {
                        "resume_id": resume.id,
                        "retrieval": match.retrieval,
                        "embedding_model": match.embedding_model,
                        "ranking": match.ranking,
                        "candidate_count": match.candidate_count,
                        "top_job_id": match.results[0].job_id if match.results else None,
                    }

            payload = {
                "kind": "postgresql_pgvector",
                "split": args.split,
                "provider": provider.name,
                "stored_vectors": len(stored),
                "evaluation_jobs": len(mapping),
                "note": (
                    "Recall is measured with SQL ORDER BY embedding <=> query "
                    "on active evaluation jobs only. This is not the in-memory fixture ranker."
                ),
                "cutoffs": {
                    cutoff: {
                        "mean": (sum(values) / len(values)) if values else 0.0,
                    }
                    for cutoff, values in per_cutoff.items()
                },
                "sample_match": sample,
                "pgvector_used": bool(sample and sample["retrieval"] == RETRIEVAL_PGVECTOR),
            }
    except DatabaseUnavailableError as exc:
        print(exc.message, file=sys.stderr)
        return 1

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))
    if not payload["pgvector_used"]:
        print("WARNING: sample match did not use pgvector retrieval.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
