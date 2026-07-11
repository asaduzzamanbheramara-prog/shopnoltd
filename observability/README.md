Observability setup (Prometheus + Grafana)

This repository includes alerting rules and instructions to install a production-ready observability stack.

Recommended installation (Helm):

1. Add the Prometheus community Helm repo and install kube-prometheus-stack:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --namespace observability --create-namespace
```

2. Deploy the alerting rules included in `observability/alerts`:

```bash
kubectl apply -f observability/alerts/billing-alerts.yaml -n observability
```

3. For Grafana dashboards, enable the Grafana instance installed by the chart and add dashboards or use provisioning.

Notes:
- The example alert `BillingEndpointErrorsHigh` assumes your app exports Prometheus metrics, including `http_server_requests_seconds_count` with `handler` and `status` labels. If you use a different metric name (e.g., from `fastapi_prometheus` or `starlette_exporter`), update the rule accordingly.
- To forward traces, use OpenTelemetry Collector and configure your apps to export OTLP (this repo already includes `OTEL_EXPORTER_OTLP_ENDPOINT` env vars).
