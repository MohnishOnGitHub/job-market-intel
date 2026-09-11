from __future__ import annotations

import hashlib
from typing import Optional, Sequence


def build_embedding_text(
    *,
    title: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    skills: Optional[Sequence[str]] = None,
) -> str:
    """Deterministic job text used for embedding generation."""
    skill_line = ", ".join(skills or [])
    return (
        f"Title: {title or ''}\n"
        f"Company: {company or ''}\n"
        f"Location: {location or ''}\n"
        f"Description:\n{description or ''}\n"
        f"Skills:\n{skill_line}"
    )


def embedding_content_hash(text: str, embedding_model: str) -> str:
    payload = f"{embedding_model}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
