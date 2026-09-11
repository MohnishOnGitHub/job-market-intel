from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError


@contextmanager
def get_connection() -> Iterator:
    settings = get_settings()
    if not settings.database_url:
        raise DatabaseUnavailableError("DATABASE_URL is not set.")

    try:
        conn = psycopg2.connect(settings.database_url)
    except psycopg2.Error as exc:
        raise DatabaseUnavailableError("Database is unavailable.") from exc

    try:
        yield conn
    finally:
        conn.close()
