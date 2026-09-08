import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIAdapter(BaseAdapter):
    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult:
        api_key = self.require_api_key("OpenAI-compatible")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return InferenceResult(text=text, tokens_used=tokens, raw=data)

    async def health_check(self, timeout: int = 5) -> bool:
        api_key = self.require_api_key("OpenAI-compatible")
        base = self.base_url or DEFAULT_BASE_URL
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{base}/models", headers=headers)
        return r.status_code == 200
