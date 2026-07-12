# Shopnoltd Service Topology

Every service depends on the ones above it. The arrows mean "calls / reads from / writes to".

                    ┌────────────┐
                    │  Keycloak  │  (auth.shopnoltd.dpdns.org)
                    └─────┬──────┘
                          │ OIDC tokens
       ┌──────────────────┼────────────────────────┐
       │                  │                        │
       ▼                  ▼                        ▼
   api-service     gateway                  oauth-service
       │                  │                        │
       │     ┌────────────┴───────────┐            │
       │     │                        │            │
       ▼     ▼                        ▼            ▼
   payment  billing-engine    tenant-router   auth-service
   service  exchange-service
       │          │                    │
       │          ▼                    ▼
       │     report-service      ┌─────┴──────┐
       │                         │            │
       │                         ▼            ▼
       │                   jitsi / meet   chatwoot
       │                         │            │
       │                         ▼            ▼
       │                   kobotoolbox    owncast
       │                         │            │
       │                         ▼            ▼
       │                   onlyoffice    nextcloud
       │                         │            │
       │                         ▼            ▼
       │                     gitea        code-server
       │                         │
       │                         ▼
       │                    notification
       │                       service
       │
       ▼
  search/analytics/audit/license/scheduler/worker/mobile-api/admin-portal/web-portal

## Cross-cutting services
- All services depend on Keycloak for OIDC
- All services depend on storage-service (MinIO S3) for files
- All services depend on Postgres (shared) and per-service DBs
- All services depend on Redis (cache + queue)
- All web/UI services depend on storage-service for assets
- All mobile apps depend on mobile-api + payment-service
- All paid services depend on billing-engine (entitlement check)
- All multi-currency services depend on exchange-service (FX rates)
- All services log to Loki, emit metrics to Prometheus, traces to Tempo
- All services route through Traefik → cloudflared → public DNS

## Trust zones
- shopno-payments: PCI-isolated namespace, only oauth-service and api-service may call it
- shopno-identity: only gateway, oauth-service, auth-service may call it
- shopno-data: only data plane services may call it directly
- shopno-ingress: only Traefik + cloudflared; everything else is egress-only
