from __future__ import annotations

from app.core.config import get_settings


def embedding_kind(provider_name: str) -> str:
    lowered = (provider_name or "").strip().lower()
    if "sentence-transformer" in lowered or lowered in {"st", "sentence_transformers"}:
        return "semantic"
    return "lexical_hashing"


def hybrid_ranking_label(provider_name: str) -> str:
    if embedding_kind(provider_name) == "semantic":
        return "Semantic + structured hybrid"
    return "Lexical vector + structured hybrid"


def ranking_status_payload() -> dict:
    settings = get_settings()
    provider = settings.embedding_provider
    kind = embedding_kind(provider)
    return {
        "embedding_provider": provider,
        "embedding_model": settings.embedding_model,
        "embedding_kind": kind,
        "hybrid_label": hybrid_ranking_label(provider),
        "tfidf_label": "Pairwise TF-IDF baseline",
        "weights": {
            "semantic": settings.rank_weight_semantic,
            "skill": settings.rank_weight_skill,
            "experience": settings.rank_weight_experience,
            "recency": settings.rank_weight_recency,
            "location": settings.rank_weight_location,
        },
    }
