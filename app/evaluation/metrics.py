from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

from app.evaluation import BINARY_RELEVANCE_THRESHOLD


def precision_at_k(
    ranked_ids: Sequence[int],
    relevant_ids: Iterable[int],
    k: int,
) -> float:
    """Fraction of the top-k results that are binary-relevant. Divides by k."""
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(relevant_ids)
    top = list(ranked_ids)[:k]
    hits = sum(1 for job_id in top if job_id in relevant)
    return hits / k


def recall_at_k(
    ranked_ids: Sequence[int],
    relevant_ids: Iterable[int],
    k: int,
) -> float:
    """Fraction of labeled relevant items recovered in the top k."""
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    top = set(list(ranked_ids)[:k])
    return len(top & relevant) / len(relevant)


def average_precision_at_k(
    ranked_ids: Sequence[int],
    relevant_ids: Iterable[int],
    k: int,
) -> float:
    relevant = set(relevant_ids)
    if not relevant or k <= 0:
        return 0.0
    hits = 0
    total = 0.0
    for index, job_id in enumerate(list(ranked_ids)[:k], start=1):
        if job_id in relevant:
            hits += 1
            total += hits / index
    return total / min(len(relevant), k)


def dcg_at_k(gains: Sequence[float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    score = 0.0
    for index, gain in enumerate(list(gains)[:k], start=1):
        score += (math.pow(2.0, float(gain)) - 1.0) / math.log2(index + 1.0)
    return score


def ndcg_at_k(
    ranked_ids: Sequence[int],
    graded_relevance: Mapping[int, float],
    k: int,
) -> float:
    """NDCG with graded gains. Unlisted ids contribute 0."""
    if k <= 0:
        raise ValueError("k must be positive")
    gains = [float(graded_relevance.get(job_id, 0.0)) for job_id in list(ranked_ids)[:k]]
    ideal = sorted((float(value) for value in graded_relevance.values()), reverse=True)
    ideal_dcg = dcg_at_k(ideal, k)
    if ideal_dcg == 0.0:
        return 0.0
    return dcg_at_k(gains, k) / ideal_dcg


def reciprocal_rank(
    ranked_ids: Sequence[int],
    relevant_ids: Iterable[int],
) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    for index, job_id in enumerate(ranked_ids, start=1):
        if job_id in relevant:
            return 1.0 / index
    return 0.0


def binary_relevant_ids(
    graded_relevance: Mapping[int, float],
    threshold: int = BINARY_RELEVANCE_THRESHOLD,
) -> set[int]:
    return {
        job_id
        for job_id, grade in graded_relevance.items()
        if grade >= threshold
    }


def query_metrics(
    ranked_ids: Sequence[int],
    graded_relevance: Mapping[int, float],
    *,
    threshold: int = BINARY_RELEVANCE_THRESHOLD,
) -> dict[str, float]:
    relevant = binary_relevant_ids(graded_relevance, threshold)
    return {
        "precision_at_5": precision_at_k(ranked_ids, relevant, 5),
        "precision_at_10": precision_at_k(ranked_ids, relevant, 10),
        "recall_at_10": recall_at_k(ranked_ids, relevant, 10),
        "ndcg_at_5": ndcg_at_k(ranked_ids, graded_relevance, 5),
        "ndcg_at_10": ndcg_at_k(ranked_ids, graded_relevance, 10),
        "mrr": reciprocal_rank(ranked_ids, relevant),
    }
