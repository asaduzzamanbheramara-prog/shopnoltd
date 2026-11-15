"""Secure Manus API v2 task delegation for Shopno Agent."""
from __future__ import annotations
import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any
import httpx

MANUS_API_BASE = os.environ.get("MANUS_API_BASE", "https://api.manus.ai").rstrip("/")
MANUS_POLL_SECONDS = max(2, int(os.environ.get("MANUS_POLL_SECONDS", "4")))
MANUS_TASK_TIMEOUT = max(60, int(os.environ.get("MANUS_TASK_TIMEOUT", "900")))

def manus_api_keys() -> list[str]:
    names = ["MANUS_API_KEY"] + [f"MANUS_API_KEY_{i}" for i in range(1, 6)]
    return [value.strip() for name in names if (value := os.environ.get(name, "").strip())]

def manus_configured() -> bool:
    return bool(manus_api_keys())

async def create_manus_task(goal: str, progress: Callable[[dict[str, Any]], Awaitable[None]]) -> str:
    keys = manus_api_keys()
    if not keys:
        raise RuntimeError("Manus API credentials are not configured.")
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
        created = None
        active_key = None
        for key in keys:
            response = await client.post(
                f"{MANUS_API_BASE}/v2/task.create",
                headers={"content-type": "application/json", "x-manus-api-key": key},
                json={"message": {"content": goal}, "interactive_mode": False, "share_visibility": "private"},
            )
            if response.status_code in {401, 403}:
                continue
            response.raise_for_status()
            payload = response.json()
            if payload.get("ok") is False or not payload.get("task_id"):
                raise RuntimeError("Manus did not return a valid task identifier.")
            created, active_key = payload, key
            break
        if created is None or active_key is None:
            raise RuntimeError("All configured Manus API keys were rejected.")

        task_id = str(created["task_id"])
        task_url = str(created.get("task_url") or "")
        await progress({"type": "text", "text": "Manus task accepted; waiting for the result."})
        deadline = asyncio.get_running_loop().time() + MANUS_TASK_TIMEOUT
        seen: set[str] = set()
        latest_answer = ""
        latest_status = "running"
        headers = {"x-manus-api-key": active_key}

        while asyncio.get_running_loop().time() < deadline:
            response = await client.get(
                f"{MANUS_API_BASE}/v2/task.listMessages", headers=headers,
                params={"task_id": task_id, "order": "asc", "limit": 100},
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("ok") is False:
                raise RuntimeError("Manus could not return task progress.")
            status_value = latest_status
            for event in payload.get("messages", []):
                event_id = str(event.get("id") or "")
                if event_id and event_id in seen:
                    continue
                if event_id:
                    seen.add(event_id)
                kind = event.get("type")
                if kind == "assistant_message":
                    content = (event.get("assistant_message") or {}).get("content")
                    if isinstance(content, str) and content.strip():
                        latest_answer = content.strip()[:12000]
                        await progress({"type": "text", "text": "Manus update: " + latest_answer[:3000]})
                elif kind == "error_message":
                    detail = (event.get("error_message") or {}).get("content") or "Manus task failed."
                    raise RuntimeError(str(detail)[:1000])
                elif kind == "status_update":
                    status_value = str((event.get("status_update") or {}).get("agent_status") or status_value)
            latest_status = status_value
            if status_value == "error":
                raise RuntimeError(latest_answer or "Manus task failed.")
            if status_value == "waiting":
                return f"Manus is waiting for input or confirmation. Open {task_url} to continue."
            if status_value == "stopped":
                detail_response = await client.get(
                    f"{MANUS_API_BASE}/v2/task.detail", headers=headers, params={"task_id": task_id}
                )
                detail_response.raise_for_status()
                if not bool(detail_response.json().get("has_running_background_jobs")):
                    await progress({"type": "text", "text": "Manus task completed: " + task_url})
                    suffix = f"\n\nManus task: {task_url}" if task_url else ""
                    return (latest_answer or "Manus task completed without a text response.") + suffix
            await asyncio.sleep(MANUS_POLL_SECONDS)
        await progress({"type": "text", "text": "Manus is still processing; task remains available at " + task_url})
        return f"Manus task is still running. Check {task_url} for its latest status."
