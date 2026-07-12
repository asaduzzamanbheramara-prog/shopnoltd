# Changelog

All notable changes to Shopnoltd are documented here.

## [0.1.0] - 2026-07-12

### Added
- 44 service base manifests (21 platform + 23 upstream)
- 2 portal services (android-portal, pc-portal)
- cloudflared tunnel deployment
- GitHub Actions CI (validate + lint)
- GitHub Actions build pipeline (21 platform images → ghcr.io)
- GitHub Actions branding pipeline (10 upstream images)
- Prometheus Operator install script
- Service-to-service dependency topology
- Branding overlay Dockerfile
- Tenant router, payment service, exchange service skeletons

### Security
- NetworkPolicy + PodSecurity=restricted on all namespaces
- All secrets via Kubernetes Secrets (sealed-secrets recommended in production)
- readOnlyRootFilesystem on every container
- All capability drops
