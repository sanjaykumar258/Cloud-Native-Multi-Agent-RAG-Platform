"""
brain/vectorstore.py — ChromaDB wrapper with Ollama-based embeddings.

Uses nomic-embed-text (via Ollama) to embed chunks, with a
sentence-transformers fallback for when Ollama is not available.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import chromadb

from backend.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, EMBED_MODEL, OLLAMA_BASE_URL

logger = logging.getLogger(__name__)


# ─── Embedding function ───────────────────────────────────────────────────────

class OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB-compatible embedding function backed by Ollama."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        # Dynamically look up from env if not provided, allowing sidebar overrides to work
        from backend.config import EMBED_MODEL, OLLAMA_BASE_URL
        import os
        self.model = model or os.getenv("EMBED_MODEL", EMBED_MODEL)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL)).rstrip("/")

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        import requests

        if self.model == "all-MiniLM-L6-v2":
            return _st_embed_batch(input)

        embeddings = []
        for text in input:
            try:
                resp = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=60,
                )
                resp.raise_for_status()
                embeddings.append(resp.json()["embedding"])
            except Exception as exc:
                logger.warning("Ollama embedding failed, using fallback: %s", exc)
                embeddings.append(_st_embed_batch([text])[0])
        return embeddings


_st_model = None

def _st_embed_batch(texts: list[str]) -> list[list[float]]:
    """SentenceTransformer batched embedding for high throughput."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        # Load model only once
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Process the entire batch in one call
    embeddings = _st_model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


# ─── VectorStore class ────────────────────────────────────────────────────────

class VectorStore:
    """Thin wrapper around a ChromaDB persistent collection."""

    def __init__(self, collection_name: str = CHROMA_COLLECTION, persist_dir: str = CHROMA_PERSIST_DIR):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embed_fn = OllamaEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready: collection=%s, persist_dir=%s, count=%d",
            collection_name,
            persist_dir,
            self._collection.count(),
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[dict], batch_size: int = 100) -> int:
        """
        Embed and store chunk dicts. Returns number of chunks stored.
        Skips chunks whose ID already exists (idempotent).
        """
        if not chunks:
            return 0

        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [_chunk_id(c) for c in batch]
            texts = [c["text"] for c in batch]
            metas = [_sanitize_metadata(c["metadata"]) for c in batch]

            try:
                self._collection.upsert(ids=ids, documents=texts, metadatas=metas)
                total += len(batch)
            except Exception as exc:
                logger.error("Failed to upsert batch starting at %d: %s", i, exc)

        return total

    def clear_by_source(self, source_name: str) -> None:
        """Remove all chunks from a given source file."""
        try:
            self._collection.delete(where={"source": source_name})
            logger.info("Cleared existing chunks for source: %s", source_name)
        except Exception as exc:
            logger.warning("Could not clear source %s: %s", source_name, exc)

    def clear_all(self) -> None:
        """Wipes the entire collection clean efficiently."""
        try:
            count_before = self._collection.count()
            if count_before > 0:
                # Delete everything by filtering for source != ""
                self._collection.delete(where={"source": {"$ne": ""}})
            logger.info("Cleared all %d chunks from the vector store.", count_before)
        except Exception as exc:
            logger.error("Failed to clear vector store: %s", exc)
            # Fallback to slower method if above fails
            try:
                sources = self.list_sources()
                for src in sources:
                    self.clear_by_source(src)
            except Exception:
                pass

    # ── Read ──────────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Semantic search. Returns a list of result dicts:
          { text, metadata, distance }
        """
        kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(n_results, max(self._collection.count(), 1)),
        }
        if where:
            kwargs["where"] = where

        try:
            results = self._collection.query(**kwargs)
        except Exception as exc:
            logger.error("Query failed: %s", exc)
            return []

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            {"text": d, "metadata": m, "distance": dist}
            for d, m, dist in zip(docs, metas, distances)
        ]

    def count(self) -> int:
        return self._collection.count()

    def list_sources(self) -> list[str]:
        """Return unique source filenames indexed in this collection."""
        if self._collection.count() == 0:
            return []
        try:
            all_metas = self._collection.get(include=["metadatas"])["metadatas"]
            return sorted({m.get("source", "unknown") for m in all_metas})
        except Exception:
            return []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _chunk_id(chunk: dict) -> str:
    """Deterministic ID based on source + chunk index."""
    key = f"{chunk['metadata'].get('source', '')}:{chunk['metadata'].get('chunk_index', 0)}"
    return hashlib.md5(key.encode()).hexdigest()


def _sanitize_metadata(meta: dict) -> dict:
    """ChromaDB only accepts str, int, float, bool values in metadata."""
    clean = {}
    for k, v in meta.items():
        if v is None:
            clean[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean
