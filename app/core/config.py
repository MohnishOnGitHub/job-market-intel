from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _int_env(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return value


def _float_env(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    app_env: str
    log_level: str
    max_upload_mb: int
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    adzuna_country: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    candidate_count: int
    rank_weight_semantic: float
    rank_weight_skill: float
    rank_weight_experience: float
    rank_weight_recency: float
    rank_weight_location: float
    recency_tau_days: float

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        max_upload_mb = _int_env("MAX_UPLOAD_MB", "5")
        if max_upload_mb <= 0:
            raise ValueError("MAX_UPLOAD_MB must be greater than 0")

        database_url = os.getenv("DATABASE_URL")
        if database_url is not None:
            database_url = database_url.strip() or None

        country = (os.getenv("ADZUNA_COUNTRY") or "in").strip().lower() or "in"
        embedding_dimension = _int_env("EMBEDDING_DIMENSION", "256")
        if embedding_dimension <= 0:
            raise ValueError("EMBEDDING_DIMENSION must be greater than 0")
        candidate_count = _int_env("CANDIDATE_COUNT", "100")
        if candidate_count <= 0:
            raise ValueError("CANDIDATE_COUNT must be greater than 0")
        recency_tau_days = _float_env("RECENCY_TAU_DAYS", "30")
        if recency_tau_days <= 0:
            raise ValueError("RECENCY_TAU_DAYS must be greater than 0")

        return cls(
            database_url=database_url,
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_upload_mb=max_upload_mb,
            adzuna_app_id=_optional_env("ADZUNA_APP_ID") or _optional_env("APP_ID"),
            adzuna_app_key=_optional_env("ADZUNA_APP_KEY") or _optional_env("APP_KEY"),
            adzuna_country=country,
            embedding_provider=(os.getenv("EMBEDDING_PROVIDER") or "hashing").strip(),
            embedding_model=(
                os.getenv("EMBEDDING_MODEL") or "all-MiniLM-L6-v2"
            ).strip()
            or "all-MiniLM-L6-v2",
            embedding_dimension=embedding_dimension,
            candidate_count=candidate_count,
            rank_weight_semantic=_float_env("RANK_WEIGHT_SEMANTIC", "0.50"),
            rank_weight_skill=_float_env("RANK_WEIGHT_SKILL", "0.25"),
            rank_weight_experience=_float_env("RANK_WEIGHT_EXPERIENCE", "0.10"),
            rank_weight_recency=_float_env("RANK_WEIGHT_RECENCY", "0.10"),
            rank_weight_location=_float_env("RANK_WEIGHT_LOCATION", "0.05"),
            recency_tau_days=recency_tau_days,
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
    from app.services.embedding_provider import clear_embedding_provider_cache

    clear_embedding_provider_cache()
