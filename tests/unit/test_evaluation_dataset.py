from __future__ import annotations

import pytest

from app.evaluation.dataset import (
    EvaluationDataset,
    EvaluationDatasetError,
    RelevanceLabel,
    default_dataset_path,
    load_evaluation_dataset,
    validate_dataset,
)
from app.evaluation.v1_authoring import author_label, build_v1_dataset


def _dataset(**overrides):
    base = build_v1_dataset()
    return EvaluationDataset(
        version=overrides.get("version", base.version),
        resumes=overrides.get("resumes", base.resumes),
        jobs=overrides.get("jobs", base.jobs),
        labels=overrides.get("labels", base.labels),
        binary_threshold=base.binary_threshold,
    )


def test_v1_dataset_is_valid_and_complete():
    dataset = build_v1_dataset()
    validate_dataset(dataset)
    assert len(dataset.resumes) == 8
    assert len(dataset.jobs) == 32
    assert len(dataset.labels) == 8 * 32
    assert {item.split for item in dataset.resumes} == {"validation", "test"}
    assert sum(1 for item in dataset.resumes if item.split == "test") == 3
    assert all(item.synthetic for item in dataset.resumes)
    assert set(item.relevance for item in dataset.labels) <= {0, 1, 2, 3}


def test_duplicate_judgment_is_rejected():
    dataset = build_v1_dataset()
    labels = list(dataset.labels) + [dataset.labels[0]]
    with pytest.raises(EvaluationDatasetError, match="Duplicate"):
        validate_dataset(_dataset(labels=labels))


def test_unknown_ids_are_rejected():
    dataset = build_v1_dataset()
    labels = list(dataset.labels) + [
        RelevanceLabel(resume_id="missing", job_id=1, relevance=2)
    ]
    with pytest.raises(EvaluationDatasetError, match="Unknown resume"):
        validate_dataset(_dataset(labels=labels))
    labels = list(dataset.labels) + [
        RelevanceLabel(resume_id=dataset.resumes[0].id, job_id=999, relevance=1)
    ]
    with pytest.raises(EvaluationDatasetError, match="Unknown job"):
        validate_dataset(_dataset(labels=labels))


def test_invalid_relevance_is_rejected():
    dataset = build_v1_dataset()
    labels = list(dataset.labels)
    labels[0] = RelevanceLabel(
        resume_id=labels[0].resume_id,
        job_id=labels[0].job_id,
        relevance=4,
    )
    with pytest.raises(EvaluationDatasetError, match="Invalid relevance"):
        validate_dataset(_dataset(labels=labels))


def test_author_rubric_is_independent_of_scores():
    assert author_label("de", "mid", "de", "mid") == 3
    assert author_label("de", "mid", "de", "junior") == 2
    assert author_label("de", "mid", "da", "mid") == 0
    assert author_label("de", "mid", "analytics", "mid") == 2
    assert author_label("de", "mid", "other", "mid") == 0
    assert author_label("ds", "senior", "mle", "senior") == 2


def test_committed_v1_json_loads_and_matches_authoring_counts():
    path = default_dataset_path()
    if not path.exists():
        pytest.skip("committed v1 dataset.json is not present")
    loaded = load_evaluation_dataset(path)
    authored = build_v1_dataset()
    assert len(loaded.resumes) == len(authored.resumes)
    assert len(loaded.jobs) == len(authored.jobs)
    assert len(loaded.labels) == len(authored.labels)
    assert loaded.binary_threshold == 2


def test_clinical_bait_is_irrelevant_for_every_profile():
    dataset = build_v1_dataset()
    for resume in dataset.resumes:
        graded = dataset.graded_relevance(resume.id)
        assert graded[15] == 0
        assert graded[16] == 0
