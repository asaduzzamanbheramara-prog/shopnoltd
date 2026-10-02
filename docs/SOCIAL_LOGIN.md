# Social Login (Google, Facebook, GitHub)

## Design decision

Social login is added as **Keycloak Identity Providers**, not as new code in
`oauth-service`. Every service in this platform already authenticates via
Keycloak OIDC (`docs/SERVICE_TOPOLOGY.md`), so brokering Google/Facebook/GitHub
through Keycloak means every service gets social login automatically, with
one integration point instead of duplicating OAuth flows.

## One-time setup

1. Provision the runtime Kubernetes Secret `shopno-identity/keycloak-social-providers` using the interactive provisioning procedure documented in `docs/SECRETS.md`. Never commit the real values or put them in a ConfigMap, PR, issue, or shell script.

2. The Keycloak GitOps sync hook reconciles Google, Facebook, and GitHub from that Secret. If the Secret is absent or a provider is incomplete, the sync hook leaves social providers unchanged and does not break the Keycloak deployment.

3. In each provider's developer console, set the redirect/callback URI:
   - Google Cloud Console -> Credentials -> OAuth client -> Authorized redirect URIs
   - Facebook for Developers -> Facebook Login -> Settings -> Valid OAuth Redirect URIs
   - GitHub -> Settings -> Developer settings -> OAuth Apps -> Authorization callback URL

   All three take the same shape:
   `https://auth.shopnoltd.dpdns.org/realms/shopnoltd/broker/<provider>/endpoint`

5. Confirm on the web portal login page -- Google/Facebook/GitHub buttons
   should now appear on the Keycloak login screen used by every service.


## GitOps behavior

The Keycloak client-sync hook is the durable source-controlled integration. It reads provider credentials only from the runtime Secret and never writes credentials into Git. Provider aliases are fixed as `google`, `facebook`, and `github`, matching the callback paths below. The synchronization is idempotent and updates an existing provider rather than creating duplicates.

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
