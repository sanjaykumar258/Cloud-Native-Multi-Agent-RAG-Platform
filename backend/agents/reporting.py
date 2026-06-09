"""
agents/reporting.py — Agent 4: The Reporter.

Crawls the workspace, analyzes document metadata, and generates structured
Markdown reports with summary insights and data validity scores.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

REPORTING_SYSTEM_PROMPT = """You are an expert Workspace Analyst. 
Your goal is to generate a comprehensive, professional Markdown report based on the provided workspace metadata.

The metadata includes a list of files, their sizes, and extensions.

Guidelines:
1. Start with a clear # Header.
2. Use ## Subheaders for sections like "File Distribution", "Content Summary", and "Insights".
3. Provide a "Data Validity Score" (0-100) based on the presence of expected files (e.g., .env, requirements.txt, documentation).
4. Use bullet points for lists.
5. Summarize the overall purpose of the workspace based on the file names and structure.

WORKSPACE METADATA:
{metadata}
"""

class ReportingAgent:
    """Crawls local folder and generates a structured Markdown report."""

    def __init__(self, llm, root_dir: str = "."):
        self.llm = llm
        self.root_dir = Path(root_dir).resolve()

    def run(self, question: str) -> dict[str, Any]:
        """
        Crawls the directory, analyzes via LLM, and returns the report content.
        """
        logger.info("ReportingAgent: Crawling %s", self.root_dir)
        
        files_info = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip hidden directories like .git
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    stats = file_path.stat()
                    files_info.append({
                        "path": str(file_path.relative_to(self.root_dir)),
                        "size": stats.st_size,
                        "extension": file_path.suffix
                    })
                except Exception as e:
                    logger.warning("Could not stat file %s: %s", file_path, e)

        metadata_str = "\n".join([str(f) for f in files_info[:100]]) # Limit to first 100 files for context
        
        system_msg = SystemMessage(content=REPORTING_SYSTEM_PROMPT.format(metadata=metadata_str))
        user_msg = HumanMessage(content=f"Generate a report for this workspace. User request details: {question}")

        try:
            response = self.llm.invoke([system_msg, user_msg])
            report_content = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("ReportingAgent LLM call failed: %s", exc)
            report_content = f"# Workspace Report\n\nError generating report: {exc}"

        return {
            "report_content": report_content,
            "files_crawled": len(files_info),
            "root": str(self.root_dir)
        }
