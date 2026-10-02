import httpx

from app.core.config import settings


class MediaServiceError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code


class MediaServiceClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.media_service_url).rstrip("/")
        self.token = token or settings.media_service_token

    def _headers(self, owner: str | None = None) -> dict[str, str]:
        if not self.token:
            raise MediaServiceError(503, "media service authentication is not configured")
        headers = {"Authorization": f"Bearer {self.token}"}
        if owner:
            headers["X-Owner"] = owner[:64]
        return headers

    async def render_design(
        self,
        source: str,
        kind: str = "svg",
        fmt: str = "png",
        width: int | None = None,
        height: int | None = None,
        background: str = "#ffffff",
        name: str = "design",
        owner: str | None = None,
    ) -> tuple[bytes, str, str]:
        payload = {
            "source": source,
            "kind": kind,
            "format": fmt,
            "background": background,
            "name": name,
        }
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height

        try:
            async with httpx.AsyncClient(timeout=settings.media_service_timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/v1/design/render",
                    headers=self._headers(owner),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise MediaServiceError(502, f"media service request failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text[:200])
            except Exception:
                detail = response.text[:200]
            raise MediaServiceError(response.status_code, str(detail))

        return (
            response.content,
            response.headers.get("content-type", "application/octet-stream"),
            response.headers.get("content-disposition", 'attachment; filename="design"'),
        )
