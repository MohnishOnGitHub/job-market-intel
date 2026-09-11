from __future__ import annotations

from app.ingestion.hashing import CONTENT_HASH_FIELDS, job_content_hash
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job


def test_hash_fields_are_documented():
    assert CONTENT_HASH_FIELDS == ("title", "company", "description", "location")


def test_content_hash_is_deterministic():
    first = job_content_hash("Data Engineer", "Example", "Build pipelines", "Bengaluru")
    second = job_content_hash("Data Engineer", "Example", "Build pipelines", "Bengaluru")
    assert first == second
    assert len(first) == 64


def test_content_hash_changes_when_material_field_changes():
    base = job_content_hash("Data Engineer", "Example", "Build pipelines", "Bengaluru")
    assert job_content_hash("ML Engineer", "Example", "Build pipelines", "Bengaluru") != base
    assert job_content_hash("Data Engineer", "Other", "Build pipelines", "Bengaluru") != base
    assert job_content_hash("Data Engineer", "Example", "Different work", "Bengaluru") != base
    assert job_content_hash("Data Engineer", "Example", "Build pipelines", "Pune") != base


def test_normalized_whitespace_does_not_change_hash():
    left = normalize_job(
        RawJob(source="adzuna", title="Data Engineer", description="Build pipelines", location="Bengaluru")
    )
    right = normalize_job(
        RawJob(
            source="adzuna",
            title="  Data   Engineer ",
            description=" Build   pipelines ",
            location="  Bengaluru  ",
        )
    )
    assert left.content_hash == right.content_hash
