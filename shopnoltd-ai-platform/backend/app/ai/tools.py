"""
Tool-calling framework.

Register a tool with @tool(...), and it becomes available to Claude
automatically via get_tool_definitions(). Milestone 4-6 (GitHub, Kubernetes,
Docker, Cloudflare) will add tools here — each one should be reviewed
carefully for safety before being registered, since Claude will be able to
call it autonomously during a conversation.

This milestone ships one deliberately harmless example tool
(get_current_time) to prove the framework works end-to-end.
"""
from datetime import datetime, timezone
from typing import Callable

TOOL_REGISTRY: dict[str, dict] = {}


def tool(name: str, description: str, input_schema: dict):
    """Decorator that registers a function as a Claude-callable tool."""

    def decorator(func: Callable):
        TOOL_REGISTRY[name] = {
            "func": func,
            "description": description,
            "input_schema": input_schema,
        }
        return func

    return decorator


@tool(
    name="get_current_time",
    description=(
        "Get the current date and time in UTC. Use this whenever the user "
        "asks what time or date it is."
    ),
    input_schema={"type": "object", "properties": {}, "required": []},
)
def get_current_time(**_kwargs) -> dict:
    return {"utc_time": datetime.now(timezone.utc).isoformat()}


def get_tool_definitions() -> list[dict]:
    """Returns tool schemas in the shape the Anthropic API expects."""
    return [
        {
            "name": name,
            "description": meta["description"],
            "input_schema": meta["input_schema"],
        }
        for name, meta in TOOL_REGISTRY.items()
    ]


def execute_tool(name: str, tool_input: dict) -> dict:
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    try:
        return TOOL_REGISTRY[name]["func"](**tool_input)
    except Exception as exc:  # noqa: BLE001 — surfaced back to the model, not raised
        return {"error": f"Tool '{name}' failed: {exc}"}
