"""Local persistent vector store for HR policy chunks (ChromaDB, on-disk).

We always pass our own embeddings in (see embeddings.py) so Chroma is used
purely as a persistent nearest-neighbour index, not as an embedding provider.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings

_client = None
_collection = None

COLLECTION_NAME = "hr_policy_chunks"


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb

    store_dir = Path(settings.ai_vector_store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=str(store_dir))
    _collection = _client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    return _collection


def upsert_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    if not ids:
        return
    collection = _get_collection()
    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def delete_policy_chunks(policy_id: int) -> None:
    collection = _get_collection()
    collection.delete(where={"policy_id": policy_id})


def query(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    hits: list[dict] = []
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    for document, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        hits.append(
            {
                "text": document,
                "metadata": metadata,
                # Cosine distance -> similarity score in [0, 1] (higher is better).
                "score": max(0.0, 1.0 - distance),
            }
        )
    return hits


def is_empty() -> bool:
    collection = _get_collection()
    return collection.count() == 0
