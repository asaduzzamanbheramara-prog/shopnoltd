"""
Core conversation engine: sends messages to the selected model, executes any
tool calls it makes, feeds the results back, and loops until the model
produces a final text answer (or the iteration cap is hit, as a safety valve
against runaway tool loops).
"""

import json

from app.ai.client import DEFAULT_MODEL, call_model
from app.ai.prompts import get_system_prompt
from app.ai.tools import execute_tool, get_tool_definitions

MAX_TOOL_ITERATIONS = 5
MAX_TOKENS = 1024


def run_conversation(
    messages: list[dict], mode: str = "default", model: str = DEFAULT_MODEL
) -> tuple[str, list[dict]]:
    """
    messages: [{"role": "user"|"assistant", "content": "..."}]
    model: friendly name from client.MODEL_REGISTRY, e.g. "claude-sonnet", "gpt-4o"
    Returns (final_text, full_message_log) — the log includes any
    intermediate tool_use / tool_result turns, useful for debugging or
    storing a full audit trail later.
    """
    system_prompt = get_system_prompt(mode)
    working_messages = [{"role": "system", "content": system_prompt}] + list(messages)

    for _ in range(MAX_TOOL_ITERATIONS):
        response = call_model(
            model,
            max_tokens=MAX_TOKENS,
            tools=get_tool_definitions(),
            messages=working_messages,
        )

        message = response.choices[0].message
        working_messages.append(message.model_dump())

        if not getattr(message, "tool_calls", None):
            return message.content or "", working_messages

        tool_results = []
        for call in message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = execute_tool(call.function.name, args)
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                }
            )
        working_messages.extend(tool_results)

    return (
        "I wasn't able to finish that within the allowed number of tool-use steps.",
        working_messages,
    )
