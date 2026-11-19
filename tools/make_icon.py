"""Regenerate the KeyStone app icon (SVG, PNG and ICO) from one vector definition.

    python tools/make_icon.py

The mark is a keystone with two arch stones beside it, white on the accent blue.
The SVG is written by hand (no metadata) and the PNG/ICO are rasterised from the
same polygons with Pillow, supersampled so edges stay clean at small sizes.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "keystone" / "ui" / "assets"
SIZE = 512
BLUE = (0x25, 0x57, 0xD6)
WHITE = (255, 255, 255)
SIDE_ALPHA = 0.55          # the two arch stones are a softer white than the keystone

TILE = (8, 8, 504, 504, 112)                       # x0, y0, x1, y1, corner radius
KEYSTONE = [(168, 96), (344, 96), (296, 400), (216, 400)]
SIDES = [[(48, 184), (144, 160), (204, 400), (148, 400)],
         [(464, 184), (368, 160), (308, 400), (364, 400)]]
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def _pts(poly) -> str:
    return " ".join(f"{x},{y}" for x, y in poly)


def svg() -> str:
    x0, y0, x1, y1, r = TILE
    hexblue = "#%02X%02X%02X" % BLUE
    sides = "\n".join(f'    <polygon points="{_pts(p)}" opacity="{SIDE_ALPHA}" />' for p in SIDES)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}">\n'
            f'  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{r}" ry="{r}" fill="{hexblue}" />\n'
            f'  <g fill="#FFFFFF">\n'
            f'    <polygon points="{_pts(KEYSTONE)}" />\n{sides}\n  </g>\n</svg>\n')


def raster(px: int = SIZE, scale: int = 4) -> Image.Image:
    big = px * scale
    k = big / SIZE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1, r = TILE
    d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r * k, fill=BLUE + (255,))
    soft = tuple(round(SIDE_ALPHA * w + (1 - SIDE_ALPHA) * b) for w, b in zip(WHITE, BLUE))
    for p in SIDES:
        d.polygon([(x * k, y * k) for x, y in p], fill=soft + (255,))
    d.polygon([(x * k, y * k) for x, y in KEYSTONE], fill=WHITE + (255,))
    return img.resize((px, px), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "icon.svg").write_text(svg(), encoding="utf-8")
    raster(SIZE).save(OUT / "icon.png", optimize=True)
    # Each ICO frame is rendered at its own size, not downscaled from one bitmap.
    frames = [raster(s, 8) for s in ICO_SIZES]
    frames[-1].save(OUT / "icon.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])
    print("wrote icon.svg, icon.png, icon.ico ->", OUT)


if __name__ == "__main__":
    main()
