# Adsterra Publisher Ads

## Enabled Adsterra formats

The Shopnoltd homepage supports the publisher's six display-banner zones:

| Size | Publisher zone key |
| --- | --- |
| 300x250 | `253592d9ff11f220f7c319ff3ec1bde2` |
| 728x90 | `8e53ca766e19e7f2777fbecab4ca6040` |
| 468x60 | `7747061d0c5ae776f68405dbeeab89fd` |
| 320x50 | `08bbf4b2a46b97a005c4d26ef1570b52` |
| 160x300 | `01485acb7eefc95c30f7e25fb2986c58` |
| 160x600 | `747cdd280fdc0b463f184d4662beaceb` |

Responsive placement selects 320x50 on narrow screens, 468x60 on medium screens,
and 728x90 on wide screens. The fixed 300x250 placement and two tall banner
zones are also available. The Native Banner, Social Bar, and Smartlink placements
use the publisher script/link values in `AdsterraAds.jsx`.

All placements require both advertising consent and the public server-side
Adsterra network/placement policy to be enabled. Policy failures fail closed.

## Popunder compatibility restriction

The Popunder zone (`https://afders.org/1/09836d27bc58347743587df99b0dfe7f`)
was present in historical integration code but was removed when Google AdSense
was active site-wide. Do not load Popunder while AdSense is present on the same
site; the two formats create a publisher-policy conflict. Re-enable Popunder
only after the owner deliberately switches off site-wide AdSense and verifies
current AdSense and Adsterra publisher terms.

## Release verification

1. Confirm every zone key and script URL in the official Adsterra dashboard.
2. Confirm the site is approved and each unit is active.
3. Confirm advertising consent is granted before any Adsterra request occurs.
4. Confirm the public ads API enables Adsterra for the requested placement.
5. Test desktop/mobile sizes, browser console, and Network requests.
6. Confirm no Popunder request occurs while AdSense is installed.
7. Review impressions and revenue using legitimate visitor traffic only.

A successful script request does not guarantee an ad impression or revenue. Never
click your own ads or generate artificial traffic to test earnings.
