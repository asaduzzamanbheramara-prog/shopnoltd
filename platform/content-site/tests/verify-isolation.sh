#!/bin/sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
html="$root/public/index.html"
nginx="$root/nginx.conf"
! grep -Eiq 'monetag|nap5k\.com|n6wxm\.com|12129960|12128278|12288239' "$html"
! grep -Eiq '<script|serviceWorker|navigator\.serviceWorker|shopno_token|/api/v[0-9]+' "$html"
grep -q 'location = /sw.js { return 404; }' "$nginx"
grep -q 'location / { try_files \$uri \$uri/ =404; }' "$nginx"
echo "content-site isolation checks passed"
