"""Print 2D barcodes the firmware lacks (DataMatrix/Aztec) as raster images.

ROM 7.11 has no native DataMatrix/Aztec, but raster printing works, so we can
render any symbology host-side and print it as an image. This uses treepoem
(BWIPP via Ghostscript) -- run it with the deps injected, no project change:

    uv run --with treepoem python examples/render_2d.py

Any 2D generator that yields a PIL image works the same way (qrcode, pdf417gen,
pylibdmtx, aztec_code_generator, ...).
"""

import treepoem
from PIL import Image

from vkp80iii import Justify, Printer


def render(bctype: str, data: str, target_dots: int = 300) -> Image.Image:
    """Render a barcode to a crisp 1-bit-ish raster scaled to ~target_dots wide."""
    img = treepoem.generate_barcode(barcode_type=bctype, data=data).convert("L")
    scale = max(1, target_dots // img.width)
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def main() -> None:
    with Printer.for_paper(width_mm=58) as p:
        p.begin()
        p.align(Justify.CENTER).bold().textln("RASTER 2D CODES").bold(False)
        p.textln("(rendered host-side)")
        p.newline()

        p.textln("DataMatrix:")
        p.image(render("datamatrix", "VKP80III via raster"), threshold=128)
        p.newline()

        p.textln("Aztec:")
        p.image(render("azteccode", "VKP80III via raster"), threshold=128)
        p.feed(2)
        p.present(steps=6, blink_led=False, timeout_s=2)
    print("raster 2D codes printed")


if __name__ == "__main__":
    main()
