"""Build the app icons (home-screen / installed-app icons) from the church logo.

    python scripts/make_icons.py

Reads static/img/logo-large.png (a circular logo on a transparent background) and writes
static/icons/*.png. Needs Pillow, which is already in requirements/base.txt.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "static" / "img" / "logo-large.png"
OUT = ROOT / "static" / "icons"
NAVY = (11, 42, 91, 255)


def render(size, fill):
    """Logo centred on a navy square. `fill` is the share of the square the logo covers."""
    logo = Image.open(SRC).convert("RGBA")
    d = int(size * fill)
    logo = logo.resize((d, d), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), NAVY)
    canvas.alpha_composite(logo, ((size - d) // 2, (size - d) // 2))
    return canvas.convert("RGB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    # "maskable" icons get cropped into circles/squircles by Android, so keep the logo inside the safe zone.
    for name, size, fill in [
        ("icon-192.png", 192, 0.92),
        ("icon-512.png", 512, 0.92),
        ("maskable-512.png", 512, 0.68),
        ("apple-touch-icon.png", 180, 0.92),
    ]:
        render(size, fill).save(OUT / name, optimize=True)
        print("wrote", OUT / name)
