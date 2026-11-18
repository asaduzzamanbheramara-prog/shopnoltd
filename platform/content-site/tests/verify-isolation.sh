#!/bin/sh
set -eux
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
html="$root/public/index.html"
app="$root/public/app.js"
ipp="$root/public/monetag-ipp-test.js"
nginx="$root/nginx.conf"
! grep -Eiq 'monetag|nap5k\.com|n6wxm\.com|12129960|12128278|12288239' "$app"
grep -q '<script src="/app.js" defer></script>' "$html"
grep -q '<script src="/monetag-ipp-test.js" defer></script>' "$html"
! grep -Eiq "<script[^>]+src=[\"']https?://" "$html"
grep -q "location.hostname !== host" "$ipp"
grep -q "monetag-test.*!== '1'" "$ipp"
grep -Fq 'blog\\/[^/]+$/.test(path)' "$ipp"
grep -q "root.querySelector('.article')" "$ipp"
grep -q "script.dataset.zone = '12129960'" "$ipp"
grep -q "script.setAttribute('data-cfasync', 'false')" "$ipp"
grep -q "https://nap5k.com/tag.min.js" "$ipp"
! grep -Eiq '12128278|12288239|n6wxm\.com|serviceWorker|navigator\.serviceWorker' "$html" "$app" "$ipp"
grep -q "script-src 'self' https://nap5k.com" "$nginx"
grep -q 'location = /sw.js { return 404; }' "$nginx"
grep -q 'limit_except GET HEAD { deny all; }' "$nginx"
test "$(grep -c 'limit_except GET HEAD { deny all; }' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Authorization "";' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Cookie "";' "$nginx")" -eq 2
test "$(grep -c 'proxy_hide_header Set-Cookie;' "$nginx")" -eq 2
grep -Fq 'blog\\/[^/]+$/.test(path)' "$ipp"
grep -q 'frame-src https://www.youtube-nocookie.com' "$nginx"
grep -Fq 'blog\\/[^/]+$/.test(path)' "$ipp"
grep -Fq 'location / { try_files $uri $uri/ =404; }' "$nginx"
grep -q 'function youtubeId' "$app"
grep -q 'credentials:' "$app"
echo "content-site isolation, gated IPP, GET-only API proxy, and editorial media checks passed"
