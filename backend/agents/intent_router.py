"""
agents/intent_router.py — Classifies user intent: "code" vs "chat".

Classification strategy (in order):
  1. Strong keyword match  → immediate decision (< 1ms)
  2. LLM confirms         → for borderline cases (~50ms)
  3. Fallback to "chat"   → on any error

"code" intent is triggered when the user wants computation:
  averages, totals, counts, max/min, comparisons, statistics,
  rankings, distributions across many documents.

"chat" intent covers everything else (summaries, explanations,
definitions, factual look-ups, etc.)
"""

from __future__ import annotations

import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# User's strict keywords - only trigger math engine on very explicit terms
_CALC_KEYWORDS = [
    "percentage", "percent", "ratio", "total", "sum", "average", "mean", 
    "median", "difference", "compute", "calculate", "math", "how many",
    "what is the total", "sum of", "count of", "aggregation", "statistics"
]

_COMPARE_KEYWORDS = [
    "highest", "lowest", "largest", "maximum", "minimum", "max", "min"
]

_CALC_RE = re.compile(rf"\b({'|'.join(_CALC_KEYWORDS)})\b", re.IGNORECASE)
_COMPARE_RE = re.compile(rf"\b({'|'.join(_COMPARE_KEYWORDS)})\b", re.IGNORECASE)
_REPORT_RE = re.compile(r"\b(report|crawl|workspace summary|generate report)\b", re.IGNORECASE)
_VISION_RE = re.compile(r"\b(image|picture|photo|describe|see|look at|view)\b", re.IGNORECASE)
_DB_RE = re.compile(r"\b(database|sql|inspect chunks|schema|chromadb|inspect db|show db)\b", re.IGNORECASE)
_FS_RE = re.compile(r"\b(folder|directory|list files|read file|workspace|filesystem)\b", re.IGNORECASE)



# ── LLM prompt for borderline cases ──────────────────────────────────────────
_ROUTER_SYSTEM = """\
You classify user questions into exactly one of two categories:
  "code"  — requires computation, aggregation, or statistical analysis over data
  "chat"  — answered by reading and summarising text (no maths needed)

Reply with ONLY the word: code   or   chat
No explanation, no punctuation.
"""


class IntentRouter:
    """
    Routes a question to either the Python execution engine or normal RAG chat.

    Usage:
        router = IntentRouter(llm=llm)
        intent = router.route(question)   # returns "code" or "chat"
    """

    def __init__(self, llm=None):
        self.llm = llm

    def route(self, question: str) -> str:
        """Return "code", "report", "db", "file", or "chat"."""
        # 1. Fast keyword check
        if _REPORT_RE.search(question):
            return "report"
            
        if _CALC_RE.search(question):
            return "code"

        if _DB_RE.search(question):
            return "db"
        
        if _FS_RE.search(question):
            return "file"

        # 2. LLM fallback for borderline cases
        if self.llm:
            try:
                msg = [
                    SystemMessage(content=_ROUTER_SYSTEM),
                    HumanMessage(content=question)
                ]
                res = self.llm.invoke(msg).content.strip().lower()
                if "code" in res:
                    return "code"
            except Exception as e:
                logger.warning("LLM Router failed: %s", e)

        # 3. Default to chat (highest/lowest go here)
        return "chat"


