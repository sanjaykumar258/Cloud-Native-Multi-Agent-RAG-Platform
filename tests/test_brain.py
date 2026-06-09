"""
tests/test_grader.py — Unit tests for the GraderAgent.

Run:  pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock


class FakeLLM:
    """Mock LLM that returns a preset response."""
    def __init__(self, answer: str):
        self._answer = answer

    def invoke(self, messages, **kwargs):
        r = MagicMock()
        r.content = self._answer
        return r


def _make_sources():
    return [
        {"text": "The Eiffel Tower is located in Paris, France.", "metadata": {"source": "facts.pdf"}},
    ]


class TestGraderAgent:
    def test_grades_yes_for_supported_answer(self):
        from backend.agents.grader import GraderAgent
        llm = FakeLLM('{"grade": "YES"}')
        grader = GraderAgent(llm=llm)
        result = grader.grade(
            question="Where is the Eiffel Tower?",
            answer="The Eiffel Tower is in Paris.",
            sources=_make_sources(),
        )
        assert result["grade"] == "YES"

    def test_grades_no_for_unsupported_answer(self):
        from backend.agents.grader import GraderAgent
        llm = FakeLLM('{"grade": "NO", "reason": "Answer mentions Berlin which is not in passages."}')
        grader = GraderAgent(llm=llm)
        result = grader.grade(
            question="Where is the Eiffel Tower?",
            answer="The Eiffel Tower is in Berlin.",
            sources=_make_sources(),
        )
        assert result["grade"] == "NO"
        assert "reason" in result

    def test_grades_no_when_no_sources(self):
        from backend.agents.grader import GraderAgent
        llm = FakeLLM('{"grade": "YES"}')
        grader = GraderAgent(llm=llm)
        result = grader.grade(
            question="Something?",
            answer="Some answer.",
            sources=[],
        )
        assert result["grade"] == "NO"

    def test_parses_json_inside_markdown_block(self):
        from backend.agents.grader import _parse_grade
        raw = '```json\n{"grade": "YES"}\n```'
        result = _parse_grade(raw)
        assert result["grade"] == "YES"

    def test_keyword_fallback_yes(self):
        from backend.agents.grader import _parse_grade
        result = _parse_grade('The answer looks good. GRADE: YES.')
        assert result["grade"] == "YES"


class TestSemanticChunker:
    def test_table_elements_not_split(self):
        from backend.brain.chunker import chunk_elements
        elements = [{
            "text": "Col1 | Col2\nA | B\nC | D",
            "metadata": {
                "source": "test.pdf",
                "source_path": "/tmp/test.pdf",
                "page_number": 1,
                "element_type": "Table",
                "heading": None,
            },
        }]
        chunks = chunk_elements(elements)
        # Tables should remain as exactly 1 chunk
        assert len(chunks) == 1
        assert chunks[0]["metadata"]["element_type"] == "Table"

    def test_char_split_fallback(self):
        from backend.brain.chunker import _char_split
        long_text = "A" * 5000
        chunks = _char_split(long_text)
        from backend.config import MAX_CHUNK_SIZE
        assert all(len(c) <= MAX_CHUNK_SIZE for c in chunks)
        assert len(chunks) > 1


class TestVectorStoreMetadata:
    def test_sanitize_none_becomes_empty_string(self):
        from backend.brain.vectorstore import _sanitize_metadata
        meta = {"source": "file.txt", "heading": None, "page_number": 3}
        clean = _sanitize_metadata(meta)
        assert clean["heading"] == ""
        assert clean["source"] == "file.txt"
        assert clean["page_number"] == 3
