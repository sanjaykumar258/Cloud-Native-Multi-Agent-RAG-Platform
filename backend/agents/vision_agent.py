"""
agents/vision_agent.py — Handles multimodal queries (Images + Text) via llava.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class VisionAgent:
    """
    Agent for processing images using the 'llava' model via Ollama.
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        from backend.config import OLLAMA_BASE_URL, VISION_MODEL, GROQ_API_KEY, GROQ_VISION_MODEL
        
        self.api_key = GROQ_API_KEY
        if self.api_key:
            from langchain_groq import ChatGroq
            self.model_name = GROQ_VISION_MODEL
            self.llm = ChatGroq(
                api_key=self.api_key,
                model=self.model_name,
                temperature=0,
            )
            logger.info("VisionAgent: Using Cloud Groq (%s)", self.model_name)
        else:
            self.model_name = model or VISION_MODEL
            self.base_url = base_url or OLLAMA_BASE_URL
            self.llm = ChatOllama(
                base_url=self.base_url,
                model=self.model_name,
                temperature=0,
            )
            logger.info("VisionAgent: Using Local Ollama (%s)", self.model_name)

    def describe_image(self, image_path: str | Path, prompt: str = "What is in this image?") -> str:
        """
        Encode image to base64 and get description from LLaVA.
        """
        path = Path(image_path)
        if not path.exists():
            return f"Error: Image not found at {image_path}"

        try:
            # Check if model is pulled (approximate check via base_url)
            # For simplicity, we'll just catch the exception from invoke
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image_data}",
                    },
                ]
            )

            response = self.llm.invoke([message])
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            if "pull" in str(e).lower() or "404" in str(e):
                logger.warning("Vision model %s not found or pulling. Returning placeholder.", self.model_name)
                return f"[Vision Model {self.model_name} is currently initializing. Description will be available once the model pull is complete.]"
            logger.error("Vision processing failed: %s", e)
            return f"Vision error: {e}"

    def run(self, question: str, image_path: str | Path) -> dict[str, Any]:
        """
        Public API for the graph to call.
        """
        answer = self.describe_image(image_path, prompt=question)
        return {
            "answer": answer,
            "sources": [{"metadata": {"source": Path(image_path).name, "type": "image"}}]
        }
