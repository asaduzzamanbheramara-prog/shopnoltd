# APKPure anti-tamper smali patches

The upstream APKPure APK ships native libraries that perform runtime
integrity / signature checks. If a rebrand release crashes on first
launch with an "integrity check failed" or "signature mismatch" dialog,
the patches in this directory may be needed.

## Status: not currently applied

The rebrand ships **without** these patches. Status bar, store UI,
catalog browsing, and in-app downloads all work without them. The
integrity checks only gate:

- Crash reporting via Bugly
- Some anonymous analytics
- A few anti-piracy prompts

If a future rebrand needs the app to remain fully functional in the
background (e.g. for push notifications from Shopno Chat), apply the
patches below.

## How to apply (manual, when needed)

1. Open `apk-decoded/` in `jadx-gui` (or any smali editor) after
   `apktool d`.
2. Find the integrity-check entry point. As of APKPure 3.20.x, the
   native lib `libpglarmor.so` exports `Java_com_pgl_armor_NativePgl_*`
   methods called from smali at:
     `smali/com/pgl/armor/PglArmorImpl.smali`
3. Replace the return-value assignment in `verifyAppIntegrity` /
   `checkSignature` to `const/4 v0, 0x1` (success) instead of forwarding
   the native call's return.
4. Re-run `apktool b` → `zipalign` → `apksigner sign`.

## Other affected libs

| Native lib           | What it checks                | Patch? |
|----------------------|-------------------------------|--------|
| `libpglarmor.so`     | Package signature             | Yes    |
| `libmtpencrypt.so`   | TencentMTP device ID          | No — rebrand keeps this; Shopno doesn't care |
| `libbugly_*.so`      | Crash upload only             | Optional: drop the libs entirely (loses crash logs) |
| `libnllvm1630*.so`   | Anti-debug                    | Yes    |
| `libdeflater7z.so`   | 7z asset decompression        | No     |

Document the patch you apply here when you commit a rebrand that uses
them, so the next rebrand can decide whether to keep them.
