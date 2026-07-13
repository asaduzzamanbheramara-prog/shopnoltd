#!/usr/bin/env python3
"""
generate_icons.py — produce Shopno launcher icons for every Android density
and the EXE installer.

Usage (in CI / Docker):
    pip install cairosvg pillow
    python generate_icons.py --src ../../branding/shopnoapp-logo.svg \\
                             --out ../overlay/res

Outputs:
  mipmap-mdpi/ic_launcher.png             48x48
  mipmap-hdpi/ic_launcher.png             72x72
  mipmap-xhdpi/ic_launcher.png            96x96
  mipmap-xxhdpi/ic_launcher.png          144x144
  mipmap-xxxhdpi/ic_launcher.png        192x192
  mipmap-{dpi}/ic_launcher_round.png     same dimensions, rounded mask
  mipmap-anydpi-v26/ic_launcher.xml      adaptive-icon manifest
  mipmap-anydpi-v26/ic_launcher_round.xml
  drawable/ic_launcher_foreground.png    432x432 (for adaptive icon)
  drawable/ic_launcher_background.png    432x432
  mipmap-{dpi}/ic_launcher_foreground.png
  mipmap-{dpi}/ic_launcher_background.png
  ../overlay/exe/InstallHeader.bmp       150x57 (NSIS small installer header)
  ../overlay/exe/InstallSidebar.bmp      164x314 (NSIS sidebar)

If cairosvg / Pillow aren't available, the script falls back to a pure-stdlib
PNG writer that produces a flat Shopno-blue rounded square so the pipeline
still produces a valid (if boring) icon. The CI always installs the real
dependencies so the proper logo renders in production artifacts.
"""

from __future__ import annotations

import argparse
import io
import os
import struct
import sys
import zlib
from pathlib import Path

# Lazy imports — the fallback path uses only stdlib.
try:
    import cairosvg
except ImportError:
    cairosvg = None  # type: ignore[assignment]

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Icon density table — Android source: developer.android.com/training/
#   multiple-screens/screen-desities#density-independent-pixels
# ---------------------------------------------------------------------------
ANDROID_MIPMAP = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

ADAPTIVE_BG_SIZE = 432  # 432x432 is the Android adaptive-icon spec.

NSIS_HEADER_W,  NSIS_HEADER_H  = 150, 57
NSIS_SIDEBAR_W, NSIS_SIDEBAR_H = 164, 314

SHOPNO_BG    = (0x0B, 0x12, 0x20, 0xFF)  # navy
SHOPNO_BLUE  = (0x25, 0x63, 0xEB, 0xFF)
SHOPNO_SKY   = (0x38, 0xBD, 0xF8, 0xFF)
SHOPNO_WHITE = (0xFF, 0xFF, 0xFF, 0xFF)


# ---------------------------------------------------------------------------
# stdlib PNG writer — fallback when Pillow isn't installed.
# Supports RGBA 8-bit, the only mode we need.
# ---------------------------------------------------------------------------
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png_rgba(path: Path, width: int, height: int, pixels: bytes) -> None:
    """Write an RGBA 8-bit PNG. `pixels` is row-major, length w*h*4."""
    if len(pixels) != width * height * 4:
        raise ValueError(
            f"pixel buffer size mismatch: got {len(pixels)}, "
            f"expected {width*height*4}"
        )
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    # filter byte 0 (None) at the start of each scanline
    raw = b"".join(b"\x00" + pixels[y*width*4:(y+1)*width*4]
                   for y in range(height))
    idat = zlib.compress(raw, 9)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(sig)
        f.write(_png_chunk(b"IHDR", ihdr))
        f.write(_png_chunk(b"IDAT", idat))
        f.write(_png_chunk(b"IEND", b""))


def flat_rounded_square(size: int, fg: tuple, bg: tuple) -> bytes:
    """
    Produce a rounded-square RGBA buffer with a solid foreground fill on
    a transparent background. Used by the stdlib fallback.
    """
    px = bytearray(size * size * 4)
    # 22.37% corner radius (matches Material Design's recommended ratio).
    r = max(2, int(size * 0.2237))
    r_sq = r * r
    for y in range(size):
        for x in range(size):
            # corner centres
            inside = True
            if (x < r and y < r and
                    (r - x) ** 2 + (r - y) ** 2 > r_sq):
                inside = False
            elif (x >= size - r and y < r and
                  (x - (size - r - 1)) ** 2 + (r - y) ** 2 > r_sq):
                inside = False
            elif (x < r and y >= size - r and
                  (r - x) ** 2 + (y - (size - r - 1)) ** 2 > r_sq):
                inside = False
            elif (x >= size - r and y >= size - r and
                  (x - (size - r - 1)) ** 2 +
                  (y - (size - r - 1)) ** 2 > r_sq):
                inside = False
            if not inside:
                continue
            off = (y * size + x) * 4
            px[off:off+4] = bytes(fg)
    return bytes(px)


