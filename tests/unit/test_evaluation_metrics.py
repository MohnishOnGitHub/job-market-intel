from __future__ import annotations

from app.evaluation.metrics import (
    ndcg_at_k,
    precision_at_k,
    query_metrics,
    recall_at_k,
    reciprocal_rank,
)


def test_ideal_ranking_is_perfect():
    ranked = [1, 2, 3, 4, 5]
    relevant = {1, 2, 3}
    graded = {1: 3, 2: 2, 3: 1, 4: 0, 5: 0}
    assert precision_at_k(ranked, relevant, 3) == 1.0
    assert recall_at_k(ranked, relevant, 3) == 1.0
    assert ndcg_at_k(ranked, graded, 5) == 1.0
    assert reciprocal_rank(ranked, relevant) == 1.0


def test_reversed_ranking_is_worse_than_ideal():
    ideal = [1, 2, 3, 4]
    reversed_ids = [4, 3, 2, 1]
    graded = {1: 3, 2: 2, 3: 1, 4: 0}
    relevant = {1, 2, 3}
    assert precision_at_k(reversed_ids, relevant, 3) < precision_at_k(ideal, relevant, 3)
    assert ndcg_at_k(reversed_ids, graded, 4) < ndcg_at_k(ideal, graded, 4)
    assert reciprocal_rank(reversed_ids, relevant) < reciprocal_rank(ideal, relevant)


def test_no_relevant_results_are_zero():
    ranked = [4, 5, 6]
    assert precision_at_k(ranked, set(), 5) == 0.0
    assert recall_at_k(ranked, set(), 10) == 0.0
    assert ndcg_at_k(ranked, {4: 0, 5: 0}, 5) == 0.0
    assert reciprocal_rank(ranked, set()) == 0.0


def test_single_relevant_result_sets_mrr():
    ranked = [10, 20, 30]
    assert reciprocal_rank(ranked, {20}) == 0.5
    assert precision_at_k(ranked, {20}, 2) == 0.5
    assert recall_at_k(ranked, {20}, 2) == 1.0


def test_graded_ndcg_prefers_higher_labels_first():
    graded = {1: 3, 2: 1}
    better = ndcg_at_k([1, 2], graded, 2)
    worse = ndcg_at_k([2, 1], graded, 2)
    assert better > worse


def test_query_metrics_use_threshold_two():
    ranked = [1, 2, 3, 4, 5]
    graded = {1: 3, 2: 1, 3: 0, 4: 2, 5: 0}
    metrics = query_metrics(ranked, graded)
    assert metrics["precision_at_5"] == 0.4
    assert metrics["recall_at_10"] == 1.0
    assert metrics["mrr"] == 1.0
