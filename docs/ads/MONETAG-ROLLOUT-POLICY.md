# Monetag rollout policy for Shopnoltd

## Current decision

Monetag Vignette zone `12288239` is **not enabled**. The supplied tag is retained behind an explicit disabled gate in `platform/web-portal/index.html`. Do not change `MONETAG_ENABLED` to `true` or populate `ALLOWED_HOSTS` until the AdSense Vignette frequency experiment has completed and a dedicated content-only host has been approved.

## Non-Vignette formats: staged plan

Monetag documents Push Notifications, In-Page Push (IPP), and Direct Link as formats that can generally coexist with AdSense when they do not cover or move Google ad units, interfere with navigation, or create excessive ad density. This is not blanket approval for every Shopnoltd page: the publisher remains responsible for the complete page experience and all ad networks present.

| Format | Rollout decision | Technical requirement / blocker |
| --- | --- | --- |
| In-Page Push | First candidate for a controlled content-only test; not active yet | Copy the exact IPP zone tag from the Monetag dashboard and install only on a dedicated isolated content host. Test placement, dismissal, consent, mobile/desktop, and navigation. |
| Push Notifications | Defer until a dedicated host is available | Monetag requires its zone-provided `sw.js` at the site root. Shopnoltd already has an application service worker at `/sw.js`; do not overwrite or merge provider code into it without a separately reviewed integration and rollback plan. |
| Direct Link | Optional later, clearly labelled sponsored link only | Must be a separate sponsored placement, never a service, download, registration, or payment button. |
| Vignette Banner | Disabled while the AdSense Vignette frequency experiment is Running | Review the completed AdSense experiment before considering a separate controlled test. |
| OnClick / Popunder | Prohibited on AdSense pages | Google AdSense policy does not permit ads on sites that contain or trigger pop-unders. |

No Monetag IPP or Push script has been fabricated from a zone ID. The exact publisher-generated code and any required root file must come from the Monetag dashboard.

## Why a global tag is unsafe

The Cloudflare Tunnel and Kubernetes ingress route many explicit Shopnoltd subdomains and a wildcard `*.shopnoltd.dpdns.org` host. The wildcard ingress can serve the shared web portal on hosts beyond the public marketing site. A script placed unconditionally in the shared HTML shell would therefore execute on more hosts than the main website, potentially including service workflows.

The shared portal is also a single-page application. A one-time script loaded on an allowed landing route may remain active while the visitor navigates to login, registration, dashboard, checkout, or other functional routes. A static path check in the HTML shell is not sufficient to guarantee safe route-by-route behavior.

The existing public Blog and Blog Post pages are also routes inside this same shared SPA, not an independently isolated host. They are therefore not yet a safe place to install a persistent Monetag script.

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

1. Confirm the AdSense Vignette experiment is complete before testing Monetag Vignette.
2. Provision a dedicated public content-only hostname with an independently controlled origin/service-worker scope; do not assume the wildcard SPA is isolated.
3. Obtain the exact zone tag(s) and any provider files from the Monetag dashboard.
4. Verify host routing and the final deployed HTML for every included and excluded hostname.
5. Test desktop/mobile, consent, keyboard navigation, back/forward navigation, and ad dismissal.
6. Confirm no ad overlays, shifts, or blocks Google ads, page content, navigation, or user actions.
7. Enable only the approved host(s), then monitor complaints, bounce rate, page performance, and Monetag/AdSense reports.
8. Keep the existing Shopnoltd service worker unchanged unless a separately reviewed integration is approved.

## Existing ad-network note

The current web-portal Home, Services, Blog, and Blog Post pages import Adsterra components. This policy does not remove or alter those existing placements; they need a separate placement/density/policy review before any additional network is enabled.
