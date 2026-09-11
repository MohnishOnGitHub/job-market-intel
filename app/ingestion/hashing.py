from __future__ import annotations

import hashlib
from typing import Optional

# SHA-256 over these normalized fields, joined by newline:
#   1. title (lowercased)
#   2. company (lowercased, empty if missing)
#   3. description (whitespace-normalized, original case)
#   4. location (lowercased location_normalized, empty if missing)
CONTENT_HASH_FIELDS = ("title", "company", "description", "location")


def job_content_hash(
    title: str,
    company: Optional[str],
    description: str,
    location: Optional[str],
) -> str:
    payload = "\n".join(
        [
            (title or "").strip().lower(),
            (company or "").strip().lower(),
            (description or "").strip(),
            (location or "").strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
