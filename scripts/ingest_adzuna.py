#!/usr/bin/env python3
"""Manual Adzuna job loader.

This is not a test. It calls a live HTTP API and writes to PostgreSQL.
Do not run it unless you intend to insert rows into your local database.

Required environment variables:
  DATABASE_URL
  ADZUNA_APP_ID
  ADZUNA_APP_KEY
"""

from __future__ import annotations

import os
import sys

import psycopg2
import requests
from dotenv import load_dotenv

ADZUNA_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/in/search/{page}"


def parse_job(job: dict) -> dict:
    return {
        "title": job.get("title"),
        "company": job.get("company", {}).get("display_name"),
        "location": job.get("location", {}).get("display_name"),
        "description": job.get("description"),
        "created_at": job.get("created"),
    }


def main() -> int:
    load_dotenv()

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    app_id = os.getenv("ADZUNA_APP_ID") or os.getenv("APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY") or os.getenv("APP_KEY")

    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    if not app_id or not app_key:
        print("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set.", file=sys.stderr)
        return 1

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 5,
        "what": "python developer",
        "where": "bangalore",
    }

    try:
        conn = psycopg2.connect(database_url)
    except psycopg2.Error:
        print("Could not connect to the database.", file=sys.stderr)
        return 1

    inserted = 0
    try:
        cur = conn.cursor()
        for page in range(1, 4):
            url = ADZUNA_SEARCH_URL.format(page=page)
            response = requests.get(url, params=params, timeout=30)
            print(f"Page {page} status: {response.status_code}")
            if response.status_code != 200:
                print("Adzuna request failed.", file=sys.stderr)
                continue

            for job in response.json().get("results", []):
                parsed = parse_job(job)
                cur.execute(
                    """
                    INSERT INTO jobs (title, company, location, description, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        parsed["title"],
                        parsed["company"],
                        parsed["location"],
                        parsed["description"],
                        parsed["created_at"],
                    ),
                )
                inserted += cur.rowcount

        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        print("Ingestion failed.", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print(f"Ingestion finished. Rows reported inserted: {inserted}.")
    print("ON CONFLICT DO NOTHING only skips rows when a unique constraint exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
