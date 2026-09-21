import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIAdapter(BaseAdapter):
    async def generate(
        self,
        model_name: str,
        prompt: str,
        timeout: int,
        attachments: list[dict] | None = None,
    ) -> InferenceResult:
        api_key = self.require_api_key("OpenAI-compatible")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {"Authorization": f"Bearer {api_key}"}

        content = [{"type": "text", "text": prompt}]
        for attachment in attachments or []:
            mime_type = str(attachment.get("mime_type") or "")
            data = attachment.get("data")
            if not data:
                continue
            if not mime_type.startswith("image/"):
                raise RuntimeError(
                    f"OpenAI-compatible adapter does not accept attachment type '{mime_type}'"
                )
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{data}"
                },
            })

        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": content}],
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return InferenceResult(text=text, tokens_used=tokens, raw=data)


    async def list_models(self, timeout: int = 10) -> list[dict] | None:
        api_key = self.require_api_key("OpenAI-compatible")
        base = self.base_url or DEFAULT_BASE_URL
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base}/models", headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            payload = response.json()
        return [
            {
                "id": item.get("id"),
                "display_name": item.get("name") or item.get("id"),
                "context_window": item.get("context_length"),
                "pricing": item.get("pricing"),
                "capabilities": item.get("capabilities") or {},
            }
            for item in payload.get("data", [])
            if item.get("id")
        ]

    async def health_check(self, timeout: int = 5) -> bool:
        api_key = self.require_api_key("OpenAI-compatible")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{base}/models", headers=headers)
        return r.status_code == 200
