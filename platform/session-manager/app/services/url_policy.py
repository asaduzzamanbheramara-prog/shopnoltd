"""SSRF guard for server-side browser navigation and page subresources."""
import asyncio
import ipaddress
import socket
import time
from urllib.parse import urlsplit


class PublicURLPolicy:
    def __init__(self, cache_seconds: int = 20):
        self.cache_seconds = cache_seconds
        self._dns_cache: dict[str, tuple[float, bool]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            scheme = parsed.scheme.lower()
            if scheme in {"about", "data", "blob"}:
                return True
            if scheme not in {"http", "https"} or not parsed.hostname:
                return False
            if parsed.username is not None or parsed.password is not None:
                return False
            host = parsed.hostname.rstrip(".").lower()
            if (
                host == "localhost"
                or host.endswith((".localhost", ".local", ".internal", ".svc", ".cluster.local"))
                or host in {"metadata.google.internal", "metadata", "kubernetes.default"}
            ):
                return False
            try:
                address = ipaddress.ip_address(host)
                return address.is_global
            except ValueError:
                pass

            now = time.monotonic()
            async with self._lock:
                cached = self._dns_cache.get(host)
                if cached and cached[0] > now:
                    return cached[1]
            try:
                records = await asyncio.wait_for(
                    asyncio.to_thread(socket.getaddrinfo, host, parsed.port or (443 if scheme == "https" else 80), 0, socket.SOCK_STREAM),
                    timeout=3,
                )
                addresses = {ipaddress.ip_address(item[4][0]) for item in records}
                allowed = bool(addresses) and all(address.is_global for address in addresses)
            except (OSError, ValueError, asyncio.TimeoutError):
                allowed = False
            async with self._lock:
                self._dns_cache[host] = (time.monotonic() + self.cache_seconds, allowed)
            return allowed
        except (ValueError, TypeError):
            return False

    async def require_allowed(self, url: str) -> None:
        if not await self.is_allowed(url):
            raise ValueError("This browser blocks private, local, or non-HTTP destinations for security.")
