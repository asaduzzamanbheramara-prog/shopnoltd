import httpx

from app.services.adapters.base import BaseAdapter, InferenceResult


class OllamaAdapter(BaseAdapter):
    async def generate(
        self,
        model_name: str,
        prompt: str,
        timeout: int,
        attachments: list[dict] | None = None,
    ) -> InferenceResult:
        base = self.base_url or "http://ollama.shopno-apps.svc.cluster.local:11434"

        images = []
        for attachment in attachments or []:
            mime_type = str(attachment.get("mime_type") or "")
            data = attachment.get("data")
            if not data:
                continue
            if not mime_type.startswith("image/"):
                raise RuntimeError(
                    f"Ollama adapter does not accept attachment type '{mime_type}'"
                )
            images.append(data)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
        return InferenceResult(
            text=data.get("response", ""),
            tokens_used=data.get("eval_count", 0),
            raw=data,
        )


    async def list_models(self, timeout: int = 10) -> list[dict] | None:
        base = self.base_url or "http://ollama.shopno-apps.svc.cluster.local:11434"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base}/api/tags")
            response.raise_for_status()
            payload = response.json()
        return [
            {
                "id": item.get("name") or item.get("model"),
                "display_name": item.get("name") or item.get("model"),
                "capabilities": {
                    "chat": True,
                    "local": True,
                },
            }
            for item in payload.get("models", [])
            if item.get("name") or item.get("model")
        ]

    async def health_check(self, timeout: int = 5) -> bool:
        base = self.base_url or "http://ollama.shopno-apps.svc.cluster.local:11434"
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{base}/api/tags")
        return r.status_code == 200
