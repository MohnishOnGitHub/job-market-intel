from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    app_env: str
    log_level: str
    max_upload_mb: int

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        raw_max = os.getenv("MAX_UPLOAD_MB", "5")
        try:
            max_upload_mb = int(raw_max)
        except ValueError as exc:
            raise ValueError("MAX_UPLOAD_MB must be an integer") from exc
        if max_upload_mb <= 0:
            raise ValueError("MAX_UPLOAD_MB must be greater than 0")

        database_url = os.getenv("DATABASE_URL")
        if database_url is not None:
            database_url = database_url.strip() or None

        return cls(
            database_url=database_url,
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_upload_mb=max_upload_mb,
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
