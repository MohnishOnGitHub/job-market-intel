from __future__ import annotations

import pytest
import requests

from app.core.exceptions import JobSourceError, JobValidationError
from app.ingestion.sources.adzuna import AdzunaSource, map_adzuna_job


SAMPLE_JOB = {
    "id": 12345,
    "title": "Python Developer",
    "description": "Work with FastAPI and SQL",
    "created": "2024-05-01T10:00:00Z",
    "redirect_url": "https://www.adzuna.com/jobs/12345",
    "company": {"display_name": "Example Corp"},
    "location": {"display_name": "Bengaluru"},
    "salary_min": 100000,
    "salary_max": 150000,
    "salary_is_predicted": "0",
    "contract_time": "full_time",
    "salary_currency": "INR",
}


def test_map_adzuna_job_extracts_raw_fields():
    raw = map_adzuna_job(SAMPLE_JOB)
    assert raw.source == "adzuna"
    assert raw.source_job_id == "12345"
    assert raw.company == "Example Corp"
    assert raw.location == "Bengaluru"
    assert raw.employment_type == "full_time"
    assert raw.salary_min == 100000
    assert raw.posted_at == "2024-05-01T10:00:00Z"


def test_map_adzuna_job_ignores_predicted_salary():
    payload = dict(SAMPLE_JOB)
    payload["salary_is_predicted"] = "1"
    raw = map_adzuna_job(payload)
    assert raw.salary_min is None
    assert raw.salary_max is None


def test_map_adzuna_job_rejects_non_object():
    with pytest.raises(JobValidationError):
        map_adzuna_job(["not", "a", "job"])


class _Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.response


def test_adzuna_source_maps_mocked_results():
    session = _Session(_Response(200, {"results": [SAMPLE_JOB]}))
    source = AdzunaSource("id", "key", session=session, pages=1)
    jobs = list(source.fetch_jobs())
    assert len(jobs) == 1
    assert jobs[0].source_job_id == "12345"
    assert "app_key" in session.calls[0]["params"]


def test_adzuna_source_fails_on_auth_error():
    source = AdzunaSource("id", "key", session=_Session(_Response(401)))
    with pytest.raises(JobSourceError, match="authentication"):
        list(source.fetch_jobs())


def test_adzuna_source_fails_on_http_error():
    source = AdzunaSource("id", "key", session=_Session(_Response(500)))
    with pytest.raises(JobSourceError, match="request failed"):
        list(source.fetch_jobs())


def test_adzuna_source_fails_on_network_error():
    class BoomSession:
        def get(self, *args, **kwargs):
            raise requests.ConnectionError("offline")

    source = AdzunaSource("id", "key", session=BoomSession())
    with pytest.raises(JobSourceError):
        list(source.fetch_jobs())


def test_malformed_result_is_yielded_as_incomplete_raw_job():
    session = _Session(_Response(200, {"results": [SAMPLE_JOB, "bad"]}))
    source = AdzunaSource("id", "key", session=session)
    jobs = list(source.fetch_jobs())
    assert jobs[0].title == "Python Developer"
    assert jobs[1].title is None
