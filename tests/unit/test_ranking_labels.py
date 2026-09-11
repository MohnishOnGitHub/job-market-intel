from __future__ import annotations

from app.services.ranking_labels import embedding_kind, hybrid_ranking_label, ranking_status_payload


def test_hashing_is_lexical_not_semantic():
    assert embedding_kind("hashing") == "lexical_hashing"
    assert embedding_kind("hashing-v1:256") == "lexical_hashing"
    assert hybrid_ranking_label("hashing-v1:256") == "Lexical vector + structured hybrid"
    assert embedding_kind("sentence-transformers:all-MiniLM-L6-v2") == "semantic"
    assert hybrid_ranking_label("sentence-transformers:x") == "Semantic + structured hybrid"


def test_ranking_status_does_not_need_database():
    payload = ranking_status_payload()
    assert payload["tfidf_label"] == "Pairwise TF-IDF baseline"
    assert "hybrid_label" in payload
    assert "weights" in payload
