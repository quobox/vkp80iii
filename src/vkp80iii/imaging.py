"""Convert host-side images into VKP80III raster bit-image data.

Requires Pillow (``pip install vkp80iii[image]``). The output is the
``(width_bytes, height, data)`` tuple expected by
:func:`vkp80iii.commands.raster_image` / :meth:`vkp80iii.printer.Printer.image`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import MAX_DOTS
from .exceptions import VKPError

if TYPE_CHECKING:  # pragma: no cover
    from PIL import Image


def _require_pillow():
    try:
        from PIL import Image  # noqa: F401

        return Image
    except ImportError as exc:  # pragma: no cover - optional dep
        raise VKPError("image support requires Pillow. Install with: pip install vkp80iii[image]") from exc


def image_to_raster(
    image: Image.Image | str,
    *,
    max_width: int = MAX_DOTS,
    threshold: int | None = None,
    dither: bool = True,
    invert: bool = False,
) -> tuple[int, int, bytes]:
    """Convert an image (or path) to ``(width_bytes, height, data)``.

    * The image is scaled down (never up) so its width fits ``max_width`` dots.
    * ``threshold`` -- if given (0..255), use a hard black/white threshold;
      otherwise convert to 1-bit (with Floyd-Steinberg dithering when
      ``dither`` is True).
    * ``invert`` -- swap black and white.

    A pixel becomes a printed (black) dot when its luminance is below the
    threshold. Rows are packed MSB-first, 8 dots per byte.
    """
    Image = _require_pillow()

    img = Image.open(image) if isinstance(image, str) else image
    img = img.convert("L")  # grayscale

    if img.width > max_width:
        new_h = max(1, round(img.height * max_width / img.width))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    width, height = img.width, img.height
    width_bytes = (width + 7) // 8

    if threshold is None:
        dither_mode = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
        # mode "1" packs 1 bit/pixel, rows padded to a byte, MSB first, bit set = white
        raw = img.convert("1", dither=dither_mode).tobytes()

        def is_black(x: int, y: int) -> bool:
            return not raw[y * width_bytes + (x >> 3)] & (0x80 >> (x & 7))
    else:
        if not (0 <= threshold <= 255):
            raise VKPError("threshold must be 0..255")
        raw = img.tobytes()  # "L": one byte per pixel, row-major

        def is_black(x: int, y: int) -> bool:
            return raw[y * width + x] < threshold

    data = bytearray(width_bytes * height)
    for y in range(height):
        base = y * width_bytes
        for x in range(width):
            if is_black(x, y) != invert:  # XOR: set the dot bit
                data[base + (x >> 3)] |= 0x80 >> (x & 7)

    return width_bytes, height, bytes(data)
