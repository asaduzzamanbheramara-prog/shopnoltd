# Shopnoltd VPN service

Production-oriented WireGuard control plane for infrastructure owned and operated by Shopnoltd.

Features: persistent peer registry, WireGuard key generation, peer add/remove/rotate, live interface reconciliation, NAT setup, health/readiness endpoints, and an authenticated admin API.

The WireGuard UDP endpoint must resolve directly to the VPN server; HTTP proxies/tunnels must not be used for UDP 51820.

Required runtime secret: `VPN_ADMIN_TOKEN`.
