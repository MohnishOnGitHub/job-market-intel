from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from app.core.exceptions import JobValidationError
from app.ingestion.hashing import job_content_hash
from app.ingestion.models import NormalizedJob, RawJob

_WHITESPACE = re.compile(r"\s+")

SAFE_EMPLOYMENT_TYPES = {
    "full_time": "full_time",
    "full-time": "full_time",
    "full time": "full_time",
    "part_time": "part_time",
    "part-time": "part_time",
    "part time": "part_time",
    "contract": "contract",
    "permanent": "permanent",
    "internship": "internship",
    "temporary": "temporary",
}


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ")
    text = _WHITESPACE.sub(" ", text).strip()
    return text or None


def normalize_url(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    parts = urlsplit(text)
    if not parts.scheme or not parts.netloc:
        return text
    path = parts.path.rstrip("/")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, parts.query, "")
    )


def normalize_employment_type(value: Any) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return SAFE_EMPLOYMENT_TYPES.get(text.lower())


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = clean_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_money(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value):  # NaN
            return None
        return Decimal(str(value))
    text = clean_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def normalize_job(raw: RawJob) -> NormalizedJob:
    source = clean_text(raw.source)
    if not source:
        raise JobValidationError("source is required")

    title = clean_text(raw.title)
    description = clean_text(raw.description)
    if not title:
        raise JobValidationError("title is required")
    if not description:
        raise JobValidationError("description is required")

    location_raw = clean_text(raw.location)
    source_job_id = clean_text(raw.source_job_id)
    company = clean_text(raw.company)
    experience_level = clean_text(raw.experience_level)
    salary_currency = clean_text(raw.salary_currency)
    if salary_currency:
        salary_currency = salary_currency.upper()

    normalized = NormalizedJob(
        source=source.lower(),
        source_job_id=source_job_id,
        source_url=normalize_url(raw.source_url),
        company=company,
        title=title,
        description=description,
        location_raw=location_raw,
        location_normalized=location_raw,
        employment_type=normalize_employment_type(raw.employment_type),
        experience_level=experience_level,
        salary_min=parse_money(raw.salary_min),
        salary_max=parse_money(raw.salary_max),
        salary_currency=salary_currency,
        posted_at=parse_timestamp(raw.posted_at),
        content_hash="",
    )
    normalized.content_hash = job_content_hash(
        normalized.title,
        normalized.company,
        normalized.description,
        normalized.location_normalized,
    )
    return normalized
