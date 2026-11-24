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


## GitHub disaster-recovery backup contract

The scheduled postgres-backup.yml workflow publishes encrypted snapshots to the database-backups branch of a separate private GitHub repository. The source Shopnoltd repository is public, so encrypted backup artifacts must never be pushed to a branch in the source repository. It includes the primary PostgreSQL dump, every connectable non-template database plus global roles, and an all-namespace Kubernetes Secret export. The workflow decrypts and parses each snapshot before publishing it. A keyed HMAC-SHA256 sidecar is generated for every encrypted artifact and verified before any decryption, so ciphertext tampering is detected (a plain SHA-256 checksum alone is not an authenticity check).

Configure these GitHub Actions repository secrets before enabling the backup workflow:
- BACKUP_REPOSITORY: owner/private-repository for a dedicated private backup repository, different from the public source repository.
- BACKUP_REPOSITORY_TOKEN: a fine-grained GitHub token restricted to that private backup repository with Contents read/write access. It is used only for the backup push.
- BACKUP_ENCRYPTION_KEY: the high-entropy encryption passphrase used for the encrypted snapshots.

The workflow verifies through the GitHub API that the destination exists and is private, and fails closed if the destination is missing, public, or the source repository. It pushes only to the separate private repository's database-backups branch.

BACKUP_ENCRYPTION_KEY is a GitHub Actions repository secret and must remain outside Git. Keep an independently recoverable copy in an approved password manager or offline secret vault; do not store the only decryption key in the same GitHub account/repository as the encrypted backup. Rotate it only with a planned re-encryption of retained backups. Restrict write access to the private backup repository, its backup branch, and the Actions workflow.

GitHub Actions secret values cannot be read back by workflows or exported by GitHub. Therefore GitHub repository/environment secret names and their values must be maintained in an external secret inventory/password manager and restored manually through the GitHub Settings UI or API. The encrypted Kubernetes Secret snapshot does not contain GitHub Actions secrets, external provider-console credentials that were never installed in Kubernetes, or user passwords.

The platform account registry and each user's profile/connection metadata live in PostgreSQL, with encrypted provider tokens in the social database. GitHub stores code, migrations, provider capability/configuration templates and encrypted disaster-recovery snapshots—not live plaintext user profiles or provider tokens. The Platform Accounts UI is user-scoped; administrative cross-user operations must use a separately authorized admin view with audit logging and must never weaken tenant/owner isolation.

Restore remains a deliberate, reviewed operation: retrieve the backup branch, verify HMAC and checksum, decrypt with the separately held key, restore into an isolated target first, validate row counts/ownership and service compatibility, then approve any production recovery. The scheduled backup is not proof of a successful full restore until a periodic isolated restore drill passes.
