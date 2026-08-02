# Shopnoltd Automation Scripts (PowerShell 7.6.4)

Three independent, safe-by-default scripts. Run from `C:\Users\asadu\PROJECTS\shopnoltd` in PowerShell 7.

## Order of operations

1. **`01-repo-audit-cleanup.ps1`** — dry run first, review the list, then `-Apply`.
   Moves clutter into `.archive\<timestamp>\` instead of deleting — nothing is lost.

   ```powershell
   ./01-repo-audit-cleanup.ps1              # dry run
   ./01-repo-audit-cleanup.ps1 -Apply        # actually archive
   ```

2. **`02-k8s-oauth-secrets-rotate.ps1`** — run this *after* you've generated new
   credentials in the Google/Facebook/GitHub developer consoles (the ones
   pasted in your terminal history are compromised and should not be reused).

   ```powershell
   ./02-k8s-oauth-secrets-rotate.ps1
   # prompts securely for each ID/secret, applies a Secret to shopno-identity
   ```

   Then update your Deployment manifests to pull from the Secret via
   `envFrom.secretRef` instead of inline `value:` fields, and remove the
   plaintext values from any committed YAML.

3. **`03-branding-sync.ps1`** — first run generates a starter
   `branding\branding-manifest.json`; edit the source/target paths to match
   your actual portal folder structure, then re-run to copy assets out.

   ```powershell
   ./03-branding-sync.ps1 -WhatIf   # preview
   ./03-branding-sync.ps1            # apply
   ```

## What this does NOT cover

- **Registration/login functionality itself.** Wiring up OAuth callback
  routes, session/JWT issuance, and user creation in Postgres is backend
  code specific to each service's framework (FastAPI, Keycloak realm config,
  etc.). This is a per-service coding task, not something a PowerShell layer
  can generate safely across 40+ services with differing internals. Happy to
  do this next, service by service, once the secrets/branding groundwork above
  is in place.
- **APK rebuilding/signing.** Updating branding inside an already-built `.apk`
  requires decompiling/recompiling and re-signing — better done by rebuilding
  from your Android source (`mobile/android-portal`) with the new assets from
  script 3, then a normal Gradle build, rather than patching a compiled APK.
