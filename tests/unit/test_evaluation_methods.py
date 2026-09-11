from __future__ import annotations

import pytest

from app.evaluation.dataset import EvaluationResume
from app.evaluation.methods import rank_skills, rank_tfidf, stable_rank
from app.evaluation.weights import normalize_weight_tuple, ranking_weights_from_tuple
from app.schemas.job import Job
from app.services.ranking import pairwise_tfidf_score
from app.services.skill_extractor import compute_skill_score, extract_skills, skill_overlap


def test_stable_rank_breaks_ties_by_job_id():
    ranked = stable_rank([(3, 0.5), (1, 0.5), (2, 0.9)])
    assert [item.job_id for item in ranked] == [2, 1, 3]


def test_skill_method_matches_production_skill_score():
    resume = EvaluationResume(
        id="r",
        text="python sql spark",
        profile="Data Engineer",
        seniority="mid",
        split="test",
    )
    jobs = [
        Job(id=1, description="python sql spark", persisted_skills=["Python", "SQL", "Apache Spark"]),
        Job(id=2, description="team player", persisted_skills=[]),
    ]
    ranked = rank_skills(resume, jobs)
    resume_skills = extract_skills(resume.text)
    expected = []
    for job in jobs:
        matched, _ = skill_overlap(resume_skills, job.persisted_skills or [])
        expected.append((job.id, compute_skill_score(matched, job.persisted_skills or [])))
    assert ranked[0].job_id == 1
    assert ranked[0].score == expected[0][1]
    assert ranked[1].score == 0


def test_tfidf_method_uses_pairwise_cosine_only():
    resume = EvaluationResume(
        id="r",
        text="python sql fastapi",
        profile="Backend",
        seniority="mid",
        split="test",
    )
    jobs = [
        Job(id=2, description="python sql fastapi backend"),
        Job(id=1, description="registered nurse night shift"),
    ]
    ranked = rank_tfidf(resume, jobs)
    assert ranked[0].job_id == 2
    assert ranked[0].score == pairwise_tfidf_score(resume.text, jobs[0].description)
    assert ranked[1].score == pairwise_tfidf_score(resume.text, jobs[1].description)


def test_weight_normalization_and_rejection():
    values = normalize_weight_tuple((0.50, 0.25, 0.10, 0.10, 0.05))
    assert abs(sum(values) - 1.0) < 1e-9
    with pytest.raises(ValueError):
        normalize_weight_tuple((-0.1, 0.5, 0.2, 0.2, 0.2))
    weights = ranking_weights_from_tuple((1, 1, 0, 0, 0))
    assert abs(weights.semantic - 0.5) < 1e-9
    assert abs(weights.skill - 0.5) < 1e-9
