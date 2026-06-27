"""Store a logo in flash (FS 0x94) and print it by number (FS 0x93).

    uv run python examples/logo_flash.py upload <path/to/logo.png> [number]
    uv run python examples/logo_flash.py print  [number]

IMPORTANT: after `upload`, **power-cycle the printer once** -- this firmware only
re-reads the logo index on boot, so print_logo() returns "FILE ERROR" until then.
Flash also has limited write cycles, so upload during setup, not per print.

Numbers 1/2 hold the factory demo logo; use your own (e.g. 200). Requires Pillow.
"""

import sys

from PIL import Image, ImageOps

from vkp80iii import Justify, Printer

TARGET_W = 320  # logo width in dots; must be a multiple of 16 for flash


def load_logo(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))  # flatten transparency
    img = Image.alpha_composite(bg, img).convert("L")
    bbox = ImageOps.invert(img).getbbox()  # trim white border
    if bbox:
        img = img.crop(bbox)
    h = round(img.height * TARGET_W / img.width)
    return img.resize((TARGET_W, h), Image.LANCZOS)


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "upload"

    if action == "upload":
        if len(sys.argv) < 3:
            print("usage: logo_flash.py upload <path/to/logo.png> [number]")
            sys.exit(2)
        path = sys.argv[2]
        number = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        with Printer(paper_width_mm=58) as p:
            img = load_logo(path)
            print(f"uploading logo #{number} ({img.width}x{img.height}) to flash ...")
            p.upload_logo(number, img, name="QUOBOX.BMP")
        print("upload OK. Now POWER-CYCLE the printer, then run:")
        print(f"    uv run python examples/logo_flash.py print {number}")

    elif action == "print":
        number = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        with Printer(paper_width_mm=58) as p:
            p.begin()
            p.print_logo(number, justify=Justify.CENTER)
            p.feed(3)
            p.present(steps=6, blink_led=False, timeout_s=2)
        print(f"printed logo #{number}")

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
