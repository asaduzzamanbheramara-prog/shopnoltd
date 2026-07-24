#!/usr/bin/env bash
# setup-branding-assets.sh — generate placeholder brand assets for shopnoltd
set -euo pipefail
ASSET_DIR="/mnt/c/Users/asadu/PROJECTS/shopnoltd/branding/assets"
mkdir -p "$ASSET_DIR"

PRIMARY="#5B21B6"     # purple
SECONDARY="#06B6D4"   # cyan
ACCENT="#F59E0B"      # amber

# Check imagemagick
if ! command -v convert >/dev/null 2>&1; then
  echo "ImageMagick not found. Installing..."
  sudo apt-get update -y && sudo apt-get install -y imagemagick
fi

# Generate main logo (512x512)
convert -size 512x512 \
  -define gradient:angle=135 \
  gradient:"$PRIMARY"-"$SECONDARY" \
  -gravity center -pointsize 64 -fill white -font DejaVu-Sans-Bold \
  -annotate +0+0 "shopnoltd" \
  -bordercolor "$ACCENT" -border 16 \
  "$ASSET_DIR/shopnoltd-logo.png"

# Smaller variants
convert "$ASSET_DIR/shopnoltd-logo.png" -resize 192x192 "$ASSET_DIR/shopnoltd-logo-192.png"
convert "$ASSET_DIR/shopnoltd-logo.png" -resize 96x96   "$ASSET_DIR/shopnoltd-logo-96.png"
convert "$ASSET_DIR/shopnoltd-logo.png" -resize 48x48   "$ASSET_DIR/shopnoltd-logo-48.png"

# favicon
convert "$ASSET_DIR/shopnoltd-logo-48.png" "$ASSET_DIR/favicon.ico"

# Windows .ico (multi-size)
convert "$ASSET_DIR/shopnoltd-logo-48.png" \
        "$ASSET_DIR/shopnoltd-logo-96.png" \
        "$ASSET_DIR/shopnoltd-logo-192.png" \
        "$ASSET_DIR/shopnoltd.ico"

# Android adaptive icon
convert -size 108x108 xc:"$PRIMARY" "$ASSET_DIR/ic_launcher_background.png"
convert "$ASSET_DIR/shopnoltd-logo-192.png" -resize 72x72 \
  -background none -gravity center -extent 108x108 \
  "$ASSET_DIR/ic_launcher_foreground.png"

echo "Generated brand assets:"
ls -lh "$ASSET_DIR"