def flat_round_icon(size: int, fg: tuple) -> bytes:
    """RGBA buffer for a circular icon (used by ic_launcher_round)."""
    px = bytearray(size * size * 4)
    cx = cy = (size - 1) / 2.0
    r = cx
    for y in range(size):
        for x in range(size):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                off = (y * size + x) * 4
                px[off:off+4] = bytes(fg)
    return bytes(px)


def flat_bmp(width: int, height: int, fg: tuple, bg: tuple) -> bytes:
    """
    Minimal 24-bit BMP writer. NSIS only needs 24bpp BMPs for InstallHeader
    and InstallSidebar. Returns the encoded bytes.
    """
    row_pad = (4 - (width * 3) % 4) % 4
    row_size = width * 3 + row_pad
    pixel_data = bytearray()
    for y in range(height):
        for x in range(width):
            # gradient between two Shopno blues
            t = (x + y) / (width + height)
            r = int(fg[0] * (1 - t) + bg[0] * t)
            g = int(fg[1] * (1 - t) + bg[1] * t)
            b = int(fg[2] * (1 - t) + bg[2] * t)
            # BMP rows are bottom-up, BGR
            pixel_data += bytes([b, g, r])
        pixel_data += b"\x00" * row_pad
    file_size = 14 + 40 + len(pixel_data)
    bmp = bytearray()
    bmp += b"BM"
    bmp += struct.pack("<I", file_size)
    bmp += struct.pack("<HH", 0, 0)  # reserved
    bmp += struct.pack("<I", 14 + 40)  # pixel data offset
    bmp += struct.pack("<I", 40)       # DIB header size
    bmp += struct.pack("<i", width)
    bmp += struct.pack("<i", -height)  # negative => top-down rows
    bmp += struct.pack("<HH", 1, 24)   # planes, bpp
    bmp += struct.pack("<I", 0)        # compression = BI_RGB
    bmp += struct.pack("<I", len(pixel_data))
    bmp += struct.pack("<ii", 2835, 2835)  # ~72 DPI in pixels-per-metre
    bmp += struct.pack("<II", 0, 0)  # colours in palette
    bmp += bytes(pixel_data)
    return bytes(bmp)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def render_with_pillow(svg_path: Path, size: int) -> Image.Image:
    """Rasterize SVG to RGBA PIL Image at the given size."""
    if cairosvg is None or Image is None:
        raise RuntimeError("cairosvg + Pillow required for SVG rendering")
    png_bytes = cairosvg.svg2png(url=str(svg_path),
                                 output_width=size,
                                 output_height=size)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def apply_round_mask(img: Image.Image) -> Image.Image:
    """Circular alpha mask for ic_launcher_round."""
    size = img.size[0]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask=mask)
    return out


def save_pil_as_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


# ---------------------------------------------------------------------------
# per-icon generation
# ---------------------------------------------------------------------------
def generate_android_mipmaps(svg_path: Path, res_out: Path) -> list[Path]:
    """Generate ic_launcher.png + ic_launcher_round.png for every density."""
    outputs: list[Path] = []
    if cairosvg is not None and Image is not None:
        for folder, size in ANDROID_MIPMAP.items():
            base = render_with_pillow(svg_path, size)
            square = base.copy()
            rounded = apply_round_mask(base)
            sq_path = res_out / folder / "ic_launcher.png"
            rd_path = res_out / folder / "ic_launcher_round.png"
            save_pil_as_png(square, sq_path)
            save_pil_as_png(rounded, rd_path)
            outputs += [sq_path, rd_path]
    else:
        # stdlib fallback
        for folder, size in ANDROID_MIPMAP.items():
            write_png_rgba(
                res_out / folder / "ic_launcher.png",
                size, size,
                flat_rounded_square(size, SHOPNO_BLUE, (0, 0, 0, 0)),
            )
            write_png_rgba(
                res_out / folder / "ic_launcher_round.png",
                size, size,
                flat_round_icon(size, SHOPNO_BLUE),
            )
            outputs += [res_out / folder / "ic_launcher.png",
                        res_out / folder / "ic_launcher_round.png"]
    return outputs


