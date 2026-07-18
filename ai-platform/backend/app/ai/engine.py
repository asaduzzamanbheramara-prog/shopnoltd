"""
Core conversation engine: sends messages to Claude, executes any tool calls
it makes, feeds the results back, and loops until Claude produces a final
text answer (or the iteration cap is hit, as a safety valve against runaway
tool loops).
"""

from app.ai.client import MODEL, client
from app.ai.prompts import get_system_prompt
from app.ai.tools import execute_tool, get_tool_definitions

MAX_TOOL_ITERATIONS = 5
MAX_TOKENS = 1024


def run_conversation(messages: list[dict], mode: str = "default") -> tuple[str, list[dict]]:
    """
    messages: [{"role": "user"|"assistant", "content": "..."}]
    Returns (final_text, full_message_log) — the log includes any
    intermediate tool_use / tool_result turns, useful for debugging or
    storing a full audit trail later.
    """
    system_prompt = get_system_prompt(mode)
    working_messages = list(messages)

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=get_tool_definitions(),
            messages=working_messages,
        )

        assistant_blocks = [block.model_dump() for block in response.content]
        working_messages.append({"role": "assistant", "content": assistant_blocks})

        if response.stop_reason != "tool_use":
            final_text = "".join(block.text for block in response.content if block.type == "text")
            return final_text, working_messages

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
        working_messages.append({"role": "user", "content": tool_results})

    return (
        "I wasn't able to finish that within the allowed number of tool-use steps.",
        working_messages,
    )
