#!/bin/sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
html="$root/public/index.html"
app="$root/public/app.js"
ipp="$root/public/monetag-loader.js"
nginx="$root/nginx.conf"

! grep -Eiq 'monetag|nap5k\.com|n6wxm\.com|12129960|12128278|12288239' "$app"
grep -q '<script src="/app.js" defer></script>' "$html"
grep -q '<script src="/monetag-loader.js" defer></script>' "$html"
! grep -Eiq "<script[^>]+src=[\"']https?://" "$html"

grep -q "location.hostname.toLowerCase() !== HOST" "$ipp"
grep -q "readConsent() !== true" "$ipp"
grep -q "policy?.networks?.monetag !== true" "$ipp"
grep -q "policy?.placements?.blog !== true" "$ipp"
grep -Fq 'blog\/[^/]+$/.test(path)' "$ipp"
grep -q "root.querySelector('.article')" "$ipp"
grep -q "script.dataset.zone = ZONE_ID" "$ipp"
grep -q "script.setAttribute('data-cfasync', 'false')" "$ipp"
grep -q "https://nap5k.com/tag.min.js" "$ipp"
! grep -Eiq '12128278|12288239|n6wxm\.com|serviceWorker|navigator\.serviceWorker' "$html" "$app" "$ipp"

grep -q "script-src 'self' https://nap5k.com" "$nginx"
grep -q 'location = /sw.js { return 404; }' "$nginx"
grep -q 'limit_except GET HEAD { deny all; }' "$nginx"
test "$(grep -c 'limit_except GET HEAD { deny all; }' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Authorization \"\";' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Cookie \"\";' "$nginx")" -eq 2
test "$(grep -c 'proxy_hide_header Set-Cookie;' "$nginx")" -eq 2
grep -q 'proxy_pass https://api.shopnoltd.dpdns.org/api/v2/blog' "$nginx"
grep -q 'frame-src https://www.youtube-nocookie.com' "$nginx"
grep -Fq 'location ^~ /blog/ { try_files $uri /index.html; }' "$nginx"
grep -Fq 'location / { try_files $uri $uri/ =404; }' "$nginx"
grep -q 'function youtubeId' "$app"
grep -q 'credentials:' "$app"

echo "content-site isolation, gated IPP, GET-only API proxy, and editorial media checks passed"
