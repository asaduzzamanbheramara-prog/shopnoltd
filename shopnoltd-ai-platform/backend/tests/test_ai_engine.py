from datetime import datetime

from app.ai.tools import execute_tool, get_tool_definitions


def test_get_tool_definitions_includes_example_tool():
    definitions = get_tool_definitions()
    names = [d["name"] for d in definitions]
    assert "get_current_time" in names


def test_execute_known_tool_returns_valid_timestamp():
    result = execute_tool("get_current_time", {})
    assert "utc_time" in result
    # Should parse without raising — confirms it's a real ISO timestamp
    datetime.fromisoformat(result["utc_time"])


def test_execute_unknown_tool_returns_error_not_exception():
    result = execute_tool("does_not_exist", {})
    assert "error" in result
