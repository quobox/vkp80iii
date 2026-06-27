"""Print an image file as a centered raster logo.

    uv run python examples/logo.py [path/to/logo.png]

Handles transparency (flattened onto white), trims the white border, scales to a
target width and centers it. Requires Pillow.
"""

import sys

from PIL import Image, ImageOps

from vkp80iii import Printer

PAPER_DOTS = 464  # 58 mm printable width (8 dots/mm)
TARGET_W = 320  # logo width in dots (~40 mm)


def load_logo(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    # flatten transparency onto white so transparent areas stay white
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    img = Image.alpha_composite(bg, img).convert("L")
    # trim surrounding white
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop(bbox)
    # scale to target width, then centre on a full-width white canvas
    h = round(img.height * TARGET_W / img.width)
    img = img.resize((TARGET_W, h), Image.LANCZOS)
    canvas = Image.new("L", (PAPER_DOTS, h), 255)
    canvas.paste(img, ((PAPER_DOTS - TARGET_W) // 2, 0))
    return canvas


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: logo.py <path/to/logo.png>")
        sys.exit(2)
    path = sys.argv[1]
    with Printer(paper_width_mm=58, left_offset_dots=0) as p:
        p.begin()
        p.image(load_logo(path), threshold=128)
        p.feed(3)
        p.present(steps=6, blink_led=False, timeout_s=2)
    print(f"logo printed: {path}")


if __name__ == "__main__":
    main()
