# Shopnoltd Runbook

## Start/stop Cloudflared tunnel

The public platform is exposed through Cloudflare Tunnel using `C:\Users\asadu\.cloudflared\config.yml`.

To start the tunnel manually:

```powershell
cloudflared tunnel --config "C:\Users\asadu\.cloudflared\config.yml" run
```

The service is installed as a Windows service and starts automatically.

To check status:

```powershell
Get-Service -Name cloudflared
```

## Secrets management

Secrets are stored in Kubernetes as:
- `oauth-secrets`
- `postgres-secret`
- `stripe-secret`

Use the helper script to generate and apply them:

```powershell
Set-Item Env:STRIPE_SECRET_KEY "sk_test_..."
Set-Item Env:STRIPE_WEBHOOK_SECRET "whsec_..."
.\scripts\create_k8s_secrets.ps1 -Apply
```

Or use the auto deploy script with generated JWT/session/Postgres values:

```powershell
.\scripts\apply_secrets_auto.ps1
```

## Deployments

Update deployments and autoscaling manifests:

```bash
kubectl apply -f deployment-api-service.yaml
kubectl apply -f deployment-billing-engine.yaml
kubectl apply -f autoscaling/hpa-api-service.yaml
kubectl apply -f autoscaling/hpa-billing-engine.yaml
```

Restart services after secret or config changes:

```bash
kubectl rollout restart deployment/api-service -n default
kubectl rollout restart deployment/billing-engine -n default
```

## Observability

Prometheus/Grafana can be installed with Helm:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --namespace observability --create-namespace
```

Apply alert rules:

```bash
kubectl apply -f observability/alerts/billing-alerts.yaml -n observability
```

## Integration tests

Run the Stripe webhook test locally:

```bash
pip install -r requirements.txt
python scripts/test_stripe_webhook.py --secret "whsec_..."
```

Health check endpoints:

- https://api.shopnoltd.dpdns.org/health
- https://billing.shopnoltd.dpdns.org/health

## Backup suggestions

Postgres backups should be scheduled to a remote object store, and uploads should be kept in a persistent volume with versioned snapshots.

## DNS and Cloudflare

The domain `shopnoltd.dpdns.org` is served through Cloudflare and the tunnel. Ensure the Cloudflare DNS records point to the tunnel endpoint and `proxy` mode is enabled where required.
