"""
tools/chroma_tool.py — Direct ChromaDB inspection and management tool.
"""

from __future__ import annotations

import logging
import pandas as pd
from typing import Any

from backend.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION

logger = logging.getLogger(__name__)

class ChromaTool:
    """
    Allows the AI to inspect the vector store, check source counts, 
    and verify indexed content.
    """

    def __init__(self):
        from backend.brain.vectorstore import VectorStore
        self.vs = VectorStore()

    def list_sources(self) -> str:
        """List all indexed files and their chunk counts."""
        try:
            sources = self.vs.list_sources()
            if not sources:
                return "The vector store is currently empty."
            
            # Get chunk counts per source
            collection = self.vs._collection
            metas = collection.get(include=['metadatas'])['metadatas']
            counts = {}
            for m in metas:
                src = m.get('source', 'unknown')
                counts[src] = counts.get(src, 0) + 1
            
            summary = "### Indexed Documents in ChromaDB\n"
            for src in sources:
                summary += f"- **{src}**: {counts.get(src, 0)} chunks\n"
            
            summary += f"\n**Total Chunks**: {len(metas)}"
            return summary
        except Exception as e:
            return f"Error listing sources: {e}"

    def inspect_chunks(self, source: str, limit: int = 5) -> str:
        """Read the literal text chunks of a specific source."""
        try:
            collection = self.vs._collection
            res = collection.get(where={"source": source}, limit=limit)
            
            if not res['documents']:
                return f"No chunks found for source: {source}"

            output = f"### Top {len(res['documents'])} Chunks for {source}\n"
            for i, doc in enumerate(res['documents']):
                output += f"\n**Chunk {i+1}**:\n```\n{doc}\n```\n"
            return output
        except Exception as e:
            return f"Error inspecting chunks: {e}"

    def status(self) -> str:
        """Return general vector store health."""
        count = self.vs.count()
        return f"ChromaDB Status: Active | Path: {CHROMA_PERSIST_DIR} | Collection: {CHROMA_COLLECTION} | Total Chunks: {count}"

    def run(self, action: str, source: str | None = None) -> str:
        """Unified runner for the graph."""
        if action == "list":
            return self.list_sources()
        elif action == "inspect" and source:
            return self.inspect_chunks(source)
        return self.status()
