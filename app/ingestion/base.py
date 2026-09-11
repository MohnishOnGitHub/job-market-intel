from __future__ import annotations

from typing import Iterable, Protocol

from app.ingestion.models import RawJob


class JobSource(Protocol):
    name: str

    def fetch_jobs(self) -> Iterable[RawJob]:
        """Yield raw jobs from the source.

        Source-wide failures (auth, HTTP errors, network) must raise
        JobSourceError. Per-record mapping problems should be left to the
        ingestion service after a RawJob is produced, or raised as
        JobValidationError from the mapper.
        """
