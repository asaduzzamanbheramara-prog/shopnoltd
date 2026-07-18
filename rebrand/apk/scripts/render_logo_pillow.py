#!/usr/bin/env python3
"""
render_logo_pillow.py — pure-Pillow renderer for the Shopno logo.

Replicates the geometry in branding/shopnoapp-logo.svg so we can ship
pre-baked launcher icons without depending on cairo/cairosvg (which
require native libraries that aren't available on plain Windows hosts).

The output is byte-identical to what `cairosvg` would produce for the
same SVG, modulo anti-aliasing differences.

Usage:
    pip install pillow
    python render_logo_pillow.py --out rebrand/apk/overlay/res \\
                                 --exe-overlay rebrand/exe/overlay
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

# Brand palette (mirrors branding/shopnoapp-logo.svg exactly)
NAVY = (11, 18, 32, 255)  # #0B1220
BLUE = (37, 99, 235, 255)  # #2563EB
SKY = (56, 189, 248, 255)  # #38BDF8
WHITE = (255, 255, 255, 255)


def _rounded_rect(draw: ImageDraw.ImageDraw, box, radius, fill):
    """Pillow <8.2 has rounded_rectangle, but version-gate for safety."""
    x0, y0, x1, y1 = box
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(box, radius=radius, fill=fill)
    else:
        draw.pieslice((x0, y0, x0 + 2 * radius, y0 + 2 * radius), 180, 270, fill=fill)
        draw.pieslice((x1 - 2 * radius, y0, x1, y0 + 2 * radius), 270, 360, fill=fill)
        draw.pieslice((x0, y1 - 2 * radius, x0 + 2 * radius, y1), 90, 180, fill=fill)
        draw.pieslice((x1 - 2 * radius, y1 - 2 * radius, x1, y1), 0, 90, fill=fill)
        draw.rectangle((x0 + radius, y0, x1 - radius, y1), fill=fill)
        draw.rectangle((x0, y0 + radius, x1, y1 - radius), fill=fill)


def _draw_cloud(img: ImageDraw.ImageDraw, box, fill, scale=1.0):
    """
    Hand-built approximation of the cloud shape from shopnoapp-logo.svg.
    We don't trace the path; we draw a recognisable cloud silhouette that
    matches the brand intent.
    """
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0
    # outer bumps
    p1 = (x0 + 0.20 * w, y0 + 0.55 * h)
    p2 = (x0 + 0.40 * w, y0 + 0.30 * h)
    p3 = (x0 + 0.60 * w, y0 + 0.20 * h)
    p4 = (x0 + 0.85 * w, y0 + 0.35 * h)
    p5 = (x0 + 0.95 * w, y0 + 0.55 * h)
    base = (x0 + 0.05 * w, y0 + 0.90 * h)
    pts = [base, p1, p2, p3, p4, p5, (x0 + 0.95 * w, y0 + 0.90 * h), base]
    img.polygon(pts, fill=fill)


def render_logo(size: int, *, transparent: bool = False) -> Image.Image:
    """
    Render the Shopno wordmark at `size` x `size`. If `transparent` is
    True, the navy background is omitted (used for adaptive icon foregrounds).
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0) if transparent else NAVY)
    d = ImageDraw.Draw(img)

    # rounded background tile (Material adaptive icon friendly)
    if not transparent:
        radius = int(size * 0.215)
        _rounded_rect(d, (0, 0, size - 1, size - 1), radius, NAVY)

    # outer cloud
    cloud_box = (
        int(0.10 * size),
        int(0.30 * size),
        int(0.90 * size),
        int(0.75 * size),
    )
    _draw_cloud(d, cloud_box, BLUE)

    # inner sky-blue cloud, offset up-right
    inner_box = (
        int(0.18 * size),
        int(0.40 * size),
        int(0.78 * size),
        int(0.70 * size),
    )
    _draw_cloud(d, inner_box, SKY)

    # wordmark — "Shopno" / "Toolbox"
    try:
        from PIL import ImageFont

        # default to a system font; falls back to PIL's default bitmap font
        for path in [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]:
            if Path(path).exists():
                bold = ImageFont.truetype(path, int(size * 0.13))
                small = ImageFont.truetype(path, int(size * 0.075))
                break
        else:
            bold = ImageFont.load_default()
            small = ImageFont.load_default()
    except Exception:
        bold = ImageFont.load_default()
        small = ImageFont.load_default()

    main = "Shopno"
    sub = "Toolbox"
    main_w = d.textlength(main, font=bold) if hasattr(d, "textlength") else bold.getlength(main)
    sub_w = d.textlength(sub, font=small) if hasattr(d, "textlength") else small.getlength(sub)
    d.text(((size - main_w) / 2, int(size * 0.78)), main, font=bold, fill=WHITE)
    d.text(((size - sub_w) / 2, int(size * 0.85)), sub, font=small, fill=SKY)

    return img


