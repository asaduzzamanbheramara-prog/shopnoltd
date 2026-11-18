# Isolated editorial content origin

This service serves the public Blog and BlogPost read views from a dedicated static origin at `content.shopnoltd.dpdns.org`.

- Public article list/detail reads are proxied to the existing `/api/v2/blog` API; the API remains the source of truth.
- Authenticated like, comment, save, and share actions remain on the original Shopnoltd article URL.
- No account, payment, domain, dashboard, download, or administrative API is proxied.
- No service worker is registered or served; `/sw.js` returns 404.
- No Monetag or AdSense tags are included.
- The main web-portal Blog routes remain available during staged migration and rollback.

Do not enable Monetag until CI passes, the image is published, the content host is deployed and verified, API read proxy behavior is tested, and the AdSense experiment is reviewed.