import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(BaseAdapter):
    async def generate(
        self,
        model_name: str,
        prompt: str,
        timeout: int,
        attachments: list[dict] | None = None,
    ) -> InferenceResult:
        api_key = self.require_api_key("Anthropic")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        content = [{"type": "text", "text": prompt}]
        for attachment in attachments or []:
            mime_type = str(attachment.get("mime_type") or "")
            data = attachment.get("data")
            if not data:
                continue
            if not mime_type.startswith("image/"):
                raise RuntimeError(
                    f"Anthropic adapter does not accept attachment type '{mime_type}'"
                )
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": data,
                },
            })

        payload = {
            "model": model_name,
            "max_tokens": self.extra_config.get("max_tokens", 1024),
            "messages": [{"role": "user", "content": content}],
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


    async def list_models(self, timeout: int = 10) -> list[dict] | None:
        api_key = self.require_api_key("Anthropic")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION}
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base}/models", headers=headers)
            response.raise_for_status()
            payload = response.json()
        return [
            {"id": item.get("id"), "display_name": item.get("display_name") or item.get("id")}
            for item in payload.get("data", [])
            if item.get("id")
        ]

    async def health_check(self, timeout: int = 5) -> bool:
        # Anthropic has no universally cheap model-list ping; use the configured
        # health-check model for a minimal request. The request is intentionally
        # one token and is only used by the admin connectivity test.
        api_key = self.require_api_key("Anthropic")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {
            "x-api-key": api_key,
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
