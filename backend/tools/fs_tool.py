"""
tools/fs_tool.py — File system interaction tool.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class FSTool:
    """
    Allows the AI to explore the local file system within the workspace.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()

    def list_files(self, sub_dir: str = "") -> str:
        """List files in a directory."""
        target = (self.root_dir / sub_dir).resolve()
        if not str(target).startswith(str(self.root_dir)):
            return "Error: Access denied (path traversal blocked)."

        if not target.exists():
            return f"Error: Directory not found: {sub_dir}"

        try:
            items = []
            for item in target.iterdir():
                prefix = "📁" if item.is_dir() else "📄"
                items.append(f"{prefix} {item.name}")
            return "### Files in " + (sub_dir or "root") + ":\n- " + "\n- ".join(items)
        except Exception as e:
            return f"FS Error: {e}"

    def read_file(self, file_path: str) -> str:
        """Read content of a specific file."""
        target = (self.root_dir / file_path).resolve()
        if not str(target).startswith(str(self.root_dir)):
            return "Error: Access denied."

        if not target.is_file():
            return f"Error: {file_path} is not a file."

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            # Truncate if very large
            if len(content) > 5000:
                content = content[:5000] + "\n... [truncated]"
            return f"### Content of {file_path}:\n```\n{content}\n```"
        except Exception as e:
            return f"FS Error: {e}"
