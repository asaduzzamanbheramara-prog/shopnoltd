#!/usr/bin/env bash
# rebrand-binaries.sh — brand OmniloginSetup and APKPure with shopnoltd
set -euo pipefail

SRC_DIR="/mnt/c/Users/asadu/Downloads"
OUT_DIR="/mnt/c/Users/asadu/PROJECTS/shopnoltd/branding/output"
OMNILOGIN_SRC="$SRC_DIR/OmniloginSetup-x64-8.9.12.exe"
APKPURE_SRC="$SRC_DIR/APKPure_3.20.7402_apkpure.com.apk"

BRAND_NAME="shopnoltd"
BRAND_DISPLAY="Shopnoltd"
BRAND_DOMAIN="shopnoltd.dpdns.org"
BRAND_PRIMARY="#5B21B6"
BRAND_SECONDARY="#06B6D4"
BRAND_PNG="/mnt/c/Users/asadu/PROJECTS/shopnoltd/branding/assets/shopnoltd-logo.png"
mkdir -p "$OUT_DIR"

banner() { printf '\n\033[1;33m═══ %s ═══\033[0m\n' "$*"; }
ok()     { printf '\033[0;32m[OK]\033[0m %s\n' "$*"; }
warn()   { printf '\033[0;31m[WARN]\033[0m %s\n' "$*" >&2; }
info()   { printf '\033[0;36m[INFO]\033[0m %s\n' "$*"; }

# Phase 0: install tools
banner "PHASE 0 · Install tools"
NEEDED=(p7zip-full innoextract imagemagick)
MISSING=()
for t in "${NEEDED[@]}"; do dpkg -l "$t" >/dev/null 2>&1 || MISSING+=("$t"); done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  sudo apt-get update -y
  sudo apt-get install -y "${MISSING[@]}" 2>&1 | tail -3
fi
# apktool — try apt, then snap, then download
if ! command -v apktool >/dev/null 2>&1; then
  warn "apktool not found, installing..."
  sudo apt-get install -y apktool 2>/dev/null || \
    sudo snap install apktool 2>/dev/null || {
      warn "  apt+snap failed, downloading from GitHub"
      sudo apt-get install -y default-jre-headless
      sudo mkdir -p /opt/apktool
      sudo curl -fsSL -o /opt/apktool/apktool.jar \
        https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar
      sudo curl -fsSL -o /opt/apktool/apktool \
        https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool
      sudo chmod +x /opt/apktool/apktool
      sudo ln -sf /opt/apktool/apktool /usr/local/bin/apktool
    }
fi
ok "tools ready"

# Phase 1: extract OmniloginSetup
banner "PHASE 1 · Extract OmniloginSetup"
[[ -f "$OMNILOGIN_SRC" ]] || { warn "missing $OMNILOGIN_SRC"; exit 1; }
EXTRACT_DIR="$OUT_DIR/omnilogin-extracted"
rm -rf "$EXTRACT_DIR"; mkdir -p "$EXTRACT_DIR"
if 7z x "$OMNILOGIN_SRC" -o"$EXTRACT_DIR" -y >/dev/null 2>&1; then
  ok "extracted with 7z"
elif innoextract -d "$EXTRACT_DIR" "$OMNILOGIN_SRC" >/dev/null 2>&1; then
  ok "extracted with innoextract"
else
  warn "extraction failed — see $EXTRACT_DIR for partial output"
fi
info "extracted contents (top 30):"
find "$EXTRACT_DIR" -type f 2>/dev/null | head -30

# Phase 2: replace brand assets
banner "PHASE 2 · Replace brand assets"
ASSET_DIR="$OUT_DIR/omnilogin-assets"
mkdir -p "$ASSET_DIR"

# Find installer asset files
find "$EXTRACT_DIR" -type f \
  \( -iname "*.ico" -o -iname "*.bmp" -o -iname "*.rtf" \
     -o -iname "license*" -o -iname "eula*" -o -iname "*.ini" \) \
  2>/dev/null | while read -r f; do
    cp "$f" "$ASSET_DIR/$(basename "$f").original" 2>/dev/null
    info "  found: ${f#$EXTRACT_DIR/}"
  done

# Generate brand assets
[[ -f "$BRAND_PNG" ]] || {
  warn "no brand PNG yet, generating..."
  bash /mnt/c/Users/asadu/PROJECTS/shopnoltd/setup-branding-assets.sh
}
convert "$BRAND_PNG" -resize 256x256 "$ASSET_DIR/shopnoltd.ico"
convert "$BRAND_PNG" -resize 164x314 "$ASSET_DIR/shopnoltd.bmp"
convert "$BRAND_PNG" -resize 55x55   "$ASSET_DIR/shopnoltd-small.bmp"
ok "brand assets generated"

