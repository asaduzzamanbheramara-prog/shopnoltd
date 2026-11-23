# Adsterra Publisher Ads

## Current publisher status

The Adsterra dashboard evidence supplied on 2026-11-23 shows website
`shopnoltd.dpdns.org` (website ID `6138776`) as **Approved**.

The dashboard lists these website units:

| Unit | ID | Dashboard status |
|---|---:|---|
| Smartlink_1 | 31843290 | Inactive |
| Popunder_1 | 31843289 | Inactive |
| SocialBar_1 | 31843291 | Inactive |
| NativeBanner_1 | 31843292 | Active |
| Banner 468x60 | 31843293 | Active |
| Banner 160x300 | 31843294 | Active |
| Banner 320x50 | 31843295 | Active |
| Banner 728x90 | 31843296 | Active |
| Banner 160x600 | 31843297 | Active |
| Banner 300x250 | 31843298 | Active |

A separate standalone Smartlink, `Smartlink_1` ID `31843363`, was shown as
**Active** on the Smartlinks dashboard. Its owner-supplied destination is
`https://asiafilm.org/4/bd6b0eff0d812e506d7bb51d544a1f92`. It is presented as
an explicit user-click sponsored link behind advertising consent and the
exact-host policy. Do not confuse this standalone Smartlink with the inactive
website ad unit `31843290`.

## Website placements in code

The supplied publisher snippets for the six display banners and the Native
Banner match the zone keys, dimensions, script URLs, and native container
configured in `src/components/AdsterraAds.jsx`.

The standard display snippets share the global `window.atOptions` variable.
The component serializes their script loading so a zone's configuration is not
overwritten by another zone before its script executes. The existing
`AdsterraBanner.jsx` component retains the homepage 300x250 placement and
delegates to this loader. Responsive banner selection uses 320x50, 468x60, or
728x90 based on viewport width; 160x300 and 160x600 are additional placements.

The website Smartlink, Popunder, and Social Bar units are currently inactive
according to the supplied dashboard. Do not represent them as active or
expect delivery from them. The old, unverified Social Bar script URL has been
removed from automatic loading; the Adsterra integration remains in place for
verified placements. Restore Social Bar only after unit `31843291` is activated
and its current GET CODE snippet is supplied. The Popunder must not be enabled
while Google AdSense is present unless the relevant publisher policies
explicitly permit the combined experience.

## Consent and policy gates

Optional Adsterra scripts and the standalone sponsored link are gated by
advertising consent and the public exact-host ad policy. Sensitive account,
authentication, administrative, wallet, payment, checkout, and billing routes
must remain excluded. Do not bypass consent or host policy to force ad loading.

## Release verification

1. Confirm the website is approved and each intended zone is active in Adsterra.
2. Confirm all keys and URLs match the current publisher dashboard snippets.
3. Run the web portal production build and public-route tests.
4. Check desktop and mobile layouts, including responsive banner selection.
5. In DevTools, verify expected requests and check Console for errors.
6. Review privacy disclosures, consent requirements, and network policies.
7. Confirm impressions and revenue in Adsterra reporting after legitimate traffic.

An active unit or successful script request does not guarantee an ad impression
or revenue. Do not click your own ads or generate artificial traffic to test
earnings.
