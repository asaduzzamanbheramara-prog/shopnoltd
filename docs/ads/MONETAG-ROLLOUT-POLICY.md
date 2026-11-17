# Monetag rollout policy for Shopnoltd

## Current decision

Monetag Vignette zone `12288239` is **not enabled**. The supplied tag is retained behind an explicit disabled gate in `platform/web-portal/index.html`. Do not change `MONETAG_ENABLED` to `true` or populate `ALLOWED_HOSTS` until the AdSense Vignette frequency experiment has completed and a dedicated content-only host has been approved.

## Why a global tag is unsafe

The Cloudflare Tunnel and Kubernetes ingress route many explicit Shopnoltd subdomains and a wildcard `*.shopnoltd.dpdns.org` host. The wildcard ingress can serve the shared web portal on hosts beyond the public marketing site. A script placed unconditionally in the shared HTML shell would therefore execute on more hosts than the main website, potentially including service workflows.

The shared portal is also a single-page application. A one-time script loaded on an allowed landing route may remain active while the visitor navigates to login, registration, dashboard, checkout, or other functional routes. A static path check in the HTML shell is not sufficient to guarantee safe route-by-route behavior.

## Placement policy

| Surface | Monetag policy |
| --- | --- |
| Main public marketing/content pages | Candidate only after experiment review and a dedicated-host/route isolation test |
| Domain search, registration, management, renewal | Never inject into workflow or action buttons |
| Login, registration, OAuth callback, account/dashboard | Excluded |
| Billing, wallet, payment, checkout, transaction | Excluded |
| Cloud, Android Cloud, downloads, software installation | Excluded |
| Admin, database, infrastructure, API, auth | Excluded |
| User action buttons and navigation links | Never replace, intercept, disguise, or auto-trigger ads |
| Popunder / OnClick | Excluded while Google AdSense is present |

## Button and link requirements

- Preserve all existing functional button/link destinations and handlers.
- Never attach Monetag navigation or click handlers to Register Domain, Buy, Pay, Login, Download, Install, Dashboard, or service-launch controls.
- Any future Direct Link placement must be a separate, clearly labelled sponsored link, not a substitute for a product/service action.
- Do not trigger an ad on a user click unless the placement is explicitly disclosed and approved; do not simulate clicks or force redirects.

## Required checks before enabling

1. Confirm the AdSense Vignette experiment is complete and review its result.
2. Select a dedicated public content-only hostname that does not share the portal shell with protected workflows.
3. Verify host routing and the final deployed HTML for every included and excluded hostname.
4. Test desktop/mobile, consent, keyboard navigation, back/forward navigation, and ad dismissal.
5. Confirm no ad overlays, shifts, or blocks Google ads, page content, navigation, or user actions.
6. Enable only the approved host(s), then monitor complaints, bounce rate, page performance, and Monetag/AdSense reports.
7. Keep the existing Shopnoltd service worker unchanged. Do not add a Monetag service worker.

## Existing ad-network note

The current web-portal Home and Services pages already import Adsterra components. This policy does not remove or alter those existing placements; they need a separate placement/policy review before any additional network is enabled.