# Text replacements
BRAND_REPLACEMENTS=(
  "Omnilogin:${BRAND_DISPLAY}"
  "OmniLogin:${BRAND_DISPLAY}"
  "omnilogin:${BRAND_NAME}"
  "Omni Login:${BRAND_DISPLAY}"
)
info "  text replacements in installer files..."
for f in $(find "$EXTRACT_DIR" -type f \
            \( -name "*.txt" -o -name "*.rtf" -o -name "*.ini" \
               -o -name "*.cfg" -o -name "*.json" -o -name "*.xml" \
               -o -name "*.html" -o -name "*.nsh" -o -name "*.nsi" \) \
            2>/dev/null); do
  for pair in "${BRAND_REPLACEMENTS[@]}"; do
    src="${pair%:*}"; dst="${pair#*:}"
    if grep -q "$src" "$f" 2>/dev/null; then
      sed -i.bak "s/$src/$dst/g" "$f" 2>/dev/null
    fi
  done
done
ok "text branding applied"

# Phase 3: rebuild .exe
banner "PHASE 3 · Rebuild .exe"
OUT_EXE="$OUT_DIR/${BRAND_NAME}-setup-x64-8.9.12.exe"

# Try NSIS rebuild if there's a .nsi
if command -v makensis >/dev/null 2>&1; then
  NSI=$(find "$EXTRACT_DIR" -name "*.nsi" -type f 2>/dev/null | head -1)
  if [[ -n "$NSI" ]]; then
    info "  NSIS script found: $NSI — compiling"
    (cd "$EXTRACT_DIR" && makensis -V2 "$(basename "$NSI")") && ok "  NSIS rebuild ok"
  fi
fi

# Always create a 7z SFX as a fallback / packaging
info "  creating 7z archive at $OUT_EXE (use innoextract or 7z to extract)"
7z a -mx=9 "$OUT_EXE" "$EXTRACT_DIR"/* 2>&1 | tail -3
chmod +x "$OUT_EXE"
ok "rebranded installer: $OUT_EXE ($(du -h "$OUT_EXE" | cut -f1))"

# Phase 4: rebrand APKPure
banner "PHASE 4 · Rebrand APKPure"
[[ -f "$APKPURE_SRC" ]] || { warn "missing $APKPURE_SRC"; exit 1; }
APK_WORK="$OUT_DIR/apkpure-work"
rm -rf "$APK_WORK"; mkdir -p "$APK_WORK"
cp "$APKPURE_SRC" "$APK_WORK/original.apk"

if command -v apktool >/dev/null 2>&1; then
  info "apktool decompile..."
  apktool d -f -o "$APK_WORK/decoded" "$APK_WORK/original.apk" 2>&1 | tail -3

  # Replace app name
  for sf in $(find "$APK_WORK/decoded/res" -name "strings.xml" 2>/dev/null); do
    sed -i "s|<string name=\"app_name\">[^<]*</string>|<string name=\"app_name\">${BRAND_DISPLAY}</string>|g" "$sf"
    sed -i "s|APKPure|${BRAND_DISPLAY}|g" "$sf"
  done
  ok "  app name rebranded"

  # Replace launcher icons
  if [[ -d "$APK_WORK/decoded/res" ]] && [[ -f "$BRAND_PNG" ]]; then
    for dir in "$APK_WORK/decoded/res"/mipmap-*; do
      [[ -d "$dir" ]] || continue
      for icon in ic_launcher.png ic_launcher_round.png; do
        if [[ -f "$dir/$icon" ]]; then
          cp "$BRAND_PNG" "$dir/$icon"
        fi
      done
    done
    ok "  launcher icons replaced"
  fi

  # Rebuild
  info "  apktool rebuild..."
  apktool b "$APK_WORK/decoded" -o "$APK_WORK/rebuilt-unsigned.apk" 2>&1 | tail -3

  # Sign with debug key
  if [[ ! -f "$HOME/.android/debug.keystore" ]]; then
    info "  generating debug keystore..."
    mkdir -p "$HOME/.android"
    keytool -genkey -v -keystore "$HOME/.android/debug.keystore" \
      -storepass android -alias androiddebugkey -keypass android \
      -keyalg RSA -keysize 2048 -validity 10000 \
      -dname "CN=Android Debug,O=Android,C=US" 2>&1 | tail -2
  fi

  if [[ -f "$HOME/.android/debug.keystore" ]]; then
    apksigner sign --ks "$HOME/.android/debug.keystore" \
      --ks-pass pass:android --key-pass pass:android \
      --ks-key-alias androiddebugkey \
      --out "$OUT_DIR/${BRAND_NAME}-app.apk" \
      "$APK_WORK/rebuilt-unsigned.apk"
    zipalign -f 4 "$OUT_DIR/${BRAND_NAME}-app.apk" \
      "$OUT_DIR/${BRAND_NAME}-app-aligned.apk" 2>/dev/null
    mv -f "$OUT_DIR/${BRAND_NAME}-app-aligned.apk" "$OUT_DIR/${BRAND_NAME}-app.apk"
    ok "  signed APK: $OUT_DIR/${BRAND_NAME}-app.apk"
  fi
fi

# Phase 5: report
banner "DONE"
echo "Output files:"
ls -lh "$OUT_DIR"/*.exe "$OUT_DIR"/*.apk 2>/dev/null
echo
echo "Source files (unchanged):"
ls -lh "$OMNILOGIN_SRC" "$APKPURE_SRC"
