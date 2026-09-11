from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass
class RawJob:
    """Source payload before canonical normalization."""

    source: str
    source_job_id: Optional[str] = None
    source_url: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[Any] = None
    salary_max: Optional[Any] = None
    salary_currency: Optional[str] = None
    posted_at: Optional[Any] = None
    raw_payload: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedJob:
    source: str
    title: str
    description: str
    content_hash: str
    source_job_id: Optional[str] = None
    source_url: Optional[str] = None
    company: Optional[str] = None
    location_raw: Optional[str] = None
    location_normalized: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_currency: Optional[str] = None
    posted_at: Optional[datetime] = None


@dataclass
class IngestionCounts:
    records_fetched: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    status: str = "running"
    error_summary: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
