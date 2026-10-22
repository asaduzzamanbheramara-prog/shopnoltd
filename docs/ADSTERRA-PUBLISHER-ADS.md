# Adsterra Publisher Ads

## Current integration

The public Shopnoltd homepage integrates the ten publisher units supplied for
website `shopnoltd.dpdns.org`:

- 300x250 display banner
- Responsive display banner: 320x50 on narrow screens, 468x60 on medium screens,
  and 728x90 on wide screens (one of these loads per viewport)
- 160x300 and 160x600 display banners
- Native banner
- Popunder
- Social Bar
- Smartlink, displayed as an explicitly labelled sponsored link

The standard display snippets share the global `window.atOptions` variable.
`src/components/AdsterraAds.jsx` serializes their script loading so a zone's
configuration is not overwritten by another zone before its script executes.
The existing `AdsterraBanner.jsx` component retains the original homepage
300x250 placement and delegates to this loader.

Popunder and Social Bar scripts are loaded from the homepage. They can affect
visitor experience; monitor frequency, mobile behavior, browser console, and
Adsterra's policy requirements. The Smartlink is a deliberate user action and
is not an automatic redirect.

## Publisher-provided hosts and keys

The supplied code uses `afders.org`, `arwf.org`, and `bicea.org`. These are
the exact hosts supplied in the publisher snippets. Confirm in the official
Adsterra dashboard that each host and key matches the intended active unit
before release. Do not substitute hosts or keys without publisher confirmation.

## Release verification

1. Confirm the website is approved and each zone is active in Adsterra.
2. Confirm all keys and URLs match the publisher dashboard.
3. Run the web portal production build and public-route prerender.
4. Check desktop and mobile layouts, including the responsive banner selection.
5. In DevTools, verify each expected request and check Console for errors.
6. Review privacy disclosures and consent requirements for the visitors served.
7. Confirm impressions and revenue in Adsterra reporting after legitimate traffic.

An active unit or successful script request does not guarantee an ad impression
or revenue. Do not click your own ads or generate artificial traffic to test
earnings.
