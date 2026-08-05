"""Local embedding generation for the Policy RAG vector store.

Uses a small sentence-transformers model that runs entirely on-device -- no
API key and no network call is needed to embed policy chunks or user
questions, which keeps the RAG path usable even before an LLM provider key
is configured.
"""

from __future__ import annotations

from app.core.config import settings

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.ai_embedding_model_name)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
