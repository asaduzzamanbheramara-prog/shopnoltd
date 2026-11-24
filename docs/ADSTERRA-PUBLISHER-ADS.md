# Adsterra Publisher Ads

## Current integration

The public Shopnoltd homepage loads **one Adsterra 300x250 display banner**,
only after a visitor opts into advertising consent.

Other formats are disabled in the web portal:
- Native banner
- Popunder
- Social Bar
- Smartlink
- Alternate display sizes (468x60, 320x50, 728x90, 160x300, 160x600)

The standard display snippet uses the publisher's `window.atOptions` global.
The web portal serializes script loading and keeps the original homepage
300x250 placement.

## Publisher-provided host and key

The configured banner uses the publisher-provided `bicea.org` host and the
300x250 zone key. Confirm the exact host and key in the official Adsterra
dashboard before release. Do not substitute a host or key without publisher
confirmation.

## Release verification

1. Confirm the website is approved and the 300x250 zone is active in Adsterra.
2. Confirm the key and script URL match the publisher dashboard.
3. Run the web portal production build and public-route prerender.
4. Check desktop and mobile layout, browser console, and Network requests.
5. Confirm the banner script is absent until advertising consent is granted.
6. Review privacy disclosures and consent requirements.
7. Confirm impressions and revenue in Adsterra reporting after legitimate traffic.

An active unit or successful script request does not guarantee an ad impression
or revenue. Do not click your own ads or generate artificial traffic to test
earnings.
