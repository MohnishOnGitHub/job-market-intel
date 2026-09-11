from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

FRESHNESS_BUCKETS = (
    "0-7 days",
    "8-30 days",
    "31-60 days",
    "61+ days",
    "unknown",
)


def freshness_bucket(
    posted_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> str:
    """Bucket a posting date. Missing posted_at is unknown, not invented."""
    if posted_at is None:
        return "unknown"
    moment = now or datetime.now(timezone.utc)
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    age = moment - posted_at
    if age <= timedelta(days=7):
        return "0-7 days"
    if age <= timedelta(days=30):
        return "8-30 days"
    if age <= timedelta(days=60):
        return "31-60 days"
    return "61+ days"
