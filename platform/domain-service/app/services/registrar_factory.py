import os
from app.models.models import Registrar
from app.services.registrar_adapter import RegistrarAdapter
from app.services.registrars.cloudflare import CloudflareAdapter
from app.services.registrars.namecheap import NamecheapAdapter

_ADAPTERS = {"namecheap": NamecheapAdapter, "cloudflare": CloudflareAdapter}

def get_adapter(registrar: Registrar) -> RegistrarAdapter:
    adapter_cls = _ADAPTERS.get(registrar.name.lower())
    if adapter_cls is None:
        raise ValueError(f"No adapter: {registrar.name}. Known: {list(_ADAPTERS)}")
    kwargs = {"api_key": registrar.api_key, "api_secret": registrar.api_secret}
    if registrar.name.lower() == "namecheap":
        username = os.getenv("NAMECHEAP_USERNAME")
        client_ip = os.getenv("NAMECHEAP_CLIENT_IP")
        use_sandbox = os.getenv("NAMECHEAP_SANDBOX", "false").lower() == "true"
        if not username:
            raise RuntimeError("NAMECHEAP_USERNAME not configured")
        if not client_ip:
            raise RuntimeError("NAMECHEAP_CLIENT_IP not configured")
        kwargs["username"] = username
        kwargs["client_ip"] = client_ip
        kwargs["sandbox"] = use_sandbox
    return adapter_cls(**kwargs)
