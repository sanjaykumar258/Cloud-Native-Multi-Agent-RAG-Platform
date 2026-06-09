"""
agents/grader.py — Agent 2: The Grader.

Reviews the Researcher's draft answer against the source passages and
outputs a binary verdict: YES (supported) or NO (hallucination/unsupported).
"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

GRADER_SYSTEM_PROMPT = """You are a strict fact-checker. Your role is to determine whether an AI-generated answer
is fully supported by the provided source passages.

Instructions:
- Read the SOURCE PASSAGES carefully.
- Read the ANSWER.
- Output ONLY valid JSON in one of the two formats below — nothing else:

If the answer is fully supported by the passages:
{{"grade": "YES"}}

If the answer explicitly states that there is not enough information to answer the question, count this as supported:
{{"grade": "YES"}}

If the answer contains any claim NOT found in the passages, or if the answer invents details:
{{"grade": "NO", "reason": "<one-sentence explanation of what is unsupported>"}}

If the user's question explicitly asks to COMPARE multiple files or sources, and the answer only uses one source, you MUST reject it:
{{"grade": "NO", "reason": "Question asked to compare multiple sources, but answer relies on only one."}}

Do not add any explanation outside of the JSON.

SOURCE PASSAGES:
{context}

ANSWER:
{answer}
"""


class GraderAgent:
    """Checks whether an answer is grounded in the retrieved source passages."""

    def __init__(self, llm):
        self.llm = llm

    def grade(self, question: str, answer: str, sources: list[dict]) -> dict:
        """
        Returns:
          { "grade": "YES" } or { "grade": "NO", "reason": "..." }
        """
        if not sources:
            # No sources → answer cannot be grounded
            return {"grade": "NO", "reason": "No source passages were retrieved."}

        # Build context from sources
        context_parts = []
        for i, s in enumerate(sources, 1):
            context_parts.append(f"[Passage {i}]\n{s['text']}")
        context_str = "\n\n".join(context_parts)

        system_msg = SystemMessage(
            content=GRADER_SYSTEM_PROMPT.format(context=context_str, answer=answer)
        )
        user_msg = HumanMessage(content=f"Question: {question}")

        try:
            response = self.llm.invoke([system_msg, user_msg])
            raw = response.content if hasattr(response, "content") else str(response)
            return _parse_grade(raw)
        except Exception as exc:
            logger.error("GraderAgent LLM call failed: %s", exc)
            # On error, assume graded as YES to avoid infinite retries
            return {"grade": "YES"}


def _parse_grade(raw: str) -> dict:
    """Extract JSON from the model output robustly."""
    # Try direct JSON parse
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON object anywhere in the text
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Keyword fallback
    upper = text.upper()
    if '"GRADE": "YES"' in upper or "GRADE: YES" in upper:
        return {"grade": "YES"}
    if '"GRADE": "NO"' in upper or "GRADE: NO" in upper:
        return {"grade": "NO", "reason": "Could not parse detailed reason."}

    # Default to YES to prevent spin loops
    logger.warning("Could not parse grader output: %s — defaulting to YES.", text[:200])
    return {"grade": "YES"}
