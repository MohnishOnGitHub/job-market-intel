from __future__ import annotations

from app.services.embedding_provider import (
    HashingEmbeddingProvider,
    cosine_similarity,
)
from app.services.embedding_text import build_embedding_text, embedding_content_hash


def test_hashing_embeddings_are_deterministic():
    provider = HashingEmbeddingProvider(dimension=32)
    first = provider.embed_query("python sql spark")
    second = provider.embed_query("python sql spark")
    assert first == second
    assert provider.dimension == 32
    assert provider.name == "hashing-v1:32"


def test_similar_texts_rank_above_unrelated_texts():
    provider = HashingEmbeddingProvider(dimension=64)
    query = provider.embed_query("python data engineer spark sql")
    close = provider.embed_documents(["Title: Data Engineer\npython spark sql pipelines"])[0]
    far = provider.embed_documents(["Title: Nurse\nnight shift patient care"])[0]
    assert cosine_similarity(query, close) > cosine_similarity(query, far)


def test_empty_text_embedding_is_zero_vector():
    provider = HashingEmbeddingProvider(dimension=8)
    vector = provider.embed_query("   ")
    assert vector == [0.0] * 8
    assert cosine_similarity(vector, provider.embed_query("python")) == 0.0


def test_embedding_text_is_deterministic_and_includes_skills():
    text = build_embedding_text(
        title="Data Engineer",
        company="Example",
        location="Bengaluru",
        description="Build pipelines",
        skills=["Python", "SQL"],
    )
    assert text == (
        "Title: Data Engineer\n"
        "Company: Example\n"
        "Location: Bengaluru\n"
        "Description:\nBuild pipelines\n"
        "Skills:\nPython, SQL"
    )
    first = embedding_content_hash(text, "hashing-v1:256")
    second = embedding_content_hash(text, "hashing-v1:256")
    assert first == second
    assert first != embedding_content_hash(text, "other-model")
