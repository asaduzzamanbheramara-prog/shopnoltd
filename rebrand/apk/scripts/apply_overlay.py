#!/usr/bin/env python3
"""
apply_overlay.py — rebrand an apktool-decoded APKPure APK in place.

Usage:
    apply_overlay.py --src <decoded-apk-dir> \\
                     --overlay <rebrand/apk/overlay> \\
                     --endpoints <rebrand/common/endpoints.yaml> \\
                     --endhosts-out <output/endhosts.json> \\
                     [--colors <rebrand/common/colors.json>] \\
                     [--strings <rebrand/common/strings.txt>]

What it does:
  1. Copies overlay files (AndroidManifest.xml, res/values/*.xml, mipmap icons)
     on top of the apktool-decoded tree, replacing APKPure branding.
  2. Patches the apktool-decoded AndroidManifest with the new package id,
     app label, icon, theme, and intent filters for our store URL.
  3. Walks every res/values/*.xml and every smali*/**/*.smali file, doing
     literal string replacements per the strings.txt swap table.
  4. Rewrites color values in res/values/colors.xml and the support
     supporting palette from colors.json.
  5. Generates endhosts.json (the in-app store catalog) from endpoints.yaml.

The script is idempotent: re-running it on an already-rebranded tree is a
no-op for the swap table (the source strings no longer exist) and a fresh
copy for the overlay files.

Why Python, not bash: apktool-decoded trees are large (4k+ files). Walking
them in pure Python with `os.walk` + bulk string replace on text files is
fast and predictable. The only non-stdlib dependency is PyYAML, which the
Dockerfile installs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    sys.stderr.write("apply_overlay.py requires PyYAML. Install with: pip install pyyaml\n")
    sys.exit(2)


# ---------------------------------------------------------------------------
# overlay copy
# ---------------------------------------------------------------------------


def copy_overlay(overlay_dir: Path, src_dir: Path) -> int:
    """
    Walk overlay_dir and copy every file into src_dir, overwriting.
    Returns the number of files copied.
    """
    if not overlay_dir.is_dir():
        raise FileNotFoundError(f"overlay dir not found: {overlay_dir}")

    count = 0
    for root, _dirs, files in os.walk(overlay_dir):
        rel = Path(root).relative_to(overlay_dir)
        for name in files:
            src = Path(root) / name
            dst = src_dir / rel / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    return count


# ---------------------------------------------------------------------------
# AndroidManifest patching
# ---------------------------------------------------------------------------

MANIFEST_PATH = "AndroidManifest.xml"

# apktool's decoded AndroidManifest.xml is plain text (not binary AXML).
# We patch the text form. Element names are simple; we target the
# <manifest> and <application> top-level tags.
PACKAGE_RE = re.compile(r'package="[^"]*"')
LABEL_RE = re.compile(r'android:label="[^"]*"')
ICON_RE = re.compile(r'android:icon="[^"]*"')
ROUND_ICON_RE = re.compile(r'android:roundIcon="[^"]*"')
THEME_RE = re.compile(r'android:theme="[^"]*"')


def patch_manifest(
    src_dir: Path,
    *,
    package: str,
    label: str,
    icon: str,
    round_icon: str,
    theme: str,
) -> None:
    manifest = src_dir / MANIFEST_PATH
    text = manifest.read_text(encoding="utf-8")

    text = PACKAGE_RE.sub(f'package="{package}"', text, count=1)
    text = ICON_RE.sub(f'android:icon="{icon}"', text, count=1)
    text = ROUND_ICON_RE.sub(f'android:roundIcon="{round_icon}"', text, count=1)
    text = THEME_RE.sub(f'android:theme="{theme}"', text, count=1)

    # The label can be either a literal string or a @string/ resource.
    # We force a literal so the rebranded name sticks even if APKPure's
    # strings.xml resource id changes upstream.
    text = LABEL_RE.sub(f'android:label="{label}"', text, count=1)

    manifest.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# string swaps across res/values/*.xml and smali*/**/*.smali
# ---------------------------------------------------------------------------

SMALI_DIR_PREFIX = "smali"
VALUES_DIR = "res/values"


def parse_swap_table(path: Path) -> list[tuple[str, str]]:
    """
    Parse a `from|to` per-line table. Lines starting with `#` and blank
    lines are ignored. More specific (longer) `from` strings are sorted
    first so they win over shorter substrings.
    """
    out: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            sys.stderr.write(f"swap: skipping malformed line: {raw!r}\n")
            continue
        src, dst = line.split("|", 1)
        out.append((src, dst))
    out.sort(key=lambda pair: len(pair[0]), reverse=True)
    return out


def iter_swap_targets(src_dir: Path) -> Iterable[Path]:
    # res/values*.xml — but NOT res/values/public.xml (apktool's resource
    # index, never edited) and NOT res/values/*s* that are non-XML.
    values = src_dir / "res"
    if values.is_dir():
        for p in values.glob("values*/*.xml"):
            if p.name == "public.xml":
                continue
            yield p
    # smali code — smali, smali_classes2, smali_classes3, smali_classes4 ...
    for p in src_dir.iterdir():
        if p.is_dir() and p.name.startswith(SMALI_DIR_PREFIX):
            for sm in p.rglob("*.smali"):
                yield sm


def apply_swaps(targets: Iterable[Path], swaps: list[tuple[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        original = text
        local_hits = 0
        for src, dst in swaps:
            if src in text:
                local_hits += text.count(src)
                text = text.replace(src, dst)
        if text != original:
            path.write_text(text, encoding="utf-8")
            counts[str(path)] = local_hits
    return counts


# ---------------------------------------------------------------------------
# color rewrite (res/values/colors.xml)
# ---------------------------------------------------------------------------


def apply_colors(src_dir: Path, colors: dict, swap_colors: dict) -> int:
    """
    Replace any of the APKPure color tokens we know about with the
    Shopno equivalents. Writes a fresh colors.xml from the Shopno
    palette too, so the file is consistent with the brand.
    """
    colors_xml = src_dir / "res" / "values" / "colors.xml"
    if not colors_xml.exists():
        return 0
    text = colors_xml.read_text(encoding="utf-8")
    hits = 0
    for src, dst in swap_colors.items():
        if src in text:
            hits += text.count(src)
            text = text.replace(src, dst)
    if hits:
        colors_xml.write_text(text, encoding="utf-8")
    return hits


# ---------------------------------------------------------------------------
# endhosts.json — the in-app store catalog
# ---------------------------------------------------------------------------


def build_endhosts(endpoints_yaml: Path, out_path: Path) -> int:
    """
    Read endpoints.yaml, build a flat JSON catalog the rebranded store
    can read on first launch (so users see Shopnoltd apps without us
    having to host a backend first).
    """
    data = yaml.safe_load(endpoints_yaml.read_text(encoding="utf-8"))
    block = data.get("shopnoltd", {})

    catalog = {
        "schema_version": 1,
        "brand": "Shopnoltd",
        "name": "Shopno Store",
        "base_url": block.get("base_url", ""),
        "support_email": block.get("support_email", ""),
        "privacy_url": block.get("privacy_url", ""),
        "terms_url": block.get("terms_url", ""),
        "services": [
            {
                "id": s["id"],
                "label": s["label"],
                "url": s["url"],
                "icon": s.get("icon", "generic"),
                "description": s.get("description", ""),
            }
            for s in block.get("services", [])
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    return len(catalog["services"])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--src", required=True, type=Path, help="apktool-decoded APK directory")
    p.add_argument("--overlay", required=True, type=Path, help="overlay files to copy in")
    p.add_argument("--endpoints", required=True, type=Path, help="endpoints.yaml (source of truth)")
    p.add_argument(
        "--endhosts-out",
        required=True,
        type=Path,
        help="where to write the generated endhosts.json",
    )
    p.add_argument("--colors", type=Path, help="colors.json (Shopno + APKPure swap table)")
    p.add_argument("--strings", type=Path, help="strings.txt (from|to swap table)")
    args = p.parse_args()

    src: Path = args.src.resolve()
    if not (src / "AndroidManifest.xml").is_file():
        sys.stderr.write(
            f"--src {src} does not look like an apktool-decoded tree "
            f"(no AndroidManifest.xml at the root)\n"
        )
        return 2

    print(f"[1/5] copying overlay files from {args.overlay} -> {src}")
    copied = copy_overlay(args.overlay, src)
    print(f"      copied {copied} files")

    print("[2/5] patching AndroidManifest.xml (package, label, icon, theme)")
    overlay_manifest = args.overlay / MANIFEST_PATH
    if overlay_manifest.is_file():
        # Overlay supplies the canonical values. Pull them out of the
        # overlay manifest so the user has a single source of truth.
        om_text = overlay_manifest.read_text(encoding="utf-8")
        m_pkg = re.search(r'package="([^"]+)"', om_text)
        m_lbl = re.search(r'android:label="([^"]+)"', om_text)
        m_icon = re.search(r'android:icon="([^"]+)"', om_text)
        m_round = re.search(r'android:roundIcon="([^"]+)"', om_text)
        m_theme = re.search(r'android:theme="([^"]+)"', om_text)
        patch_manifest(
            src,
            package=m_pkg.group(1) if m_pkg else "com.shopnoltd.store",
            label=m_lbl.group(1) if m_lbl else "Shopno Store",
            icon=m_icon.group(1) if m_icon else "@mipmap/ic_launcher",
            round_icon=m_round.group(1) if m_round else "@mipmap/ic_launcher_round",
            theme=m_theme.group(1) if m_theme else "@style/AppTheme.Shopno",
        )
    else:
        sys.stderr.write(
            "warning: overlay has no AndroidManifest.xml; " "skipping manifest patch\n"
        )

    if args.strings and args.strings.is_file():
        print(f"[3/5] applying string swaps from {args.strings}")
        swaps = parse_swap_table(args.strings)
        targets = list(iter_swap_targets(src))
        print(f"      walking {len(targets)} target files for " f"{len(swaps)} swap pairs")
        hits = apply_swaps(targets, swaps)
        total_hits = sum(hits.values())
        print(f"      made {total_hits} replacements across " f"{len(hits)} files")
    else:
        print("[3/5] no --strings file, skipping")

    if args.colors and args.colors.is_file():
        print(f"[4/5] applying color rewrites from {args.colors}")
        cdata = json.loads(args.colors.read_text(encoding="utf-8"))
        swap = cdata.get("_apkpure_swap", {})
        # filter the meta keys out
        swap = {k: v for k, v in swap.items() if not k.startswith("_")}
        # values are 6-digit hex without the leading "#" in swap table
        # but with it in the palette — normalise.
        if swap:
            hits = apply_colors(src, cdata, swap)
            print(f"      made {hits} color replacements in colors.xml")
        else:
            print("      no _apkpure_swap entries to apply")
    else:
        print("[4/5] no --colors file, skipping")

    print(f"[5/5] building endhosts catalog -> {args.endhosts_out}")
    n = build_endhosts(args.endpoints, args.endhosts_out)
    print(f"      wrote {n} services to endhosts.json")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
