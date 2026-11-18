# Isolated editorial content origin

This service serves the public Blog and BlogPost read views from a dedicated static origin at `content.shopnoltd.dpdns.org`.

- Public article list/detail reads are proxied to the existing `/api/v2/blog` API; the API remains the source of truth.
- Authenticated like, comment, save, and share actions remain on the original Shopnoltd article URL.
- No account, payment, domain, dashboard, download, or administrative API is proxied.
- No service worker is registered or served; `/sw.js` returns 404.
- The Monetag integration is **manual-test-only**: it loads only on a successfully rendered editorial article at `content.shopnoltd.dpdns.org/blog/{slug}?monetag-test=1`.
- Normal visitors, the editorial listing, and all other hosts do not load Monetag. The only configured zone is IPP `12129960`; zone `12128278`, Vignette `12288239`, Popunder/OnClick, and Multitag remain disabled.
- The main web-portal Blog routes remain available during staged migration and rollback.

The manual test gate is intentionally retained until a published article exists and the Monetag loader's browser network/CSP behavior has been checked. Do not remove the query gate or broaden CSP destinations without reviewing observed requests. The main Shopnoltd application, its AdSense implementation, database, secrets, and service worker are not modified.
