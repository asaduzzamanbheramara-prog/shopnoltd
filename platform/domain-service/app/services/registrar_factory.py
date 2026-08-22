"""Picks the correct RegistrarAdapter implementation based on a Registrar DB row."""

from app.models.models import Registrar
from app.services.registrar_adapter import RegistrarAdapter
from app.services.registrars.cloudflare import CloudflareAdapter
from app.services.registrars.namecheap import NamecheapAdapter

_ADAPTERS: dict[str, type[RegistrarAdapter]] = {
    "namecheap": NamecheapAdapter,
    "cloudflare": CloudflareAdapter,
}


def get_adapter(registrar: Registrar) -> RegistrarAdapter:
    adapter_cls = _ADAPTERS.get(registrar.name.lower())
    if adapter_cls is None:
        raise ValueError(
            f"No adapter registered for registrar '{registrar.name}'. "
            f"Known registrars: {list(_ADAPTERS)}"
        )
    return adapter_cls(api_key=registrar.api_key, api_secret=registrar.api_secret)
