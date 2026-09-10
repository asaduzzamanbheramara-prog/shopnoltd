# Release Gate change detection

The production release gate determines deployment scope for push events from the GitHub compare API using the push `before` and `after` revisions. This avoids relying on the push event's optional `commits` list, which can be empty for some merge/push payloads.

Deployment-controlled paths are `k8s/**`, `ops/cloudflare/**`, and `.github/workflows/self-hosted-k3s-gitops.yml`.
