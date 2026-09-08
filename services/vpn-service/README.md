# Shopnoltd VPN service

Production-oriented WireGuard control plane for infrastructure owned and operated by Shopnoltd.

Features: persistent peer registry, WireGuard key generation, peer add/remove/rotate, live interface reconciliation, NAT setup, health/readiness endpoints, and an authenticated admin API.

The WireGuard UDP endpoint must resolve directly to the VPN server; HTTP proxies/tunnels must not be used for UDP 51820.

Required runtime secret: `VPN_ADMIN_TOKEN`.

## Kubernetes secret provisioning

Do not commit the VPN admin token. Provision it into `shopno-apps` before the deployment is expected to become Ready:

```bash
export VPN_ADMIN_TOKEN='REPLACE_WITH_A_NEW_RANDOM_TOKEN'
./scripts/create_vpn_secret.sh
unset VPN_ADMIN_TOKEN
```

The helper sends the value to the Kubernetes API through manifest input and does not print the token. Rotate the token by repeating the same process with a new value and restarting the deployment.

## Runtime networking

`vpn.shopnoltd.dpdns.org:51820` must be DNS-only/direct to a reachable UDP endpoint. Cloudflare HTTP proxying or a Cloudflare Tunnel cannot carry this WireGuard UDP listener.

The current service configures IPv4 forwarding and NAT. IPv6 is intentionally not advertised until an IPv6 forwarding/NAT path is implemented.
