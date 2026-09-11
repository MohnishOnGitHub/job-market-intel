from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import JobValidationError
from app.ingestion.models import RawJob
from app.ingestion.normalize import (
    clean_text,
    normalize_employment_type,
    normalize_job,
    normalize_url,
    parse_money,
    parse_timestamp,
)


def test_clean_text_collapses_whitespace_and_blanks():
    assert clean_text("  Bengaluru   ") == "Bengaluru"
    assert clean_text("San   Francisco") == "San Francisco"
    assert clean_text("   ") is None
    assert clean_text("") is None
    assert clean_text(None) is None


def test_normalize_url_lowercases_and_strips():
    assert (
        normalize_url(" HTTPS://Example.COM/jobs/1/ ")
        == "https://example.com/jobs/1"
    )
    assert normalize_url("not a url") == "not a url"
    assert normalize_url("  ") is None


def test_employment_type_maps_only_safe_values():
    assert normalize_employment_type("Full Time") == "full_time"
    assert normalize_employment_type("part-time") == "part_time"
    assert normalize_employment_type("contract") == "contract"
    assert normalize_employment_type("contractor") is None
    assert normalize_employment_type(None) is None


def test_parse_timestamp_iso_and_zulu():
    parsed = parse_timestamp("2024-06-01T12:30:00Z")
    assert parsed == datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc)
    assert parse_timestamp("not-a-date") is None
    assert parse_timestamp(None) is None


def test_parse_money_numeric_only():
    assert parse_money("120000") == Decimal("120000")
    assert parse_money(85000.5) == Decimal("85000.5")
    assert parse_money("abc") is None
    assert parse_money(True) is None


def test_normalize_job_requires_source_title_description():
    with pytest.raises(JobValidationError):
        normalize_job(RawJob(source="", title="A", description="B"))
    with pytest.raises(JobValidationError):
        normalize_job(RawJob(source="adzuna", title="  ", description="desc"))
    with pytest.raises(JobValidationError):
        normalize_job(RawJob(source="adzuna", title="Title", description=""))


def test_normalize_job_does_not_invent_salary_or_experience():
    job = normalize_job(
        RawJob(
            source="Adzuna",
            source_job_id=" 99 ",
            title="  Data Engineer ",
            description="Build pipelines",
            location="  Bengaluru   ",
            company=" Example ",
        )
    )
    assert job.source == "adzuna"
    assert job.source_job_id == "99"
    assert job.title == "Data Engineer"
    assert job.location_raw == "Bengaluru"
    assert job.location_normalized == "Bengaluru"
    assert job.salary_min is None
    assert job.experience_level is None
    assert job.content_hash
