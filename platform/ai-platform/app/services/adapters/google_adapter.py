"""Google Gemini adapter using the public Generative Language REST API."""

from __future__ import annotations

import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult


class GoogleAdapter(BaseAdapter):
    def __init__(self, api_key: str | None, base_url: str | None, extra_config: dict):
        super().__init__(api_key, base_url, extra_config)
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult:
        if not self.api_key:
            raise RuntimeError("Google/Gemini provider has no API key configured")
        url = f"{self.base_url}/models/{model_name}:generateContent"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Google Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(str(part.get("text", "")) for part in parts)
        usage = data.get("usageMetadata") or {}
        tokens = int(usage.get("totalTokenCount") or 0)
        return InferenceResult(text=text, tokens_used=tokens, raw=data)

    async def health_check(self, timeout: int = 5) -> bool:
        if not self.api_key:
            return False
        # Use the model list endpoint so provider health does not require a
        # billable generation request.
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{self.base_url}/models", params={"key": self.api_key})
            return response.is_success
