"""
brain/chunker.py — Semantic chunker.

Rather than cutting every N characters, we embed each sentence and
detect "topic shifts" by measuring cosine-similarity drops between
consecutive sentences. A new chunk begins whenever similarity falls
below CHUNK_THRESHOLD.

If the embedding model is unavailable the chunker gracefully falls
back to a simple character-length splitter.
"""

from __future__ import annotations

import logging
import re
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)


# ─── Public API ───────────────────────────────────────────────────────────────

def chunk_elements(elements: list[dict]) -> list[dict]:
    """
    Take a list of element dicts (from loader.py) and return a flat list
    of chunk dicts ready for embedding & storage.

    Each chunk dict has:
      - text       : the chunk content
      - metadata   : source, page_number, element_type, heading, chunk_index
    """
    chunks: list[dict] = []
    for element in elements:
        text = element["text"]
        meta = element["metadata"]
        element_type = meta.get("element_type", "NarrativeText")
        source_name = meta.get("source", "Unknown Document")

        # Keep Tables as single chunks (don't split them)
        if element_type == "Table":
            enriched_text = f"Document: {source_name}\nContent:\n{_truncate(text)}"
            chunks.append({
                "text": enriched_text,
                "metadata": {**meta, "chunk_index": len(chunks)},
            })
            continue

        # Semantic split for narrative text
        sub_chunks = _semantic_split(text)
        for sc in sub_chunks:
            if sc.strip():
                enriched_text = f"Document: {source_name}\nContent:\n{sc.strip()}"
                chunks.append({
                    "text": enriched_text,
                    "metadata": {**meta, "chunk_index": len(chunks)},
                })

    logger.info("Produced %d chunks from %d elements.", len(chunks), len(elements))
    return chunks


# ─── Semantic splitter ────────────────────────────────────────────────────────

def _semantic_split(text: str) -> list[str]:
    """
    Split text at semantic breakpoints detected by cosine-similarity drops.
    Falls back to character-level splitting if the embedding model is not available.
    """
    from backend.config import CHUNK_THRESHOLD, MAX_CHUNK_SIZE, MIN_CHUNK_SIZE

    sentences = _split_into_sentences(text)
    if len(sentences) <= 1:
        return _char_split(text)

    embeddings = _embed_sentences(sentences)
    if embeddings is None:
        # Embedding unavailable — fall back
        return _char_split(text)

    chunks: list[str] = []
    current: list[str] = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = _cosine_similarity(embeddings[i - 1], embeddings[i])

        current_joined = " ".join(current)
        would_exceed = len(current_joined) + len(sentences[i]) > MAX_CHUNK_SIZE

        if sim < CHUNK_THRESHOLD or would_exceed:
            # Flush current chunk
            joined = " ".join(current).strip()
            if len(joined) >= MIN_CHUNK_SIZE:
                chunks.append(joined)
            current = [sentences[i]]
        else:
            current.append(sentences[i])

    # Flush last group
    if current:
        joined = " ".join(current).strip()
        if len(joined) >= MIN_CHUNK_SIZE:
            chunks.append(joined)

    return chunks if chunks else [text[:MAX_CHUNK_SIZE]]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _split_into_sentences(text: str) -> list[str]:
    """Naïve but fast sentence splitter using regex, preserving labels."""
    # Split on sentence-ending punctuation followed by whitespace,
    # but avoid splitting after words like 'Deadline:' or 'Date:'
    # and lookahead for lowercase letters which indicates mid-sentence.
    sentences = re.split(r"(?<=[.!?])\s+(?![a-z])", text.strip())
    return [s for s in sentences if s.strip()]


def _embed_sentences(sentences: Sequence[str]) -> list[list[float]] | None:
    """
    Embed sentences using a local SentenceTransformer model.
    Returns None if the model is unavailable (so caller can fall back).
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = _get_st_model()
        vecs = model.encode(list(sentences), show_progress_bar=False)
        return vecs.tolist()
    except Exception as exc:
        logger.warning("SentenceTransformer unavailable for chunking: %s", exc)
        return None


_st_model_cache: object | None = None


def _get_st_model():
    global _st_model_cache
    if _st_model_cache is None:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2 is tiny (~80 MB) and very fast on CPU
        _st_model_cache = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model_cache


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 1.0
    return float(np.dot(va, vb) / denom)


def _char_split(text: str) -> list[str]:
    """Simple character-length splitter as an emergency fallback."""
    from backend.config import MAX_CHUNK_SIZE, MIN_CHUNK_SIZE
    chunks = []
    start = 0
    while start < len(text):
        end = start + MAX_CHUNK_SIZE
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK_SIZE:
            chunks.append(chunk)
        start = end
    return chunks or [text]


def _truncate(text: str) -> str:
    from backend.config import MAX_CHUNK_SIZE
    return text[:MAX_CHUNK_SIZE]
