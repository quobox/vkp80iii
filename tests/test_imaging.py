"""Tests for PIL image -> raster conversion."""

from __future__ import annotations

import pytest

from vkp80iii.exceptions import VKPError

Image = pytest.importorskip("PIL.Image")

from vkp80iii.imaging import image_to_raster  # noqa: E402


def _img(width, height, fill=255):
    return Image.new("L", (width, height), fill)


def test_threshold_packing_msb_first():
    # 8x1: only the leftmost pixel is black -> MSB set -> 0x80
    img = _img(8, 1, 255)
    img.putpixel((0, 0), 0)
    wb, h, data = image_to_raster(img, threshold=128, dither=False)
    assert (wb, h) == (1, 1)
    assert data == b"\x80"


def test_threshold_two_bytes():
    # 16x1: left 8 px black, right 8 px white
    img = _img(16, 1, 255)
    for x in range(8):
        img.putpixel((x, 0), 0)
    wb, h, data = image_to_raster(img, threshold=128)
    assert (wb, h) == (2, 1)
    assert data == b"\xff\x00"


def test_invert():
    img = _img(16, 1, 255)
    for x in range(8):
        img.putpixel((x, 0), 0)
    _, _, data = image_to_raster(img, threshold=128, invert=True)
    assert data == b"\x00\xff"


def test_padding_width_not_multiple_of_8():
    # 12 px wide -> 2 bytes/row, last 4 bits zero-padded
    img = _img(12, 1, 0)  # all black
    wb, h, data = image_to_raster(img, threshold=128)
    assert wb == 2
    assert data == b"\xff\xf0"  # 12 bits set, padded to 16


def test_downscale_to_max_width():
    img = _img(1200, 10, 0)
    wb, h, data = image_to_raster(img, max_width=576, threshold=128)
    assert wb == 72  # 576 / 8
    assert h == round(10 * 576 / 1200)  # proportional height
    assert len(data) == wb * h


def test_no_upscale():
    img = _img(40, 4, 0)
    wb, h, _ = image_to_raster(img, max_width=576, threshold=128)
    assert wb == 5  # ceil(40/8); width unchanged (never enlarged)
    assert h == 4


def test_threshold_out_of_range():
    with pytest.raises(VKPError):
        image_to_raster(_img(8, 1), threshold=999)


def test_dither_path_all_black():
    img = _img(16, 2, 0)  # 16 px wide (2 bytes), 2 rows, all black
    for dither in (True, False):  # FLOYDSTEINBERG / NONE
        wb, h, data = image_to_raster(img, threshold=None, dither=dither)
        assert (wb, h) == (2, 2)
        assert data == b"\xff\xff\xff\xff"  # all black -> all dot bits set


def test_dither_path_white_and_invert():
    img = _img(16, 1, 255)  # all white
    assert image_to_raster(img, threshold=None)[2] == b"\x00\x00"
    assert image_to_raster(img, threshold=None, invert=True)[2] == b"\xff\xff"
