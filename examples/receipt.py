"""A small formatted receipt: optional logo + items + barcode + QR, then cut.

    uv run python examples/receipt.py [path/to/logo.png]

Pass a logo image path to print it as a centered header (raster, self-contained,
no flash/reboot needed) -- so no logo needs to live in this repo. Without a path
the logo is simply skipped. If you've stored a logo in flash (see
examples/logo_flash.py) you can instead use ``p.print_logo(200, ...)``.

This unit's firmware PRINT WIDTH is 58 mm; a small left offset keeps left-aligned
text off the head's physical edge (see the README "Narrow paper" section).
"""

import sys

from vkp80iii import Barcode, HRIPosition, Justify, Printer

PAPER_ROLL_MM = 58  # physical roll width; for_paper() derives print area + centering offset
LOGO_WIDTH = 220  # header logo width in dots (~27 mm)


def logo_canvas(path: str, area_dots: int, logo_w: int = LOGO_WIDTH):
    """Load the logo (flatten alpha, trim), centre it on an area-wide canvas."""
    from PIL import Image, ImageOps  # lazy: only needed when a logo is used

    img = Image.open(path).convert("RGBA")
    img = Image.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, 255)), img).convert("L")
    bbox = ImageOps.invert(img).getbbox()
    if bbox:
        img = img.crop(bbox)
    h = round(img.height * logo_w / img.width)
    img = img.resize((logo_w, h), Image.LANCZOS)
    canvas = Image.new("L", (area_dots, h), 255)
    canvas.paste(img, ((area_dots - logo_w) // 2, 0))
    return canvas


def main() -> None:
    logo_path = sys.argv[1] if len(sys.argv) > 1 else None

    with Printer.for_paper(width_mm=PAPER_ROLL_MM) as p:
        p.begin()  # reset + apply left margin + print width

        # --- optional logo header (centred raster, aligns with the centred text) ---
        if logo_path:
            p.image(logo_canvas(logo_path, p.width_dots), threshold=128)
            p.newline()

        p.align(Justify.CENTER)
        p.char_size(2, 2).bold().textln("QUOBOX").bold(False).char_size(1, 1)
        p.textln("Musterstrasse 1, Parma")

        p.align(Justify.LEFT)
        p.textln("----------------------------")

        items = [("Espresso", "2.50"), ("Cornetto", "1.80"), ("Acqua 0.5L", "1.00")]
        for name, price in items:
            p.textln(f"{name:<20}{price:>8}")

        p.textln("----------------------------")
        p.bold().textln(f"{'TOTAL':<20}{'5.30':>8}").bold(False)
        p.newline()

        p.align(Justify.CENTER)
        p.barcode(Barcode.CODE128, "{BTICKET-0001", hri=HRIPosition.BELOW, height=80, width=2)
        p.newline()
        p.qrcode("https://example.com/receipt/0001", module_size=5)

        p.feed(3)
        p.present(steps=8, blink_led=True)  # cut and present the ticket


if __name__ == "__main__":
    main()
