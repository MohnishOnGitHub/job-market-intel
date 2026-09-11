from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import List, Protocol, Sequence

from app.core.config import get_settings
from app.core.exceptions import EmbeddingProviderError

_TOKEN = re.compile(r"[a-z0-9+#.]{2,}")

HASHING_PROVIDER_NAME = "hashing-v1"
DEFAULT_HASHING_DIMENSION = 256


class EmbeddingProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def dimension(self) -> int:
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...

    def embed_query(self, text: str) -> List[float]:
        ...


class HashingEmbeddingProvider:
    """Deterministic hashed-ngram embeddings.

    This is a local lexical baseline so tests and machines without
    sentence-transformers can generate vectors. It is not a semantic
    sentence model. Set EMBEDDING_PROVIDER=sentence-transformers for
    real semantic embeddings.
    """

    def __init__(self, dimension: int = DEFAULT_HASHING_DIMENSION) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be greater than 0")
        self._dimension = dimension

    @property
    def name(self) -> str:
        return f"{HASHING_PROVIDER_NAME}:{self._dimension}"

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self._dimension
        tokens = _TOKEN.findall((text or "").lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return _l2_normalize(vector)


class SentenceTransformerProvider:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderError(
                "sentence-transformers is not installed. "
                "pip install sentence-transformers or use EMBEDDING_PROVIDER=hashing."
            ) from exc
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = int(self._model.get_sentence_embedding_dimension())

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self._model_name}"

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            [text or "" for text in texts],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [list(map(float, row)) for row in vectors]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    score = sum(a * b for a, b in zip(left, right))
    return _clip_unit(score)


def _l2_normalize(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _clip_unit(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = (settings.embedding_provider or "hashing").strip().lower()
    if provider in {"hashing", HASHING_PROVIDER_NAME, "hashing-v1"}:
        return HashingEmbeddingProvider(dimension=settings.embedding_dimension)
    if provider in {"sentence-transformers", "sentence_transformers", "st"}:
        return SentenceTransformerProvider(settings.embedding_model)
    raise EmbeddingProviderError(f"Unknown embedding provider: {provider}")


def clear_embedding_provider_cache() -> None:
    get_embedding_provider.cache_clear()
