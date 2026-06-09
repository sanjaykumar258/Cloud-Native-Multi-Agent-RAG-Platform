"""
agents/query_expander.py — Multi-Query Expansion.

Generates alternative phrasing and expanded keywords for the user's query
to improve vector search recall.
"""

import json
import logging
import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_provider import get_llm

logger = logging.getLogger(__name__)

EXPANDER_SYSTEM_PROMPT = """You are an expert AI search engine. Your task is to generate 3 alternative versions of the user's question to improve vector search recall.
Think about synonyms, broader categorizations, and specific keywords that might appear in related documents.

Return ONLY a valid JSON array of strings containing the 3 queries. Do not include markdown formatting or the original query.
Example output:
[
  "What is the total project budget?",
  "Financial plan and cost breakdown 2024",
  "Budget allocations and expenditures"
]
"""


def generate_queries(original_query: str) -> List[str]:
    """
    Generate 3 alternative queries for the given original query.
    Returns a list of exactly 3 strings (falling back to the original if it fails).
    """
    try:
        # Temperature slightly above 0 for some variety
        llm = get_llm(temperature=0.2)
        
        system_msg = SystemMessage(content=EXPANDER_SYSTEM_PROMPT)
        user_msg = HumanMessage(content=f"Original question: {original_query}")
        
        response = llm.invoke([system_msg, user_msg])
        raw = response.content if hasattr(response, "content") else str(response)
        
        queries = _parse_json_array(raw)
        
        # Ensure we have some variants
        if not queries:
            return [original_query]
            
        logger.info(f"Expanded queries: {queries}")
        return queries[:3]
        
    except Exception as exc:
        logger.warning(f"Query expansion failed: {exc}. Using original query only.")
        return [original_query]


def _parse_json_array(raw: str) -> List[str]:
    """Extract a JSON array of strings from the LLM output."""
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    
    # Try finding the array brackets if there's other text
    match = re.search(r"\[([\s\S]*?)\]", raw)
    if match:
        raw_array = match.group(0)
        try:
            data = json.loads(raw_array)
            if isinstance(data, list) and all(isinstance(x, str) for x in data):
                return data
        except json.JSONDecodeError:
            pass
            
    # Absolute fallback
    return []
