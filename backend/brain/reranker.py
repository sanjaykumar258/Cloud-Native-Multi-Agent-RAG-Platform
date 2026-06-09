"""
brain/reranker.py — Contextual Compression via FlashRank.

Takes a list of retrieved chunk dicts and a query, and re-ranks them using
a fast, local cross-encoder. Returns the top_k most relevant chunks.
"""

import logging
from typing import Any

from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)

_ranker = None


def get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        # Mini-LM based model is tiny (~40MB) and very fast on CPU
        _ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2")
    return _ranker


def rerank(query: str, chunks: list[dict[str, Any]], top_k: int = 3) -> list[dict[str, Any]]:
    """
    Rerank chunks using FlashRank.
    Returns the top_k chunks, preserving the exact original dict structure,
    but with an added 'rerank_score' field in the metadata or dict.
    """
    if not chunks:
        return []

    if len(chunks) <= top_k:
        return chunks

    try:
        ranker = get_ranker()
        
        # FlashRank expects a list of dicts with 'id' and 'text'
        passages = [
            {
                "id": i,
                "text": str(c.get("text", "")),
                # meta is optional but we can pass it
                "meta": c.get("metadata", {})
            }
            for i, c in enumerate(chunks)
        ]
        
        request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(request)
        
        # Results is a list of dicts, sorted by score descending
        # Example result format: [{'id': 0, 'text': '...', 'meta': {...}, 'score': 0.99}, ...]
        
        reranked_chunks = []
        for res in results[:top_k]:
            original_idx = res["id"]
            original_chunk = chunks[original_idx].copy()
            # Add score to metadata
            if "metadata" not in original_chunk:
                original_chunk["metadata"] = {}
            original_chunk["metadata"]["rerank_score"] = res["score"]
            reranked_chunks.append(original_chunk)
            
        logger.info("Reranked %d chunks down to top %d.", len(chunks), len(reranked_chunks))
        return reranked_chunks
        
    except Exception as exc:
        logger.error("FlashRank reranking failed: %s. Returning original top %d chunks.", exc, top_k)
        return chunks[:top_k]
