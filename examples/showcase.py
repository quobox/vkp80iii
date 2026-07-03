"""Print one big ticket exercising (almost) every feature of the library.

    uv run python examples/showcase.py

Calibrated for this unit's 58 mm roll (firmware PRINT WIDTH = 58 mm).
"""

from vkp80iii import (
    Barcode,
    Font,
    HRIPosition,
    Justify,
    Printer,
    QRErrorCorrection,
    Underline,
)

PAPER_ROLL_MM = 58  # physical roll width; for_paper() derives print area + centering offset


def rule(p: Printer) -> None:
    p.align(Justify.LEFT).textln("-" * 30)


def main() -> None:
    # for_paper() centers the print area on the roll; margin_mm is the per-side
    # safety margin (default 1.5 mm). Wider: for_paper(width_mm=58, margin_mm=4).
    with Printer.for_paper(width_mm=PAPER_ROLL_MM) as p:
        p.begin()
        p.led((0, 200, 0))  # bezel LED green while printing

        # --- title ---
        p.align(Justify.CENTER).char_size(2, 2).bold().textln("FEATURE SHOWCASE")
        p.char_size(1, 1).bold(False)
        rule(p)

        # --- text styles ---
        p.align(Justify.LEFT)
        p.textln("Normal text")
        p.bold().textln("Bold").bold(False)
        p.italic().textln("Italic").italic(False)
        p.underline(Underline.SINGLE).textln("Underline 1-dot").underline(0)
        p.underline(Underline.DOUBLE).textln("Underline 2-dot").underline(0)
        p.double_strike().textln("Double-strike").double_strike(False)
        p.reverse().textln(" Reverse (white on black) ").reverse(False)
        rule(p)

        # --- fonts ---
        p.font(Font.A).textln("Font A: ABCdef 12345")
        p.font(Font.B).textln("Font B: ABCdef 12345")
        p.font(Font.A)
        rule(p)

        # --- character sizes ---
        p.char_size(1, 1).textln("Size 1x1")
        p.char_size(2, 2).textln("Size 2x2")
        p.char_size(3, 3).textln("3x3")
        p.char_size(1, 2).textln("tall (1x2)")
        p.char_size(2, 1).textln("wide (2x1)")
        p.char_size(1, 1)
        rule(p)

        # --- alignment ---
        p.align(Justify.LEFT).textln("left")
        p.align(Justify.CENTER).textln("center")
        p.align(Justify.RIGHT).textln("right")
        p.align(Justify.LEFT)
        rule(p)

        # --- 1D barcodes ---
        p.align(Justify.CENTER)
        p.textln("EAN-13")
        p.barcode(Barcode.EAN13, "400638133393", height=60, width=2, hri=HRIPosition.BELOW)
        p.newline()
        p.textln("CODE39")
        p.barcode(Barcode.CODE39, "VKP80III", height=60, width=2, hri=HRIPosition.BELOW)
        p.newline()
        p.textln("CODE128")
        p.barcode(Barcode.CODE128, "{BHello-128", height=60, width=2, hri=HRIPosition.BELOW)
        p.newline()
        rule(p)

        # --- 2D barcodes ---
        # This firmware (ROM 7.11) implements QR and PDF417 but NOT DataMatrix
        # (cn=0x51) or Aztec (cn=0x50) -- and the unit has no RGB LED module
        # either. p.datamatrix()/p.aztec() are byte-correct for firmware that
        # supports them; here they'd just leak as text, so they're omitted.
        p.textln("QR / PDF417")
        p.newline()
        p.qrcode("https://github.com/quobox/vkp80iii", module_size=5, ecc=QRErrorCorrection.M)
        p.newline()
        p.pdf417("VKP80III PDF417 demo", module_width=2, module_height=2)
        p.newline()
        rule(p)

        # --- counter ---
        p.align(Justify.LEFT).textln("Counter (auto-increment):")
        p.setup_counter(1, 999, step=1, repeat=1, digits=4, pad_zero=True)
        for _ in range(3):
            p.text("  no. ").print_counter().newline()
        rule(p)

        # --- raster image (a generated gradient bar), if Pillow is present ---
        try:
            from PIL import Image

            img = Image.new("L", (320, 40))
            for x in range(img.width):
                for y in range(img.height):
                    img.putpixel((x, y), (x * 255) // img.width)
            p.align(Justify.CENTER).textln("Raster image:")
            p.image(img)
            p.newline()
        except ImportError:
            p.textln("(install Pillow for image demo)")

        p.align(Justify.CENTER).textln("-- end --")
        p.feed(2)

        p.led_off()  # leave the bar off cleanly (no lingering flash)
        p.present(steps=8, blink_led=True)
    print("showcase printed")


if __name__ == "__main__":
    main()