def generate_adaptive_icons(svg_path: Path, res_out: Path) -> list[Path]:
    """432x432 foreground + background PNGs for adaptive icon (API 26+)."""
    outputs: list[Path] = []
    if cairosvg is not None and Image is not None:
        fg = render_with_pillow(svg_path, ADAPTIVE_BG_SIZE)
        # background: full bleed navy
        bg = Image.new("RGBA",
                       (ADAPTIVE_BG_SIZE, ADAPTIVE_BG_SIZE),
                       SHOPNO_BG)
        # foreground: 50% safe zone already in the SVG canvas
        save_pil_as_png(fg, res_out / "drawable" / "ic_launcher_foreground.png")
        save_pil_as_png(bg, res_out / "drawable" / "ic_launcher_background.png")
        outputs += [res_out / "drawable" / "ic_launcher_foreground.png",
                    res_out / "drawable" / "ic_launcher_background.png"]
    else:
        write_png_rgba(
            res_out / "drawable" / "ic_launcher_foreground.png",
            ADAPTIVE_BG_SIZE, ADAPTIVE_BG_SIZE,
            flat_rounded_square(ADAPTIVE_BG_SIZE, SHOPNO_BLUE, (0, 0, 0, 0)),
        )
        write_png_rgba(
            res_out / "drawable" / "ic_launcher_background.png",
            ADAPTIVE_BG_SIZE, ADAPTIVE_BG_SIZE,
            bytes(SHOPNO_BG) * (ADAPTIVE_BG_SIZE * ADAPTIVE_BG_SIZE),
        )
        outputs += [res_out / "drawable" / "ic_launcher_foreground.png",
                    res_out / "drawable" / "ic_launcher_background.png"]
    return outputs


def write_adaptive_manifest(res_out: Path) -> list[Path]:
    """Write the anydpi-v26 adaptive-icon XML manifests."""
    res_out.mkdir(parents=True, exist_ok=True)
    files = [
        ("mipmap-anydpi-v26", "ic_launcher.xml", False),
        ("mipmap-anydpi-v26", "ic_launcher_round.xml", True),
    ]
    paths: list[Path] = []
    for folder, name, round_ in files:
        p = res_out / folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        round_attr = ' android:roundIcon="@mipmap/ic_launcher_round"' if False else ""
        # the actual roundIcon attribute belongs on <application>, not here;
        # for anydpi-v26 we just declare foreground/background.
        p.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@drawable/ic_launcher_background"/>\n'
            '    <foreground android:drawable="@drawable/ic_launcher_foreground"/>\n'
            '</adaptive-icon>\n',
            encoding="utf-8",
        )
        paths.append(p)
    return paths


def generate_nsis_bmps(svg_path: Path, exe_overlay: Path) -> list[Path]:
    """Write the NSIS installer BMPs."""
    exe_overlay.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    if cairosvg is not None and Image is not None:
        for name, w, h in [
            ("InstallHeader.bmp",  NSIS_HEADER_W,  NSIS_HEADER_H),
            ("InstallSidebar.bmp", NSIS_SIDEBAR_W, NSIS_SIDEBAR_H),
        ]:
            img = render_with_pillow(svg_path, max(w, h))
            # crop centre
            left = (img.size[0] - w) // 2
            top  = (img.size[1] - h) // 2
            cropped = img.crop((left, top, left + w, top + h)).convert("RGB")
            out = exe_overlay / name
            cropped.save(out, format="BMP")
            paths.append(out)
    else:
        for name, w, h in [
            ("InstallHeader.bmp",  NSIS_HEADER_W,  NSIS_HEADER_H),
            ("InstallSidebar.bmp", NSIS_SIDEBAR_W, NSIS_SIDEBAR_H),
        ]:
            data = flat_bmp(w, h, SHOPNO_SKY, SHOPNO_BG)
            out = exe_overlay / name
            out.write_bytes(data)
            paths.append(out)
    return paths


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--src", required=True, type=Path,
                   help="source SVG (e.g. branding/shopnoapp-logo.svg)")
    p.add_argument("--out", required=True, type=Path,
                   help="output res/ dir (APK overlay)")
    p.add_argument("--exe-overlay", type=Path,
                   help="output dir for NSIS installer BMPs (optional)")
    args = p.parse_args()

    if not args.src.is_file():
        sys.stderr.write(f"SVG not found: {args.src}\n")
        return 2

    if cairosvg is None or Image is None:
        sys.stderr.write(
            "warning: cairosvg / Pillow not installed; falling back to "
            "stdlib PNG/BMP writer (flat colour icons). The CI always "
            "installs the real libs so production artifacts get the "
            "real logo.\n"
        )

    print(f"[1/4] generating mipmap icons -> {args.out}")
    mipmaps = generate_android_mipmaps(args.src, args.out)
    print(f"      wrote {len(mipmaps)} mipmap PNGs")

    print(f"[2/4] generating adaptive-icon foreground/background")
    adaptive = generate_adaptive_icons(args.src, args.out)
    print(f"      wrote {len(adaptive)} adaptive-icon PNGs")

    print(f"[3/4] writing adaptive-icon XML manifests")
    manifests = write_adaptive_manifest(args.out)
    print(f"      wrote {len(manifests)} anydpi-v26 XMLs")

    if args.exe_overlay:
        print(f"[4/4] generating NSIS installer BMPs -> {args.exe_overlay}")
        bmps = generate_nsis_bmps(args.src, args.exe_overlay)
        print(f"      wrote {len(bmps)} BMPs")
    else:
        print("[4/4] no --exe-overlay, skipping BMPs")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
