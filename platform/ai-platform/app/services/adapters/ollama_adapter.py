import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult


class OllamaAdapter(BaseAdapter):
    async def generate(self, model_name: str, prompt: str, timeout: int) -> InferenceResult:
        base = self.base_url or "http://localhost:11434"
        payload = {"model": model_name, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
        return InferenceResult(
            text=data.get("response", ""),
            tokens_used=data.get("eval_count", 0),
            raw=data,
        )

    async def health_check(self, timeout: int = 5) -> bool:
        base = self.base_url or "http://localhost:11434"
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{base}/api/tags")
        return r.status_code == 200
