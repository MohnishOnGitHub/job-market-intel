from __future__ import annotations

from typing import Dict

from pydantic import BaseModel


class RankingStatusResponse(BaseModel):
    embedding_provider: str
    embedding_model: str
    embedding_kind: str
    hybrid_label: str
    tfidf_label: str
    weights: Dict[str, float]