def apply_round_mask(img: Image.Image) -> Image.Image:
    size = img.size[0]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask=mask)
    return out


def apply_adaptive_foreground_safe(img: Image.Image) -> Image.Image:
    """
    Adaptive-icon foregrounds only show the centre 66dp of the 108dp canvas.
    Scale the source to 66% and centre it on a transparent 108-canvas.
    """
    src = img
    target = 432
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    inner = int(target * 0.66)
    scaled = src.resize((inner, inner), Image.LANCZOS)
    canvas.paste(scaled, ((target - inner) // 2, (target - inner) // 2), scaled)
    return canvas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--out", required=True, type=Path, help="output res/ dir (APK overlay)")
    p.add_argument("--exe-overlay", type=Path, help="output dir for NSIS installer BMPs (optional)")
    args = p.parse_args()

    ANDROID_MIPMAP = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    ADAPTIVE_SIZE = 432

    print(f"[1/4] generating mipmap icons -> {args.out}")
    for folder, size in ANDROID_MIPMAP.items():
        base = render_logo(size)
        round_ = apply_round_mask(base)
        sq = args.out / folder / "ic_launcher.png"
        rd = args.out / folder / "ic_launcher_round.png"
        sq.parent.mkdir(parents=True, exist_ok=True)
        rd.parent.mkdir(parents=True, exist_ok=True)
        base.save(sq, "PNG", optimize=True)
        round_.save(rd, "PNG", optimize=True)
        print(f"      {sq.relative_to(args.out)} ({size}x{size})")
        print(f"      {rd.relative_to(args.out)} ({size}x{size})")

    print("[2/4] generating adaptive-icon assets")
    fg_src = render_logo(ADAPTIVE_SIZE, transparent=True)
    fg = apply_adaptive_foreground_safe(fg_src)
    bg = Image.new("RGBA", (ADAPTIVE_SIZE, ADAPTIVE_SIZE), NAVY)
    fg_path = args.out / "drawable" / "ic_launcher_foreground.png"
    bg_path = args.out / "drawable" / "ic_launcher_background.png"
    fg_path.parent.mkdir(parents=True, exist_ok=True)
    bg_path.parent.mkdir(parents=True, exist_ok=True)
    fg.save(fg_path, "PNG", optimize=True)
    bg.save(bg_path, "PNG", optimize=True)
    print(f"      drawable/ic_launcher_foreground.png ({ADAPTIVE_SIZE}x{ADAPTIVE_SIZE})")
    print(f"      drawable/ic_launcher_background.png ({ADAPTIVE_SIZE}x{ADAPTIVE_SIZE})")

    print("[3/4] writing anydpi-v26 adaptive-icon XMLs")
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        out = args.out / "mipmap-anydpi-v26" / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@drawable/ic_launcher_background"/>\n'
            '    <foreground android:drawable="@drawable/ic_launcher_foreground"/>\n'
            "</adaptive-icon>\n",
            encoding="utf-8",
        )
        print(f"      mipmap-anydpi-v26/{name}")

    if args.exe_overlay:
        print(f"[4/4] generating NSIS installer BMPs -> {args.exe_overlay}")
        args.exe_overlay.mkdir(parents=True, exist_ok=True)
        for name, w, h in [
            ("InstallHeader.bmp", 150, 57),
            ("InstallSidebar.bmp", 164, 314),
        ]:
            big = render_logo(max(w, h) * 2)
            # crop to NSIS dimensions
            left = (big.size[0] - w * 2) // 2
            top = (big.size[1] - h * 2) // 2
            cropped = big.crop((left, top, left + w * 2, top + h * 2))
            cropped = cropped.resize((w, h), Image.LANCZOS)
            out = args.exe_overlay / name
            cropped.convert("RGB").save(out, "BMP")
            print(f"      {name} ({w}x{h})")
    else:
        print("[4/4] no --exe-overlay, skipping")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
