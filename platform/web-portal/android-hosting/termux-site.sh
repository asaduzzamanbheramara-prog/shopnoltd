#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
SITE_DIR="$HOME_DIR/www/shopnoltd"
RELEASES_DIR="$SITE_DIR/releases"
CONFIG_DIR="$HOME_DIR/.config/shopnoltd"
STATE_DIR="$HOME_DIR/.local/state/shopnoltd-nginx"
NGINX_CONF="$CONFIG_DIR/nginx.conf"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CONFIG="$SCRIPT_DIR/nginx.conf"

usage() {
  cat <<'USAGE'
Usage:
  termux-site.sh deploy /path/to/built-dist
  termux-site.sh start
  termux-site.sh stop
  termux-site.sh status

Run inside Termux. The deploy source must be a Vite dist directory
containing index.html and built assets. Nginx listens on 127.0.0.1:8080 only.
USAGE
}

require_nginx() {
  command -v nginx >/dev/null 2>&1 || {
    echo "nginx is not installed. Run: pkg install nginx" >&2
    exit 1
  }
}

prepare() {
  mkdir -p "$RELEASES_DIR" "$CONFIG_DIR" "$STATE_DIR"
  if [[ ! -f "$NGINX_CONF" ]]; then
    cp "$SOURCE_CONFIG" "$NGINX_CONF"
  fi
}

deploy() {
  local source="${1:-}"
  [[ -n "$source" && -d "$source" && -f "$source/index.html" ]] || {
    echo "ERROR: provide a dist directory containing index.html." >&2
    usage
    exit 2
  }

  prepare
  local release
  release="$(date +%Y%m%d-%H%M%S)"
  local target="$RELEASES_DIR/$release"
  mkdir -p "$target"
  cp -R "$source"/. "$target"/

  # Verify a complete release before changing the active symlink.
  test -s "$target/index.html"
  local temporary_link="$SITE_DIR/.current-$release"
  ln -s "$target" "$temporary_link"
  if [[ -e "$SITE_DIR/current" || -L "$SITE_DIR/current" ]]; then
    mv -Tf "$temporary_link" "$SITE_DIR/current"
  else
    mv "$temporary_link" "$SITE_DIR/current"
  fi

  require_nginx
  nginx -t -c "$NGINX_CONF" -p "$STATE_DIR/"
  echo "Deployed release: $release"
  start
}

start() {
  prepare
  require_nginx
  [[ -f "$SITE_DIR/current/index.html" ]] || {
    echo "No deployed site. Run deploy first." >&2
    exit 1
  }
  nginx -t -c "$NGINX_CONF" -p "$STATE_DIR/"
  if nginx -c "$NGINX_CONF" -p "$STATE_DIR/" 2>/dev/null; then
    echo "Nginx start requested. Local origin: http://127.0.0.1:8080"
  else
    echo "Nginx may already be running; checking health."
  fi
  sleep 1
  curl --fail --silent http://127.0.0.1:8080/healthz >/dev/null
  echo "Health check: OK"
}

stop() {
  require_nginx
  if [[ -f "$STATE_DIR/nginx.pid" ]]; then
    nginx -s quit -c "$NGINX_CONF" -p "$STATE_DIR/"
    echo "Nginx stop requested."
  else
    echo "Nginx is not running."
  fi
}

status() {
  if [[ -L "$SITE_DIR/current" && -f "$SITE_DIR/current/index.html" ]]; then
    echo "Active release: $(readlink -f "$SITE_DIR/current")"
  else
    echo "No active release."
  fi
  if curl --fail --silent http://127.0.0.1:8080/healthz >/dev/null 2>&1; then
    echo "Origin: healthy at 127.0.0.1:8080"
  else
    echo "Origin: not responding"
  fi
}

case "${1:-}" in
  deploy) shift; deploy "${1:-}" ;;
  start) start ;;
  stop) stop ;;
  status) status ;;
  *) usage; exit 2 ;;
esac
