from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.job import Job
from app.services.hybrid_ranking import (
    RankingWeights,
    compute_hybrid_rank_score,
    default_ranking_weights,
    experience_score,
    location_score,
    rank_hybrid_jobs,
    recency_score,
)
from app.services.skill_extractor import compute_skill_score


NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


def test_default_weights_sum_to_one():
    weights = default_ranking_weights()
    total = (
        weights.semantic
        + weights.skill
        + weights.experience
        + weights.recency
        + weights.location
    )
    assert abs(total - 1.0) < 1e-9


def test_unused_optional_signals_renormalize_remaining_weights():
    weights = RankingWeights(0.50, 0.25, 0.10, 0.10, 0.05).without_unused(
        use_experience=False,
        use_location=False,
    )
    assert weights.experience == 0.0
    assert weights.location == 0.0
    assert abs(weights.semantic + weights.skill + weights.recency - 1.0) < 1e-9


def test_hybrid_formula_matches_weighted_sum():
    weights = RankingWeights(0.50, 0.25, 0.10, 0.10, 0.05)
    assert compute_hybrid_rank_score(
        semantic_score=0.80,
        skill_score=0.50,
        experience_score_value=1.0,
        recency_score_value=0.90,
        location_score_value=1.0,
        weights=weights,
    ) == round(0.50 * 0.80 + 0.25 * 0.50 + 0.10 * 1.0 + 0.10 * 0.90 + 0.05 * 1.0, 3)


def test_skill_score_is_zero_when_job_has_no_skills():
    assert compute_skill_score([], []) == 0.0


def test_recency_uses_exponential_decay_and_neutral_fallback():
    assert recency_score(None, now=NOW, tau_days=30) == 0.5
    fresh = recency_score(NOW, now=NOW, tau_days=30)
    month_old = recency_score(NOW - timedelta(days=30), now=NOW, tau_days=30)
    assert fresh == 1.0
    assert abs(month_old - 0.367879) < 0.001
    assert fresh > month_old


def test_location_score_only_applies_with_a_preference():
    assert location_score("Bengaluru", None) is None
    assert location_score("Bengaluru", "Bengaluru") == 1.0
    assert location_score("Bengaluru, India", "Bengaluru") == 0.5
    assert location_score("Remote", "remote") == 1.0
    assert location_score("Hybrid - Pune", "Mumbai") == 0.5
    assert location_score("Pune", "Bengaluru") == 0.0
    assert location_score(None, "Bengaluru") == 0.5


def test_experience_score_uses_explicit_levels_only():
    assert experience_score("senior", None) is None
    assert experience_score("senior", "senior") == 1.0
    assert experience_score("mid", "senior") == 0.75
    assert experience_score("junior", "senior") == 0.5
    assert experience_score("internship", "senior") == 0.25
    assert experience_score(None, "mid") == 0.5
    assert experience_score("5 years", "mid") == 0.5


def test_hybrid_ranker_returns_explanations_and_sorts():
    jobs = [
        Job(
            id=1,
            title="Weak",
            description="kubernetes only role",
            persisted_skills=["Kubernetes"],
            posted_at=NOW - timedelta(days=90),
        ),
        Job(
            id=2,
            title="Strong",
            description="python sql spark",
            persisted_skills=["Python", "SQL", "Apache Spark"],
            posted_at=NOW,
            location="Bengaluru",
            experience_level="mid",
        ),
    ]
    ranked = rank_hybrid_jobs(
        "python sql spark",
        jobs,
        {1: 0.20, 2: 0.90},
        preferred_location="Bengaluru",
        preferred_experience="mid",
        now=NOW,
        tau_days=30,
    )
    assert [item.job_id for item in ranked] == [2, 1]
    top = ranked[0]
    assert top.components.semantic == 0.9
    assert top.components.skills == 1.0
    assert top.components.location == 1.0
    assert top.components.experience == 1.0
    assert top.components.recency == 1.0
    assert "Python" in top.matched_skills
    assert top.hybrid_score >= ranked[1].hybrid_score
    assert ranked[1].components.skills == 0.0


def test_missing_posted_at_is_neutral_not_invented():
    jobs = [
        Job(id=1, title="A", description="python", persisted_skills=["Python"]),
    ]
    ranked = rank_hybrid_jobs("python", jobs, {1: 1.0}, now=NOW, tau_days=30)
    assert ranked[0].components.recency == 0.5
