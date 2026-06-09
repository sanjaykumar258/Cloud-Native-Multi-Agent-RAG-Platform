"""
config.py — Cloud-Native Multi-Agent RAG Platform: Central configuration loaded from environment variables / .env file
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root and force override any cached os.environ values
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    # Read manually to absolutely force override because load_dotenv cache can be stubborn in Streamlit
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v
load_dotenv(env_path, override=True)

# ── Ollama (Deprecated / Local Fallback) ──────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama-3.1-8b-instant")
VISION_MODEL: str = os.getenv("VISION_MODEL", "llava:7b")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./database/chroma_db")
CHROMA_COLLECTION: str = "brain_docs_v2"

# ── Groq (Primary Cloud LLM) ──────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")

# ── Agent / RAG settings ──────────────────────────────────────────────────────
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "1")) # 1 retry = 2 attempts total
TOP_K: int = int(os.getenv("TOP_K", "3"))
CHUNK_THRESHOLD: float = float(os.getenv("CHUNK_THRESHOLD", "0.4"))
MAX_CHUNK_SIZE: int = 1500        # increased for multi-line numeric context
MIN_CHUNK_SIZE: int = 50         # discard tiny fragments below this length

# ── Supported file extensions ─────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: list[str] = [".pdf", ".md", ".markdown", ".txt", ".text"]

