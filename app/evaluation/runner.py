from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from app.evaluation import BINARY_RELEVANCE_THRESHOLD, DATASET_VERSION, EVALUATION_SEED
from app.evaluation.dataset import EvaluationDataset, EvaluationResume
from app.evaluation.methods import (
    DESIGN_WEIGHTS,
    MethodResult,
    hashing_provider,
    rank_embedding,
    rank_hybrid,
    rank_skills,
    rank_tfidf,
    try_sentence_transformer,
)
from app.evaluation.metrics import binary_relevant_ids, query_metrics, recall_at_k
from app.evaluation.weights import coarse_weight_grid
from app.schemas.job import Job
from app.services.embedding_provider import EmbeddingProvider
from app.services.hybrid_ranking import RankingWeights

FIXED_NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)
CANDIDATE_CUTOFFS = (20, 50, 100)
METRIC_KEYS = (
    "precision_at_5",
    "precision_at_10",
    "recall_at_10",
    "ndcg_at_5",
    "ndcg_at_10",
    "mrr",
)


@dataclass
class QueryEvaluation:
    resume_id: str
    split: str
    metrics: Dict[str, float]
    ranked_ids: List[int]
    relevant_count: int


@dataclass
class MethodEvaluation:
    name: str
    display_name: str
    ran: bool
    skip_reason: Optional[str] = None
    per_query: List[QueryEvaluation] = field(default_factory=list)
    aggregate: Dict[str, Dict[str, float]] = field(default_factory=dict)
    latency_ms_mean: Optional[float] = None
    metadata: Dict[str, object] = field(default_factory=dict)


def evaluate_dataset(
    dataset: EvaluationDataset,
    *,
    methods: Optional[Sequence[str]] = None,
    split: str = "test",
    include_ablations: bool = True,
    tune_weights: bool = False,
    now: datetime = FIXED_NOW,
    sentence_model: str = "all-MiniLM-L6-v2",
) -> dict:
    selected = list(methods or ("skills", "tfidf", "hashing", "semantic", "hybrid"))
    jobs = dataset.to_jobs()
    resumes = dataset.resumes_for_split(split)
    hashing = hashing_provider()
    semantic_provider, semantic_error = (None, None)
    if any(name in selected for name in ("semantic", "hybrid_semantic")) or include_ablations:
        if "semantic" in selected or "hybrid_semantic" in selected:
            semantic_provider, semantic_error = try_sentence_transformer(sentence_model)

    evaluations: Dict[str, MethodEvaluation] = {}
    if "skills" in selected:
        evaluations["skills"] = _evaluate_method(
            "skills",
            "skill overlap",
            resumes,
            dataset,
            jobs,
            lambda resume: rank_skills(resume, jobs),
        )
    if "tfidf" in selected:
        evaluations["tfidf"] = _evaluate_method(
            "tfidf",
            "pairwise TF-IDF",
            resumes,
            dataset,
            jobs,
            lambda resume: rank_tfidf(resume, jobs),
        )
    if "hashing" in selected:
        evaluations["hashing"] = _evaluate_method(
            "hashing",
            "lexical hashing-v1",
            resumes,
            dataset,
            jobs,
            lambda resume: rank_embedding(resume, jobs, hashing),
            metadata={"provider": hashing.name, "kind": "lexical_hashing"},
        )
    if "semantic" in selected:
        if semantic_provider is None:
            evaluations["semantic"] = MethodEvaluation(
                name="semantic",
                display_name="sentence-transformer semantic",
                ran=False,
                skip_reason=semantic_error or "sentence-transformers is not available",
                metadata={"model": sentence_model},
            )
        else:
            evaluations["semantic"] = _evaluate_method(
                "semantic",
                f"sentence-transformer ({sentence_model})",
                resumes,
                dataset,
                jobs,
                lambda resume, provider=semantic_provider: rank_embedding(
                    resume, jobs, provider
                ),
                metadata={
                    "provider": semantic_provider.name,
                    "kind": "semantic",
                    "model": sentence_model,
                    "dimension": semantic_provider.dimension,
                    "normalize_embeddings": True,
                    "similarity": "cosine",
                },
            )
    if "hybrid" in selected:
        evaluations["hybrid"] = _evaluate_method(
            "hybrid",
            "hybrid (DESIGN weights + hashing-v1 embedding)",
            resumes,
            dataset,
            jobs,
            lambda resume: rank_hybrid(
                resume, jobs, hashing, weights=DESIGN_WEIGHTS, now=now
            ),
            metadata={
                "weights": DESIGN_WEIGHTS.as_dict(),
                "embedding": hashing.name,
                "embedding_kind": "lexical_hashing",
            },
        )

    retrieval = _retrieval_recall(dataset, resumes, jobs, hashing, semantic_provider)
    coverage = component_coverage(dataset, resumes, jobs)
    ablations = {}
    if include_ablations:
        ablations = _ablations(
            dataset,
            resumes,
            jobs,
            hashing,
            semantic_provider,
            now,
        )

    weight_search = None
    if tune_weights:
        weight_search = _weight_search(dataset, jobs, hashing, now)

    return {
        "dataset_version": dataset.version or DATASET_VERSION,
        "split": split,
        "split_strategy": dataset.split_strategy,
        "seed": EVALUATION_SEED,
        "binary_threshold": dataset.binary_threshold,
        "queries": [item.id for item in resumes],
        "query_count": len(resumes),
        "job_count": len(jobs),
        "label_count": len(dataset.labels),
        "now": now.isoformat(),
        "methods": {name: _method_to_dict(item) for name, item in evaluations.items()},
        "retrieval": retrieval,
        "ablations": ablations,
        "coverage": coverage,
        "weight_search": weight_search,
        "pgvector_retrieval": {
            "ran": False,
            "reason": "optional Postgres/pgvector evaluation was not run; fixture evaluation is database-independent",
        },
    }


