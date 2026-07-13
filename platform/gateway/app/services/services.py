"""
Registry of internal service URLs the gateway fronts with Traefik.

Names/ports here are derived from the actual k8s manifests under k8s/services/*
(namespace: shopno-platform, standard port 8080 unless noted). Two entries
(social, messaging) don't have a matching k8s/services/<name> directory yet —
they're included with a best-guess name so routes.py doesn't crash, but flagged
below. Add the real k8s Service for those (or correct the name here) before
relying on routing to them.
"""

NAMESPACE = "shopno-platform"

def _svc(name: str, port: int = 8080) -> str:
    return f"http://{name}.{NAMESPACE}.svc.cluster.local:{port}"

SERVICES = {
    "auth":         _svc("auth-service"),
    "payment":      _svc("payment-service"),
    "billing":      _svc("billing-engine"),
    "exchange":     _svc("exchange-service"),
    "social":       _svc("social-service"),      # TODO: no k8s/services/social-service yet
    "messaging":    _svc("messaging-service"),   # TODO: no k8s/services/messaging-service yet
    "notification": _svc("notification-service"),
    "storage":      _svc("storage-service"),
    "ai":           _svc("ai-platform"),
    "analytics":    _svc("analytics-service"),
    "api":          _svc("api-service"),
    "search":       _svc("search-service"),
    "audit":        _svc("audit-service"),
}
