"""
brain/entity_extractor.py — Extract Entities and Relations from Chunks.

Calls the LLM to identify key entities and their relationships within a chunk,
outputting structured data to populate the Knowledge Graph.
"""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from backend.llm_provider import get_llm

logger = logging.getLogger(__name__)

EXTRACTOR_SYSTEM_PROMPT = """You are an expert data architect. Your goal is to extract key entities and their relationships from the provided text snippet.
Focus on identifying Organizations, Projects, People, Technologies, Tools, and Dates.

Return ONLY a valid JSON object matching this schema:
{
  "entities": [
    {"name": "Entity Name", "type": "Project | Person | Organization | Technology | Date | Concept"}
  ],
  "relations": [
    {"from": "Entity Name 1", "to": "Entity Name 2", "label": "relationship description"}
  ]
}

- Keep entity names consistent and concise.
- If no significant entities or relationships are found, return empty lists.
- Do NOT wrap the JSON in markdown code blocks. Output raw JSON only.
"""


def extract_entities(chunk_text: str, source_name: str) -> dict[str, Any]:
    """
    Extract entities and relations from a text chunk.
    Returns: {"entities": [...], "relations": [...]}
    """
    try:
        # We need a stable LLM for extraction, preferentially local
        # If the user has set groq preference or ollama is loaded
        llm = get_llm(temperature=0.0)
        
        system_msg = SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT)
        # Adding source context slightly helps reasoning
        user_msg = HumanMessage(content=f"Context: {source_name}\n\nText: {chunk_text}")
        
        response = llm.invoke([system_msg, user_msg])
        raw = response.content if hasattr(response, "content") else str(response)
        
        return _parse_json_robust(raw)
    except Exception as exc:
        logger.warning(f"Failed to extract entities for chunk from {source_name}: {exc}")
        return {"entities": [], "relations": []}


def _parse_json_robust(raw: str) -> dict[str, Any]:
    """Robust JSON parsing for LLM output."""
    raw = raw.strip()
    # Remove markdown code blocks if present
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # Ensure required keys exist
            if "entities" not in data:
                data["entities"] = []
            if "relations" not in data:
                data["relations"] = []
            return data
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from entity extractor. Content snippet: %s", raw[:100])
    
    return {"entities": [], "relations": []}
