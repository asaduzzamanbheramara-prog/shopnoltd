# Social Login (Google, Facebook, GitHub)

## Design decision

Social login is added as **Keycloak Identity Providers**, not as new code in
`oauth-service`. Every service in this platform already authenticates via
Keycloak OIDC (`docs/SERVICE_TOPOLOGY.md`), so brokering Google/Facebook/GitHub
through Keycloak means every service gets social login automatically, with
one integration point instead of duplicating OAuth flows.

## One-time setup

1. Fill in your real values in `scripts/seed/social-login-secrets.local.yaml`
   (gitignored -- already created with the values you shared; rotate them in
   each provider's console once this is confirmed working, since they were
   pasted into a chat log and should be treated as compromised).

2. Make sure Keycloak is actually deployed and reachable
   (`docs/SECRETS.md` first -- the `keycloak-secret` Secret has to exist and
   be filled in, or Keycloak itself won't start).

3. Run the setup script from a machine that can reach your Keycloak URL:

   ```bash
   export KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
   export KEYCLOAK_REALM=shopnoltd
   export KEYCLOAK_ADMIN_USER=admin
   export KEYCLOAK_ADMIN_PASSWORD='the real bootstrap password from your secret.yaml'
   pip install pyyaml --break-system-packages
   python3 scripts/setup_social_login.py scripts/seed/social-login-secrets.local.yaml
   ```

   This is idempotent -- re-run it any time you rotate a credential.

4. In each provider's developer console, set the redirect/callback URI the
   script prints at the end, e.g.:
   - Google Cloud Console -> Credentials -> OAuth client -> Authorized redirect URIs
   - Facebook for Developers -> Facebook Login -> Settings -> Valid OAuth Redirect URIs
   - GitHub -> Settings -> Developer settings -> OAuth Apps -> Authorization callback URL

   All three take the same shape:
   `https://auth.shopnoltd.dpdns.org/realms/shopnoltd/broker/<provider>/endpoint`

5. Confirm on the web portal login page -- Google/Facebook/GitHub buttons
   should now appear on the Keycloak login screen used by every service.

## Common failure modes

- **`kubectl apply -f k8s/services/oauth-service/sealed-secret.yaml/oauth-secrets.yaml`
  fails** -- that path treats a directory as a file. If you're using
  sealed-secrets, the sealed file replaces `secret.yaml` itself
  (`k8s/services/oauth-service/sealed-secret.yaml`), it isn't a directory
  containing another file.
- **`helm: command not found`** -- install with `sudo snap install helm --classic`
  (or see https://helm.sh/docs/intro/install/ for other package managers).
- **`kubeseal: command not found`** -- see the install steps in
  `docs/SECRETS.md`.
- **Pasting multi-line chat responses (with `#` headers, numbered lists,
  etc.) directly into bash** -- bash will try to execute the prose as
  commands. Copy only the fenced code blocks, one command at a time, not the
  surrounding explanation.
