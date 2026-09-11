from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.freshness import freshness_bucket


NOW = datetime(2026, 9, 11, tzinfo=timezone.utc)


def test_freshness_buckets_and_unknown():
    assert freshness_bucket(None, NOW) == "unknown"
    assert freshness_bucket(NOW, NOW) == "0-7 days"
    assert freshness_bucket(NOW - timedelta(days=7), NOW) == "0-7 days"
    assert freshness_bucket(NOW - timedelta(days=8), NOW) == "8-30 days"
    assert freshness_bucket(NOW - timedelta(days=30), NOW) == "8-30 days"
    assert freshness_bucket(NOW - timedelta(days=31), NOW) == "31-60 days"
    assert freshness_bucket(NOW - timedelta(days=61), NOW) == "61+ days"
