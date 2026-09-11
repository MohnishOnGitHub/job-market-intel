from __future__ import annotations

from app.schemas.job import Job
from app.services.ranking import (
    SKILL_WEIGHT,
    TFIDF_WEIGHT,
    compute_hybrid_score,
    pairwise_tfidf_score,
    rank_jobs,
    rank_tfidf,
)
from app.services.skill_extractor import compute_skill_score


def test_rank_tfidf_is_an_independent_lexical_baseline():
    jobs = [
        Job(
            id=1,
            title="Role",
            company="Co",
            location="X",
            description="python sql pandas",
        )
    ]
    assert rank_tfidf("python sql", jobs) == rank_jobs("python sql", jobs)


def test_hybrid_formula_is_preserved():
    assert TFIDF_WEIGHT == 0.7
    assert SKILL_WEIGHT == 0.3
    assert compute_hybrid_score(0.80, 0.50) == round(0.7 * 0.80 + 0.3 * 0.50, 3)


def test_hybrid_uses_rounded_match_score_like_the_mvp():
    match_score = pairwise_tfidf_score(
        "python sql pandas fastapi",
        "python sql pandas fastapi backend role",
    )
    skill_score = compute_skill_score(
        ["python", "sql", "pandas", "fastapi"],
        ["python", "sql", "pandas", "fastapi"],
    )
    assert compute_hybrid_score(match_score, skill_score) == round(
        0.7 * match_score + 0.3 * skill_score, 3
    )


def test_pairwise_tfidf_identical_text_is_high():
    score = pairwise_tfidf_score("python developer fastapi sql", "python developer fastapi sql")
    assert score == 1.0


def test_pairwise_tfidf_unrelated_text_is_low():
    score = pairwise_tfidf_score("python pandas sql", "registered nurse night shift")
    assert score == 0.0


def test_pairwise_tfidf_empty_text_is_zero():
    assert pairwise_tfidf_score("", "python developer") == 0.0
    assert pairwise_tfidf_score("python developer", "") == 0.0


def test_no_job_skills_keeps_skill_score_zero():
    jobs = [
        Job(
            id=1,
            title="Culture fit",
            company="Example",
            location="Remote",
            description="team player needed for a growing group",
        )
    ]
    ranked = rank_jobs("python sql pandas", jobs)
    assert ranked[0].skills == []
    assert ranked[0].skill_score == 0
    assert ranked[0].hybrid_score == round(0.7 * ranked[0].match_score + 0.3 * 0, 3)


def test_ranking_order_follows_hybrid_score():
    jobs = [
        Job(
            id=1,
            title="Weak overlap",
            company="A",
            location="X",
            description="kubernetes only role for cluster operations",
        ),
        Job(
            id=2,
            title="Strong overlap",
            company="B",
            location="Y",
            description="python sql pandas fastapi backend engineer",
        ),
        Job(
            id=3,
            title="No skills",
            company="C",
            location="Z",
            description="collaborative team looking for a motivated person",
        ),
    ]
    ranked = rank_jobs("python sql pandas fastapi experience", jobs)
    assert [job.id for job in ranked] == [2, 1, 3]
    assert ranked[0].hybrid_score >= ranked[1].hybrid_score >= ranked[2].hybrid_score
    assert "Python" in ranked[0].matched_skills
    assert "Kubernetes" in ranked[1].missing_skills


def test_rank_jobs_includes_score_components():
    jobs = [
        Job(
            id=10,
            title="Data role",
            company="Co",
            location="Bengaluru",
            description="python sql spark aws",
        )
    ]
    result = rank_jobs("python sql pandas", jobs)[0]
    assert result.match_score == pairwise_tfidf_score(
        "python sql pandas", "python sql spark aws"
    )
    assert result.matched_skills == ["Python", "SQL"]
    assert result.missing_skills == ["Apache Spark", "AWS"]
    assert result.skills == ["Python", "SQL", "Apache Spark", "AWS"]
    assert result.skill_score == 0.5
    assert result.hybrid_score == compute_hybrid_score(result.match_score, 0.5)


def test_persisted_skills_are_preferred_over_description_extraction():
    jobs = [
        Job(
            id=1,
            title="Data role",
            company="Co",
            location="Bengaluru",
            description="python sql spark aws",
            persisted_skills=["Python", "Apache Spark"],
        )
    ]
    result = rank_jobs("python sql pandas", jobs)[0]
    assert result.skills == ["Python", "Apache Spark"]
    assert result.matched_skills == ["Python"]
    assert result.missing_skills == ["Apache Spark"]
    assert result.skill_score == 0.5
    assert result.hybrid_score == compute_hybrid_score(result.match_score, 0.5)
    assert TFIDF_WEIGHT == 0.7
    assert SKILL_WEIGHT == 0.3
