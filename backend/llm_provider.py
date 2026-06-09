"""
llm_provider.py — Returns an LLM instance.
Primary: Ollama (local)  |  Fallback: Groq (free-tier cloud)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_llm(
    prefer_groq: bool = True,
    temperature: float = 0.0,
):
    """
    Return a LangChain-compatible chat model.
    """
    from backend.config import OLLAMA_BASE_URL
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama-3.1-8b-instant")

    if prefer_groq and GROQ_API_KEY:
        return _make_groq_llm(GROQ_API_KEY, GROQ_MODEL, temperature)

    # Try Ollama first
    try:
        _probe_ollama(OLLAMA_BASE_URL)
        llm = _make_ollama_llm(OLLAMA_BASE_URL, OLLAMA_MODEL, temperature)
        logger.info("Using Ollama (%s) at %s", OLLAMA_MODEL, OLLAMA_BASE_URL)
        return llm
    except Exception as e:
        logger.warning("Ollama unavailable (%s). Checking Groq fallback…", e)

    # Fallback to Groq
    if GROQ_API_KEY:
        logger.info("Falling back to Groq (%s).", GROQ_MODEL)
        return _make_groq_llm(GROQ_API_KEY, GROQ_MODEL, temperature)

    raise RuntimeError(
        "No LLM is available. Make sure Ollama is running "
        "(ollama serve) or provide a GROQ_API_KEY in .env."
    )


def get_active_provider(prefer_groq: bool = True) -> str:
    """Lightweight check: returns 'ollama' or 'groq' or 'none'."""
    from backend.config import OLLAMA_BASE_URL
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

    if prefer_groq and GROQ_API_KEY:
        return "groq"

    try:
        import requests
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        if r.status_code == 200:
            return "ollama"
    except Exception:
        pass

    if GROQ_API_KEY:
        return "groq"
    return "none"


def _make_ollama_llm(base_url: str, model: str, temperature: float):
    from langchain_ollama import ChatOllama
    # Aggressive speed: Context=2048 guarantees GPU offload on most hardware
    return ChatOllama(
        base_url=base_url,
        model=model,
        temperature=temperature,
        num_ctx=2048,
        num_thread=8,
        repeat_penalty=1.0
    )



def _probe_ollama(base_url: str) -> None:
    """Throw an exception if Ollama is not reachable via a fast HTTP check."""
    import requests
    resp = requests.get(f"{base_url}/api/tags", timeout=2)
    resp.raise_for_status()


def _make_groq_llm(api_key: str, model: str, temperature: float):
    from langchain_groq import ChatGroq
    return ChatGroq(api_key=api_key, model=model, temperature=temperature)