def component_coverage(
    dataset: EvaluationDataset,
    resumes: Sequence[EvaluationResume],
    jobs: Sequence[Job],
) -> dict:
    job_count = len(jobs) or 1
    skills_available = sum(1 for job in jobs if job.persisted_skills)
    posted_available = sum(1 for job in jobs if job.posted_at is not None)
    experience_available = sum(1 for job in jobs if job.experience_level)
    location_pref = sum(1 for resume in resumes if (resume.preferred_location or "").strip())
    experience_pref = sum(
        1 for resume in resumes if (resume.preferred_experience or "").strip()
    )
    resume_count = len(resumes) or 1
    return {
        "skills_available": skills_available / job_count,
        "posted_at_available": posted_available / job_count,
        "experience_level_available": experience_available / job_count,
        "location_preference_applicable": location_pref / resume_count,
        "experience_preference_applicable": experience_pref / resume_count,
        "job_count": len(jobs),
        "resume_count": len(resumes),
    }


def write_results(payload: dict, output_dir: str | Path) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    rows = []
    for method_name, method in payload.get("methods", {}).items():
        if not method.get("ran"):
            continue
        for query in method.get("per_query", []):
            row = {
                "method": method_name,
                "resume_id": query["resume_id"],
                "split": query["split"],
                **query["metrics"],
            }
            rows.append(row)
    csv_path = directory / "per_query.csv"
    headers = [
        "method",
        "resume_id",
        "split",
        *METRIC_KEYS,
    ]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(
            ",".join(str(row.get(header, "")) for header in headers)
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_table(payload: dict) -> str:
    methods = payload.get("methods", {})
    lines = [
        f"Evaluation: {payload.get('split')}",
        f"Queries: {payload.get('query_count')}",
        "",
        f"{'Method':<28} {'P@5':>7} {'R@10':>7} {'NDCG@10':>8} {'MRR':>7}",
        "-" * 60,
    ]
    for name, method in methods.items():
        if not method.get("ran"):
            lines.append(f"{name:<28} {'NOT RUN':>7}")
            continue
        agg = method.get("aggregate", {})
        lines.append(
            f"{name:<28} "
            f"{_fmt(agg.get('precision_at_5', {}).get('mean')):>7} "
            f"{_fmt(agg.get('recall_at_10', {}).get('mean')):>7} "
            f"{_fmt(agg.get('ndcg_at_10', {}).get('mean')):>8} "
            f"{_fmt(agg.get('mrr', {}).get('mean')):>7}"
        )
    return "\n".join(lines)


def _evaluate_method(
    name: str,
    display_name: str,
    resumes: Sequence[EvaluationResume],
    dataset: EvaluationDataset,
    jobs: Sequence[Job],
    rank_fn,
    metadata: Optional[dict] = None,
) -> MethodEvaluation:
    per_query: List[QueryEvaluation] = []
    latencies: List[float] = []
    for resume in resumes:
        started = time.perf_counter()
        ranked = rank_fn(resume)
        latencies.append((time.perf_counter() - started) * 1000.0)
        ranked_ids = [item.job_id for item in ranked]
        graded = dataset.graded_relevance(resume.id)
        relevant = binary_relevant_ids(graded, dataset.binary_threshold)
        per_query.append(
            QueryEvaluation(
                resume_id=resume.id,
                split=resume.split,
                metrics=query_metrics(ranked_ids, graded, threshold=dataset.binary_threshold),
                ranked_ids=ranked_ids,
                relevant_count=len(relevant),
            )
        )
    return MethodEvaluation(
        name=name,
        display_name=display_name,
        ran=True,
        per_query=per_query,
        aggregate=_aggregate([item.metrics for item in per_query]),
        latency_ms_mean=sum(latencies) / len(latencies) if latencies else None,
        metadata=metadata or {},
    )


def _aggregate(rows: Sequence[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    if not rows:
        return summary
    for key in METRIC_KEYS:
        values = [row[key] for row in rows]
        summary[key] = {
            "mean": _mean(values),
            "median": statistics.median(values),
            "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
        }
    return summary


def _retrieval_recall(
    dataset: EvaluationDataset,
    resumes: Sequence[EvaluationResume],
    jobs: Sequence[Job],
    hashing: EmbeddingProvider,
    semantic_provider: Optional[EmbeddingProvider],
) -> dict:
    result = {
        "hashing": _cutoff_recall(dataset, resumes, jobs, hashing, "lexical hashing-v1"),
    }
    if semantic_provider is None:
        result["semantic"] = {
            "ran": False,
            "reason": "sentence-transformers is not available",
        }
    else:
        result["semantic"] = _cutoff_recall(
            dataset, resumes, jobs, semantic_provider, "sentence-transformer"
        )
    return result


def _cutoff_recall(
    dataset: EvaluationDataset,
    resumes: Sequence[EvaluationResume],
    jobs: Sequence[Job],
    provider: EmbeddingProvider,
    label: str,
) -> dict:
    per_cutoff = {str(cutoff): [] for cutoff in CANDIDATE_CUTOFFS}
    for resume in resumes:
        ranked = rank_embedding(resume, jobs, provider)
        ranked_ids = [item.job_id for item in ranked]
        relevant = binary_relevant_ids(
            dataset.graded_relevance(resume.id), dataset.binary_threshold
        )
        for cutoff in CANDIDATE_CUTOFFS:
            per_cutoff[str(cutoff)].append(recall_at_k(ranked_ids, relevant, cutoff))
    return {
        "ran": True,
        "label": label,
        "provider": provider.name,
        "kind": "in_memory_cosine_top_n",
        "note": "Fixture evaluation ranks the full labeled job set in memory. This estimates candidate-pool recall for cosine top-N, not a live pgvector index.",
        "cutoffs": {
            cutoff: {"mean": _mean(values)}
            for cutoff, values in per_cutoff.items()
        },
    }


def _ablations(
    dataset: EvaluationDataset,
    resumes: Sequence[EvaluationResume],
    jobs: Sequence[Job],
    hashing: EmbeddingProvider,
    semantic_provider: Optional[EmbeddingProvider],
    now: datetime,
) -> dict:
    configs = (
        ("hashing_only", False, False, False, False, hashing, "lexical hashing only"),
        ("hashing_skills", True, False, False, False, hashing, "lexical hashing + skills"),
        (
            "hashing_skills_recency",
            True,
            True,
            False,
            False,
            hashing,
            "lexical hashing + skills + recency",
        ),
        ("hybrid_hashing", True, True, True, True, hashing, "full hybrid with hashing-v1"),
    )
    result = {}
    for name, skills, recency, experience, location, provider, label in configs:
        result[name] = _method_to_dict(
            _evaluate_method(
                name,
                label,
                resumes,
                dataset,
                jobs,
                lambda resume, p=provider, s=skills, r=recency, e=experience, loc=location: rank_hybrid(
                    resume,
                    jobs,
                    p,
                    weights=DESIGN_WEIGHTS,
                    now=now,
                    use_skills=s,
                    use_recency=r,
                    use_experience=e,
                    use_location=loc,
                ),
            )
        )
    if semantic_provider is None:
        result["semantic_only"] = {
            "ran": False,
            "skip_reason": "sentence-transformers is not available",
        }
        result["semantic_skills"] = {
            "ran": False,
            "skip_reason": "sentence-transformers is not available",
        }
        result["semantic_skills_recency"] = {
            "ran": False,
            "skip_reason": "sentence-transformers is not available",
        }
        result["hybrid_semantic"] = {
            "ran": False,
            "skip_reason": "sentence-transformers is not available",
        }
    else:
        semantic_configs = (
            ("semantic_only", False, False, False, False, "semantic only"),
            ("semantic_skills", True, False, False, False, "semantic + skills"),
            (
                "semantic_skills_recency",
                True,
                True,
                False,
                False,
                "semantic + skills + recency",
            ),
            ("hybrid_semantic", True, True, True, True, "full hybrid with sentence-transformer"),
        )
        for name, skills, recency, experience, location, label in semantic_configs:
            result[name] = _method_to_dict(
                _evaluate_method(
                    name,
                    label,
                    resumes,
                    dataset,
                    jobs,
                    lambda resume, s=skills, r=recency, e=experience, loc=location: rank_hybrid(
                        resume,
                        jobs,
                        semantic_provider,
                        weights=DESIGN_WEIGHTS,
                        now=now,
                        use_skills=s,
                        use_recency=r,
                        use_experience=e,
                        use_location=loc,
                    ),
                )
            )
    return result


def _weight_search(
    dataset: EvaluationDataset,
    jobs: Sequence[Job],
    provider: EmbeddingProvider,
    now: datetime,
) -> dict:
    validation = dataset.resumes_for_split("validation")
    test = dataset.resumes_for_split("test")
    if len(validation) < 2 or len(test) < 1:
        return {
            "ran": False,
            "reason": "split is too small for a held-out weight search",
        }
    best = None
    best_score = -1.0
    for weights in coarse_weight_grid():
        evaluation = _evaluate_method(
            "grid",
            "grid",
            validation,
            dataset,
            jobs,
            lambda resume, w=weights: rank_hybrid(
                resume, jobs, provider, weights=w, now=now
            ),
        )
        score = evaluation.aggregate.get("ndcg_at_10", {}).get("mean", 0.0)
        if score > best_score:
            best_score = score
            best = (weights, evaluation)
    assert best is not None
    weights, validation_eval = best
    test_eval = _evaluate_method(
        "hybrid_tuned",
        "hybrid tuned on validation",
        test,
        dataset,
        jobs,
        lambda resume: rank_hybrid(resume, jobs, provider, weights=weights, now=now),
    )
    default_test = _evaluate_method(
        "hybrid_default",
        "hybrid DESIGN weights",
        test,
        dataset,
        jobs,
        lambda resume: rank_hybrid(
            resume, jobs, provider, weights=DESIGN_WEIGHTS, now=now
        ),
    )
    return {
        "ran": True,
        "note": "Directional only. Validation has few queries. Production defaults were not changed.",
        "tuned_on": "validation",
        "objective": "mean NDCG@10",
        "best_validation_weights": weights.as_dict(),
        "best_validation_ndcg_at_10": validation_eval.aggregate["ndcg_at_10"]["mean"],
        "test_default": _method_to_dict(default_test),
        "test_tuned": _method_to_dict(test_eval),
        "embedding_kind": "lexical_hashing",
    }


def _method_to_dict(evaluation: MethodEvaluation) -> dict:
    return {
        "name": evaluation.name,
        "display_name": evaluation.display_name,
        "ran": evaluation.ran,
        "skip_reason": evaluation.skip_reason,
        "per_query": [
            {
                "resume_id": item.resume_id,
                "split": item.split,
                "metrics": item.metrics,
                "ranked_ids": item.ranked_ids,
                "relevant_count": item.relevant_count,
            }
            for item in evaluation.per_query
        ],
        "aggregate": evaluation.aggregate,
        "latency_ms_mean": evaluation.latency_ms_mean,
        "metadata": evaluation.metadata,
    }


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"
