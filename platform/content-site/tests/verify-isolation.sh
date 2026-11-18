#!/bin/sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
html="$root/public/index.html"
app="$root/public/app.js"
nginx="$root/nginx.conf"
! grep -Eiq 'monetag|nap5k\.com|n6wxm\.com|12129960|12128278|12288239' "$html" "$app"
! grep -Eiq 'serviceWorker|navigator\.serviceWorker|shopno_token|/api/v[0-9]+/(users|payments|domains|wallet)' "$html" "$app"
grep -q '<script src="/app.js" defer></script>' "$html"
! grep -Eiq "<script[^>]+src=[\"']https?://" "$html"
grep -q 'location = /sw.js { return 404; }' "$nginx"
grep -q 'limit_except GET HEAD { deny all; }' "$nginx"
test "$(grep -c 'limit_except GET HEAD { deny all; }' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Authorization "";' "$nginx")" -eq 2
test "$(grep -c 'proxy_set_header Cookie "";' "$nginx")" -eq 2
test "$(grep -c 'proxy_hide_header Set-Cookie;' "$nginx")" -eq 2
grep -q 'proxy_pass https://api.shopnoltd.dpdns.org/api/v2/blog' "$nginx"
grep -q 'frame-src https://www.youtube-nocookie.com' "$nginx"
grep -Fq 'location ^~ /blog/ { try_files $uri /index.html; }' "$nginx"
grep -Fq 'location / { try_files $uri $uri/ =404; }' "$nginx"
grep -q 'function youtubeId' "$app"
grep -q 'credentials:' "$app"
echo "content-site isolation, GET-only API proxy, and editorial media checks passed"
