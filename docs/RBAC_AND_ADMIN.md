# 3-Tier Access: Admins, Tenant Owners, Customers

## Roles

| Role | Scope | Can edit |
|---|---|---|
| `platform_admin` | every tenant | everything: users, tenants, customers, theme/texts/plugins, roles |
| `tenant_owner` | their own tenant only | that tenant's customers, theme, texts, plugins |
| `customer` | their own record only | their own name/phone/billing address/preferences |

Roles and the `tenant_id` claim come from the Keycloak JWT, never from a
client-supplied field -- `app/core/security.py` in `oauth-service` enforces
this (`require_tenant_access`, `require_customer_self_or_above`).

## One-time setup

```bash
export KEYCLOAK_URL=https://auth.shopnoltd.dpdns.org
export KEYCLOAK_REALM=shopnoltd
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD='...'
python3 scripts/setup_rbac_roles.py
```

This creates the three realm roles and a token mapper so they appear as a
flat `roles` array in the JWT (matching what the existing `admin` role
already did). Assign a role to a user via the Keycloak admin console or the
Admin REST API; for `tenant_owner`/`customer`, also set a `tenant_id` user
attribute (with a matching protocol mapper) so it lands in the token.

## What's editable today (oauth-service)

New endpoints, following the same pattern as the existing `users`/`tenants`
routers:

- `GET/PATCH /api/v1/tenants/{tenant_id}/settings` -- theme, texts, plugins
  (JSON blobs merged in per-key, so a tenant_owner can update just the theme
  without touching texts/plugins). Read is public (storefronts need it
  pre-login); write is `platform_admin` or `tenant_owner` only.
- `POST/GET/PATCH/DELETE /api/v1/customers/{tenant_id}/customers[/{id}]` --
  full customer CRUD. Create/list/delete are admin/owner only; a customer can
  `GET`/`PATCH` only their own record.
- Existing `users`, `tenants`, `roles` routers are still `admin`-only
  (mapped to `platform_admin` going forward -- see "Migration" below).

## Not built yet (next steps, in priority order)

1. **Migrate the old `admin`-only checks** (`users.py`, `tenants.py`,
   `roles.py`) to also accept `platform_admin`, so there's one consistent
   role name across the whole service.
2. **Code/plugin editing** -- "editing code" safely needs a review step (a
   git-backed config repo + CI, or a sandboxed plugin runtime), not a raw
   file-write API. I did not build an endpoint that lets any role edit
   server-side code directly, since an unreviewed code-write endpoint is a
   remote-code-execution risk regardless of which role can reach it. A
   safer version of this: tenant_owner submits a plugin manifest (JSON
   config only, no arbitrary code) that a fixed, audited plugin loader reads
   -- the `plugins` key in tenant settings above is the seed of that.
3. **Database editing UI** -- direct database-editing endpoints (arbitrary
   table/row access) are also intentionally not built the same way for the
   same reason; expose specific, validated fields per resource (as
   `customers`/`tenant_settings` do) rather than a generic DB editor.
4. **Frontend** -- `admin-portal`/`web-portal` don't yet call any of this;
   the API is ready to build a UI against.
5. **Domain registration workflow** -- "domain registers" (buying/pointing a
   custom domain per tenant) needs a registrar API integration
   (Cloudflare Registrar, Namecheap, etc.) plus DNS automation against the
   cloudflared tunnel config; not started.
