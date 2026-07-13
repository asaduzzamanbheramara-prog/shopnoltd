# Secrets Management

## Why every service failed to deploy

Every `k8s/services/<name>/kustomization.yaml` lists `secret.yaml` as a
resource, but no `secret.yaml` files were committed (they match this repo's
`.gitignore` secret patterns, which is correct -- they should never be
committed with real values). That meant `kubectl apply -k k8s/services/<name>`
failed for **every service** with a missing-resource error.

`scripts/generate_missing_secrets.py` has generated a placeholder
`secret.yaml` for each service, with the exact keys that service's
`deployment.yaml` actually references (parsed from `envFrom.secretRef` and
`env[].valueFrom.secretKeyRef`). Every value is the literal string
`REPLACE_WITH_BASE64` -- these will NOT work until you fill them in.

Re-run `python3 scripts/generate_missing_secrets.py` any time you add a new
service; it skips files that already exist.

## Two ways to fill in real values

### Option A -- fastest, for local/dev clusters
Edit the generated `secret.yaml` directly and base64-encode each value:

```bash
echo -n 'your-real-value' | base64 -w0
```
Paste the result in place of `REPLACE_WITH_BASE64`, then:
```bash
kubectl apply -k k8s/services/<name>
```
Do not commit the file once real values are in it (it already matches
`.gitignore`, but double check with `git status` first).

### Option B -- recommended for anything shared/production: sealed-secrets
Sealed-secrets lets you commit an *encrypted* version of the secret safely.

```bash
# Install kubeseal CLI (Linux x86_64 example -- check
# https://github.com/bitnami-labs/sealed-secrets/releases for your arch)
KUBESEAL_VERSION='0.27.1'
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
tar -xzf "kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz" kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# Install the sealed-secrets controller into the cluster (needs helm)
sudo snap install helm --classic     # if helm isn't installed yet
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# Seal a filled-in secret.yaml into something safe to commit
kubeseal --format=yaml < k8s/services/keycloak/secret.yaml > k8s/services/keycloak/sealed-secret.yaml
```
Then reference `sealed-secret.yaml` (not `secret.yaml`) from
`kustomization.yaml`, and it's safe to commit.

## Social login credentials specifically

See `docs/SOCIAL_LOGIN.md`. The Google/Facebook/GitHub values go into
`k8s/services/keycloak/secret.yaml` (already has the right keys) AND are
consumed by `scripts/setup_social_login.py`, which registers them with
Keycloak directly over the Admin REST API -- that script needs the *plaintext*
values (from `scripts/seed/social-login-secrets.local.yaml`, gitignored), not
the base64 copies in the Kubernetes Secret.

## Rotating leaked credentials

If a real secret has ever been pasted into a chat log, committed to git, or
run through a shell history file, treat it as compromised even if "it still
works today":

1. Rotate it at the source (Stripe dashboard, Google/Facebook/GitHub developer
   console, etc.)
2. Update the relevant `secret.yaml` (or re-seal it, if using Option B)
3. `kubectl rollout restart deployment/<name> -n <namespace>`
4. If it was committed to git history (not just the working tree), scrub it
   with `git filter-repo` or BFG Repo-Cleaner -- a later commit that deletes
   the file does not remove it from history.
