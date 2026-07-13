#!/usr/bin/env bash
# rebrand/apk/build.sh
#
# Build a rebranded Shopno Store APK from the upstream APKPure binary.
# Runs inside the rebrand/Dockerfile container.
#
# Required env:
#   SRC_APK     absolute path to the source APKPure binary
#   OUT_DIR     absolute path to the build output dir
#   VERSION     rebrand version, e.g. "0.1.0"
#
# Optional env:
#   KEYSTORE_JKS   path to an existing keystore (else a fresh one is generated)
#   KEYSTORE_PASS  keystore password
#   KEY_ALIAS      key alias
#   KEY_PASS       key password
#   STRIP_NATIVE   if "1", remove libpglarmor*/libnllvm*.so from the
#                  apktool-decoded tree before rebuilding (mitigates the
#                  APKPure anti-tamper crash on rebrand)
set -euo pipefail

: "${SRC_APK:?SRC_APK is required}"
: "${OUT_DIR:?OUT_DIR is required}"
: "${VERSION:?VERSION is required}"

REPO_ROOT="${REPO_ROOT:-/work/repo}"
REBRAND_DIR="$REPO_ROOT/rebrand"
COMMON_DIR="$REBRAND_DIR/common"
APK_DIR="$REBRAND_DIR/apk"
SCRIPTS_DIR="$APK_DIR/scripts"

# Make sure we're in the right relative layout.
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# 1. Fresh output directory.
# ---------------------------------------------------------------------------
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
WORK="$OUT_DIR/work"
mkdir -p "$WORK"
DECODED="$WORK/decoded"

# ---------------------------------------------------------------------------
# 2. apktool decode the source APK.
# ---------------------------------------------------------------------------
echo "::group::apktool d $SRC_APK -> $DECODED"
apktool d -f -o "$DECODED" "$SRC_APK"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 3. Optional: strip the anti-tamper native libs.
# ---------------------------------------------------------------------------
if [[ "${STRIP_NATIVE:-0}" == "1" ]]; then
    echo "::group::stripping APKPure anti-tamper native libs"
    find "$DECODED/lib" -type f \( \
        -name 'libpglarmor*' -o \
        -name 'libnllvm*' -o \
        -name 'libbugly*' -o \
        -name 'libmtpencrypt*' -o \
        -name 'libhttpdns*' -o \
        -name 'libapminsight*' -o \
        -name 'libhuyaostar*' -o \
        -name 'libdeflater7z*' \
    \) -print -delete
    echo "::endgroup::"
fi

# ---------------------------------------------------------------------------
# 4. Bake endhosts.json into the APK's assets/ directory.
# ---------------------------------------------------------------------------
echo "::group::baking endhosts.json into assets/"
mkdir -p "$DECODED/assets"
cp "$APK_DIR/overlay/endhosts.json" "$DECODED/assets/endhosts.json"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 5. apply_overlay.py: copy overlay files in, patch manifest, swap strings.
# ---------------------------------------------------------------------------
ENDHOSTS_OUT="$APK_DIR/overlay/endhosts.json"
echo "::group::running apply_overlay.py"
python3 "$SCRIPTS_DIR/apply_overlay.py" \
    --src        "$DECODED" \
    --overlay    "$APK_DIR/overlay" \
    --endpoints  "$COMMON_DIR/endpoints.yaml" \
    --endhosts-out "$ENDHOSTS_OUT" \
    --colors     "$COMMON_DIR/colors.json" \
    --strings    "$COMMON_DIR/strings.txt"
# Re-copy the freshly-generated endhosts.json into assets/.
cp "$ENDHOSTS_OUT" "$DECODED/assets/endhosts.json"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 6. apktool b: rebuild.
# ---------------------------------------------------------------------------
echo "::group::apktool b"
apktool b "$DECODED" -o "$WORK/unsigned.apk"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 7. zipalign.
# ---------------------------------------------------------------------------
echo "::group::zipalign"
zipalign -p -f 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 8. apksigner sign.
# ---------------------------------------------------------------------------
KEYSTORE_JKS="${KEYSTORE_JKS:-$WORK/shopno-release.jks}"
KEYSTORE_PASS="${KEYSTORE_PASS:-shopno-release-pass}"
KEY_ALIAS="${KEY_ALIAS:-shopno}"
KEY_PASS="${KEY_PASS:-shopno-release-pass}"
KEY_VALIDITY_DAYS="${KEY_VALIDITY_DAYS:-36500}"  # 100 years

if [[ ! -f "$KEYSTORE_JKS" ]]; then
    echo "::group::generating release keystore at $KEYSTORE_JKS"
    keytool -genkey -v \
        -keystore "$KEYSTORE_JKS" \
        -storepass "$KEYSTORE_PASS" \
        -keypass "$KEY_PASS" \
        -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 4096 \
        -validity "$KEY_VALIDITY_DAYS" \
        -dname "CN=Shopnoltd Ltd, O=Shopnoltd, L=Dhaka, ST=Dhaka, C=BD"
    echo "::endgroup::"
    echo "::notice::Fresh keystore generated. To make future rebrand runs"
    echo "::notice::sign with the same key, back it up to the"
    echo "::notice::RELEASE_KEYSTORE secret in your repo settings."
    if [[ -n "${RELEASE_KEYSTORE_B64_OUT:-}" ]]; then
        base64 -w0 "$KEYSTORE_JKS" > "$RELEASE_KEYSTORE_B64_OUT"
        echo "::notice::Keystore base64 written to $RELEASE_KEYSTORE_B64_OUT"
    fi
fi

echo "::group::apksigner sign"
OUT_APK="$OUT_DIR/ShopnoStore-$VERSION.apk"
apksigner sign \
    --ks "$KEYSTORE_JKS" \
    --ks-pass "pass:$KEYSTORE_PASS" \
    --key-pass "pass:$KEY_PASS" \
    --ks-key-alias "$KEY_ALIAS" \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    --out "$OUT_APK" \
    "$WORK/aligned.apk"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 9. Verify the signed APK.
# ---------------------------------------------------------------------------
echo "::group::apksigner verify --print-certs"
apksigner verify --verbose --print-certs "$OUT_APK"
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 10. Dump badging for the release notes.
# ---------------------------------------------------------------------------
echo "::group::aapt2 dump badging"
aapt2 dump badging "$OUT_APK" | head -40
echo "::endgroup::"

# ---------------------------------------------------------------------------
# 11. Print a JSON summary for the workflow to consume.
# ---------------------------------------------------------------------------
cat <<EOF | tee "$OUT_DIR/build-summary.json"
{
  "artifact": "$(basename "$OUT_APK")",
  "path":      "$OUT_APK",
  "size":      $(stat -c%s "$OUT_APK"),
  "version":   "$VERSION",
  "keystore":  "$KEYSTORE_JKS",
  "strip_native": ${STRIP_NATIVE:-0}
}
EOF

echo "OK: built $OUT_APK"
