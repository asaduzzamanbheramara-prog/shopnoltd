# Isolated editorial content origin

This service serves the public Blog and BlogPost read views from a dedicated static origin at `content.shopnoltd.dpdns.org`.

- Public article list/detail reads are proxied to the existing `/api/v2/blog` API; the API remains the source of truth.
- Authenticated like, comment, save, and share actions remain on the original Shopnoltd article URL.
- No account, payment, domain, dashboard, download, or administrative API is proxied.
- No service worker is registered or served; `/sw.js` returns 404.
- Monetag zone `12129960` is integrated on successfully rendered editorial article pages at `content.shopnoltd.dpdns.org/blog/{slug}`.
- Monetag loads only after the visitor explicitly allows advertising and the public ad-policy API confirms that the exact content hostname, Monetag network, and Blog placement are enabled. A visible Privacy settings control lets visitors revisit their choice.
- The verified Monetag root domain `shopnoltd.dpdns.org` can use the same ad-zone code on its subdomains, according to Monetag's publisher guidance. Shopnoltd still applies its own exact-host allowlist and policy checks; the content subdomain is explicitly listed rather than using a wildcard.
- The content host's CSP permits the Monetag loader and the public policy API only. No service worker, Popunder, or additional Monetag zones are enabled by this loader.
- The main web-portal Blog routes remain available during staged migration and rollback.

The integration is code-complete for the configured article placement, but browser network/CSP verification and live publisher reporting must still be checked after deployment. Do not claim impressions or revenue based only on a successful build or an enabled zone. The main Shopnoltd application, its AdSense implementation, database, and secrets are not modified.
