# Adsterra Publisher Ads

## Current integration

The public Shopnoltd homepage loads one Adsterra 300x250 display zone through
`src/components/AdsterraBanner.jsx`. The zone is inserted after the homepage hero.
The component creates the script after mount and removes the inserted script on
unmount to avoid duplicate loads during client-side navigation.

The integration uses the publisher-provided zone key and script URL. Before
production release, verify the full snippet and domain in the official Adsterra
publisher dashboard. The supplied script host is `bicea.org`; this is different
from the Adsterra marketing domain, so confirm it is an authorized delivery host
for this exact zone. Do not substitute or rewrite the host without confirmation
from Adsterra.

## Other zones not enabled

The following formats are intentionally not loaded by default:

- 160x300, 160x600, 468x60, 728x90
- 320x50 mobile banner
- Native Banner
- Popunder
- Smartlink
- SocialBar

Start with a single display placement and check page layout, browser console,
network requests, mobile behavior, and Adsterra reporting before adding more
zones. Popunder and SocialBar are more intrusive; enable them only after reviewing
visitor experience and applicable policies. A Smartlink should be a deliberate
user-facing link, not an automatic redirect.

## Verification checklist

1. Confirm the website is approved and the zone is active in Adsterra.
2. Verify the exact script URL and zone key against the dashboard.
3. Build the web portal and check for JSX/build errors.
4. Open the homepage on desktop and mobile and inspect the ad container.
5. Check DevTools Network and Console for script failures or unexpected redirects.
6. Confirm privacy disclosures and consent behavior are appropriate for the site's
   visitors and applicable requirements.
7. Confirm impressions and revenue in Adsterra reporting after legitimate traffic.

Do not click your own ads or generate artificial traffic to test revenue.
