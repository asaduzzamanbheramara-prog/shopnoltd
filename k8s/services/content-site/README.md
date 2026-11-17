# Isolated editorial content origin

This static site is intentionally separate from the web-portal SPA.

- Host: `content.shopnoltd.dpdns.org`
- Backend: `content-site` Deployment and ClusterIP Service
- No application JavaScript bundle, authentication, payment, domain, account, API, or download routes.
- No service worker is registered or served.
- No Monetag or AdSense tag is enabled by this implementation.

The current page is an isolation placeholder. Do not advertise this as a migrated Blog until existing Blog/BlogPost content, canonical URLs, redirects, metadata and internal links have been migrated and checked. Do not enable Monetag until that migration and a separate policy/AdSense experiment review are complete.
