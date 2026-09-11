from __future__ import annotations

from app.ingestion.dedupe import identity_keys, primary_identity
from app.ingestion.models import RawJob
from app.ingestion.normalize import normalize_job


def _job(**kwargs):
    defaults = {
        "source": "adzuna",
        "title": "Data Engineer",
        "description": "Build pipelines",
        "company": "Example",
        "location": "Bengaluru",
    }
    defaults.update(kwargs)
    return normalize_job(RawJob(**defaults))


def test_identity_prefers_source_and_source_job_id():
    job = _job(source_job_id="abc", source_url="https://example.com/a")
    assert primary_identity(job) == ("source_job_id", "abc")
    assert identity_keys(job)[1] == "abc"
    assert identity_keys(job)[3] is None


def test_identity_falls_back_to_url_then_hash():
    by_url = _job(source_url="https://example.com/jobs/1")
    assert primary_identity(by_url)[0] == "source_url"

    by_hash = _job()
    assert primary_identity(by_hash)[0] == "content_hash"


def test_same_company_and_title_are_not_the_same_job():
    first = _job(source_job_id="1", title="Data Engineer", company="Example")
    second = _job(source_job_id="2", title="Data Engineer", company="Example")
    assert identity_keys(first)[1] != identity_keys(second)[1]
    assert primary_identity(first) != primary_identity(second)
