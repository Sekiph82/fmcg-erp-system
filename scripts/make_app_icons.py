"""Build the app icons (iPhone home screen, Android, PWA) from the POVU logo (owner's choice, 2026-11-19).

Source: PRESENTATIONS/INPUTS/CHARACTERS - LOGOS - VIDEOS/povu logo.png (transparent background). The logo is cropped to its
opaque pixels, centred on a white square and exported in the sizes the manifest and iOS use. iOS does not allow
transparency in home-screen icons, so every icon has a solid white background.
Usage: python scripts/make_app_icons.py "<path to povu logo.png>"
"""
import pathlib
import sys

from PIL import Image

src = Image.open(sys.argv[1]).convert("RGBA")
alpha = src.getchannel("A").point(lambda v: 255 if v > 24 else 0)  # transparent pixels may still carry colour data
letter = src.crop(alpha.getbbox())
out = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"


def icon(size: int, fill: float) -> Image.Image:
    """The letter scaled to `fill` of the square (maskable icons keep a safe margin), on white."""
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    w, h = letter.size
    scale = fill * size / max(w, h)
    img = letter.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas.convert("RGB")


icon(180, 0.94).save(out / "apple-touch-icon.png", optimize=True)  # wide logo: fill the width
icon(192, 0.94).save(out / "icon-192.png", optimize=True)
icon(512, 0.94).save(out / "icon-512.png", optimize=True)
icon(512, 0.78).save(out / "icon-maskable-512.png", optimize=True)  # Android masks to a circle: keep inside the safe zone
print("icons written to", out)
