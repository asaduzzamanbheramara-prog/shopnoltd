from typing import Any
from xml.etree import ElementTree
import httpx
from app.services.registrar_adapter import RegistrarAdapter

NAMECHEAP_API_PROD = "https://api.namecheap.com/xml.response"
NAMECHEAP_API_SANDBOX = "https://sandbox.namecheap.com/xml.response"

class NamecheapAdapter(RegistrarAdapter):
    def __init__(self, api_key: str, api_secret: str | None = None, username: str | None = None, client_ip: str = "0.0.0.0", sandbox: bool = False):
        super().__init__(api_key, api_secret)
        if not username:
            raise ValueError("Namecheap username is required")
        if not client_ip or client_ip == "0.0.0.0":
            raise ValueError("Namecheap client IP is required")
        self.username = username
        self.client_ip = client_ip
        self.sandbox = sandbox
        self.api_url = NAMECHEAP_API_SANDBOX if sandbox else NAMECHEAP_API_PROD

    def _base_params(self, command: str) -> dict[str, str]:
        return {"ApiUser": self.username, "ApiKey": self.api_key, "UserName": self.username, "ClientIp": self.client_ip, "Command": command}

    def _check_response_errors(self, root, operation: str) -> None:
        ns = {"nc": "http://api.namecheap.com/xml.response"}
        errors = root.findall(".//nc:Error", ns)
        if errors:
            messages = [(error.text or "Unknown error").strip() for error in errors]
            message = "; ".join(messages)
            raise RuntimeError(f"Namecheap API error in {operation}: {message}")
        status = root.get("Status")
        if status and status.lower() != "ok":
            raise RuntimeError(f"Namecheap API {operation} returned Status={status}")
