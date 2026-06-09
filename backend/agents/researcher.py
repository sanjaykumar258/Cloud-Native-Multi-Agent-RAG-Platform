"""
agents/researcher.py — Agent 1: The Researcher.

Retrieves relevant context chunks from ChromaDB and drafts an answer
with inline citations (source, page number, heading).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

RESEARCHER_SYSTEM_PROMPT = """You are a precise research assistant. Your job is to answer the user's question using ONLY the provided source passages.

Rules for Accuracy & Conflict Resolution:
1. PRIORITIZE OFFICIAL SOURCES: Trust official reports, plans, and summaries (e.g., Project_Alpha.pdf, Financial_Summary.pdf) over informal notes or logs (e.g., Meeting_Notes.pdf, Chat_Logs.txt) if they provide different dates, values, or deadlines.
2. DETECT CONFLICTS: If different sources provide conflicting information, you MUST mention the discrepancy in your answer (e.g., "The official project report states March 10, though meeting notes from February mention an update to March 25").
3. NO HALLUCINATION: If required data is missing, respond exactly: "Required numeric data not found in documents."
4. CITATIONS: For every fact, cite the source: [Source: <filename>, Page <N>]
5. CONCISE: Keep your answer extremely short (1-2 sentences).
6. NO introductions, conclusions, or inventiveness.

SOURCE PASSAGES:
{context}
"""


class ResearcherAgent:
    """Retrieves chunks from the vector store and drafts a grounded answer."""

    def __init__(self, vectorstore, llm):
        self.vs = vectorstore
        self.llm = llm

    def run(
        self,
        question: str,
        n_results: int = 10,
        where: dict | None = None,
        stream: bool = False,
    ) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
        """
        Retrieves and generates an answer. If stream=True, returns a generator.
        """
        # Only use the original question for maximum speed
        all_queries = [question]

        # Retrieve
        results = []
        seen_chunks = set()
        for q in all_queries:
            q_results = self.vs.query(q, n_results=n_results, where=where)
            if q_results:
                for res in q_results:
                    text = res.get("text", "")
                    if text not in seen_chunks:
                        seen_chunks.add(text)
                        results.append(res)
        
        # Limit total results passed to the LLM to strictly n_results
        results = results[:n_results]

        if not results:
            msg = "The provided documents do not contain sufficient information to answer this question."
            if stream:
                def _gen():
                    yield {"type": "answer", "content": msg, "sources": []}
                return _gen()
            return {"answer": msg, "sources": [], "n_results": n_results}

        # Build context string
        from backend.llm_provider import get_active_provider
        limit = 800 if get_active_provider() == "ollama" else 2500



        
        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            label = _format_citation(meta)
            # Truncate text for local LLM speed
            snippet = r['text'][:limit]
            context_parts.append(f"[Passage {i}] {label}\n{snippet}")

        context_str = "\n\n".join(context_parts)
        system_msg = SystemMessage(content=RESEARCHER_SYSTEM_PROMPT.format(context=context_str))
        user_msg = HumanMessage(content=question)

        if stream:
            return self._run_stream(system_msg, user_msg, results)

        try:
            response = self.llm.invoke([system_msg, user_msg])
            answer = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("ResearcherAgent LLM call failed: %s", exc)
            answer = f"[LLM Error] {exc}"

        return {
            "answer": answer,
            "sources": results,
            "n_results": n_results,
        }

    def _run_stream(self, system_msg, user_msg, sources):
        """Yields chunks as they come from the LLM."""
        try:
            # First yield sources so UI can show them
            yield {"type": "sources", "content": sources}
            
            full_answer = ""
            for chunk in self.llm.stream([system_msg, user_msg]):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    full_answer += token
                    yield {"type": "token", "content": token}
            
            # Final yield for the state machine
            yield {"type": "final_answer", "content": full_answer}
        except Exception as exc:
            logger.error("ResearcherAgent streaming failed: %s", exc)
            yield {"type": "token", "content": f"\n\n[Streaming Error] {exc}"}



def _format_citation(meta: dict) -> str:
    source = meta.get("source", "Unknown")
    page = meta.get("page_number", "")
    heading = meta.get("heading", "")

    parts = [f"File: {source}"]
    if page:
        parts.append(f"Page {page}")
    if heading:
        parts.append(f"Section: \"{heading}\"")
    return " | ".join(parts)
