from __future__ import annotations

from app.evaluation.methods import hashing_provider, rank_embedding
from app.evaluation.runner import component_coverage, evaluate_dataset
from app.evaluation.v1_authoring import build_v1_dataset


def test_evaluation_runs_lightweight_methods_on_fixture():
    dataset = build_v1_dataset()
    payload = evaluate_dataset(
        dataset,
        methods=("skills", "tfidf", "hashing", "semantic", "hybrid"),
        split="test",
        include_ablations=False,
        tune_weights=False,
    )
    assert payload["query_count"] == 3
    assert payload["job_count"] == 32
    assert payload["methods"]["skills"]["ran"] is True
    assert payload["methods"]["tfidf"]["ran"] is True
    assert payload["methods"]["hashing"]["ran"] is True
    assert payload["methods"]["hashing"]["metadata"]["kind"] == "lexical_hashing"
    assert payload["methods"]["semantic"]["ran"] is False
    assert payload["methods"]["hybrid"]["metadata"]["embedding_kind"] == "lexical_hashing"
    assert payload["pgvector_retrieval"]["ran"] is False
    skills = payload["methods"]["skills"]["aggregate"]["ndcg_at_10"]["mean"]
    assert 0.0 <= skills <= 1.0
    for query in payload["methods"]["tfidf"]["per_query"]:
        assert query["ranked_ids"]
        assert "precision_at_5" in query["metrics"]


def test_profile_split_does_not_leak_test_resumes_into_validation():
    dataset = build_v1_dataset()
    validation = evaluate_dataset(
        dataset,
        methods=("skills",),
        split="validation",
        include_ablations=False,
    )
    test = evaluate_dataset(
        dataset,
        methods=("skills",),
        split="test",
        include_ablations=False,
    )
    validation_ids = {item["resume_id"] for item in validation["methods"]["skills"]["per_query"]}
    test_ids = {item["resume_id"] for item in test["methods"]["skills"]["per_query"]}
    assert validation_ids.isdisjoint(test_ids)
    assert "r_de_mid" in test_ids


def test_hashing_ranking_is_deterministic():
    dataset = build_v1_dataset()
    jobs = dataset.to_jobs()
    resume = dataset.resumes[0]
    provider = hashing_provider()
    first = [item.job_id for item in rank_embedding(resume, jobs, provider)]
    second = [item.job_id for item in rank_embedding(resume, jobs, provider)]
    assert first == second


def test_component_coverage_reports_availability():
    dataset = build_v1_dataset()
    coverage = component_coverage(dataset, dataset.resumes, dataset.to_jobs())
    assert coverage["skills_available"] > 0
    assert 0 <= coverage["posted_at_available"] <= 1
    assert 0 <= coverage["experience_level_available"] <= 1
    assert coverage["location_preference_applicable"] == 1.0
