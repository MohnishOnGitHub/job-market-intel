from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, Optional

import requests

from app.core.exceptions import JobSourceError, JobValidationError
from app.ingestion.models import RawJob

SOURCE_NAME = "adzuna"
ADZUNA_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def map_adzuna_job(payload: Any) -> RawJob:
    if not isinstance(payload, dict):
        raise JobValidationError("Adzuna job payload must be an object")

    company = payload.get("company")
    company_name = company.get("display_name") if isinstance(company, dict) else None

    location = payload.get("location")
    location_name = location.get("display_name") if isinstance(location, dict) else None

    job_id = payload.get("id")
    source_job_id = str(job_id) if job_id is not None and str(job_id).strip() else None

    employment = payload.get("contract_time") or payload.get("contract_type")

    salary_min = payload.get("salary_min")
    salary_max = payload.get("salary_max")
    if payload.get("salary_is_predicted") in (1, "1", True, "true"):
        salary_min = None
        salary_max = None

    return RawJob(
        source=SOURCE_NAME,
        source_job_id=source_job_id,
        source_url=payload.get("redirect_url"),
        company=company_name,
        title=payload.get("title"),
        description=payload.get("description"),
        location=location_name,
        employment_type=employment,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=payload.get("salary_currency"),
        posted_at=payload.get("created"),
        raw_payload=payload,
    )


class AdzunaSource:
    name = SOURCE_NAME

    def __init__(
        self,
        app_id: str,
        app_key: str,
        country: str = "in",
        query: str = "python developer",
        location: Optional[str] = None,
        pages: int = 1,
        results_per_page: int = 10,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ) -> None:
        if not app_id or not app_key:
            raise JobSourceError("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set.")
        if pages < 1:
            raise JobSourceError("pages must be at least 1")
        if results_per_page < 1:
            raise JobSourceError("results_per_page must be at least 1")

        self.app_id = app_id
        self.app_key = app_key
        self.country = (country or "in").strip().lower() or "in"
        self.query = query
        self.location = location
        self.pages = pages
        self.results_per_page = results_per_page
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_jobs(self) -> Iterator[RawJob]:
        for page in range(1, self.pages + 1):
            yield from self._fetch_page(page)

    def _fetch_page(self, page: int) -> Iterable[RawJob]:
        params: Dict[str, Any] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": self.results_per_page,
            "what": self.query,
        }
        if self.location:
            params["where"] = self.location

        url = ADZUNA_SEARCH_URL.format(country=self.country, page=page)
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise JobSourceError("Adzuna request failed.") from exc

        if response.status_code in (401, 403):
            raise JobSourceError("Adzuna authentication failed.")
        if response.status_code != 200:
            raise JobSourceError("Adzuna request failed.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise JobSourceError("Adzuna returned invalid JSON.") from exc

        results = payload.get("results") if isinstance(payload, dict) else None
        if results is None:
            return
        if not isinstance(results, list):
            raise JobSourceError("Adzuna returned an unexpected results payload.")

        for item in results:
            if not isinstance(item, dict):
                yield RawJob(source=SOURCE_NAME)
                continue
            yield map_adzuna_job(item)
