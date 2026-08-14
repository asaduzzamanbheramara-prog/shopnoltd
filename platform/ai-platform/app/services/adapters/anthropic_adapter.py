import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(BaseAdapter):
    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult:
        base = self.base_url or DEFAULT_BASE_URL
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": model_name,
            "max_tokens": self.extra_config.get("max_tokens", 1024),
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/messages", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        tokens = data.get("usage", {}).get("output_tokens", 0) + data.get("usage", {}).get(
            "input_tokens", 0
        )
        return InferenceResult(text=text, tokens_used=tokens, raw=data)

    async def health_check(self, timeout: int = 5) -> bool:
        # Anthropic has no cheap "list models" ping historically usable across all keys;
        # do a minimal 1-token request instead.
        base = self.base_url or DEFAULT_BASE_URL
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self.extra_config.get("health_check_model", "claude-haiku-4-5-20251001"),
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/messages", headers=headers, json=payload)
        return r.status_code == 200
