import pytest
from backend.brain.utils import format_duration

def test_format_duration_seconds():
    assert format_duration(5.2) == "5.2s"
    assert format_duration(59.9) == "59.9s"

def test_format_duration_minutes():
    assert format_duration(60.0) == "1min"
    assert format_duration(61.0) == "1min 1s"
    assert format_duration(107.3) == "1min 47s"
    assert format_duration(120.0) == "2min"
    assert format_duration(3600.0) == "60min"
