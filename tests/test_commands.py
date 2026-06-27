"""Byte-accurate tests for the low-level command encoder (no hardware)."""

from __future__ import annotations

import pytest

from vkp80iii import (
    AztecType,
    Barcode,
    CharsetCountry,
    CodePage,
    CommandError,
    DataMatrixEncoding,
    Font,
    HRIFont,
    HRIPosition,
    Justify,
    LedFlashFreq,
    LedMode,
    PrintQuality,
    QRErrorCorrection,
    QRModel,
    StatusType,
    Underline,
)
from vkp80iii import (
    commands as c,
)
from vkp80iii.constants import PDF417ErrorMode


# =====================================================================
# init / device
# =====================================================================
def test_initialize_and_device():
    assert c.initialize() == b"\x1b\x40"
    assert c.select_peripheral(True, False) == b"\x1b\x3d\x01"
    assert c.select_peripheral(True, True) == b"\x1b\x3d\x81"
    assert c.select_peripheral(False) == b"\x1b\x3d\x00"
    assert c.enable_keys(True) == b"\x1b\x63\x35\x00"
    assert c.enable_keys(False) == b"\x1b\x63\x35\x01"
    assert c.set_print_quality(PrintQuality.HIGH_SPEED) == b"\x1d\xf0\x02"
    assert c.set_motion_units(204, 204) == b"\x1d\x50\xcc\xcc"
    assert c.set_motion_units_ext(204, 408) == b"\x1d\xd0\x00\xcc\x01\x98"
    assert c.set_density(0x04) == b"\x1d\x7c\x04"
    assert c.set_density(0x06) == b"\x1d\x7c\x06"
    assert c.data_logger(0) == b"\x1c\x47\x00"
    assert c.data_logger(1) == b"\x1c\x47\x01"
    with pytest.raises(CommandError):
        c.set_density(0x07)
    with pytest.raises(CommandError):
        c.data_logger(2)


# =====================================================================
# print / feed
# =====================================================================
def test_print_feed():
    assert c.lf() == b"\x0a"
    assert c.cr() == b"\x0d"
    assert c.form_feed() == b"\x1b\x0c"
    assert c.feed_units(16) == b"\x1b\x4a\x10"
    assert c.feed_lines(3) == b"\x1b\x64\x03"
    assert c.backspace() == b"\x08"
    assert c.horizontal_tab() == b"\x09"


# =====================================================================
# line spacing
# =====================================================================
def test_line_spacing():
    assert c.line_spacing_1_8() == b"\x1b\x30"
    assert c.line_spacing_1_6() == b"\x1b\x32"
    assert c.set_line_spacing(60) == b"\x1b\x33\x3c"


# =====================================================================
# character / text formatting
# =====================================================================
def test_print_modes_each_bit():
    assert c.select_print_modes() == b"\x1b\x21\x00"
    assert c.select_print_modes(font_b=True) == b"\x1b\x21\x01"
    assert c.select_print_modes(bold=True) == b"\x1b\x21\x08"
    assert c.select_print_modes(double_height=True) == b"\x1b\x21\x10"
    assert c.select_print_modes(double_width=True) == b"\x1b\x21\x20"
    assert c.select_print_modes(italic=True) == b"\x1b\x21\x40"  # bit 6 on this printer
    assert c.select_print_modes(underline=True) == b"\x1b\x21\x80"
    # all together
    assert (
        c.select_print_modes(
            font_b=True, bold=True, double_height=True, double_width=True, italic=True, underline=True
        )
        == b"\x1b\x21\xf9"
    )


def test_text_styles():
    assert c.bold() == b"\x1b\x45\x01"
    assert c.bold(False) == b"\x1b\x45\x00"
    assert c.double_strike() == b"\x1b\x47\x01"
    assert c.italic() == b"\x1b\x34\x01"
    assert c.underline(Underline.SINGLE) == b"\x1b\x2d\x01"
    assert c.underline(Underline.DOUBLE) == b"\x1b\x2d\x02"
    assert c.underline(0) == b"\x1b\x2d\x00"
    assert c.upside_down() == b"\x1b\x7b\x01"
    assert c.rotate_90() == b"\x1b\x56\x01"
    assert c.reverse() == b"\x1d\x42\x01"
    assert c.set_right_spacing(4) == b"\x1b\x20\x04"


def test_fonts_charsets():
    assert c.select_font(Font.A) == b"\x1b\x4d\x00"
    assert c.select_font(Font.B) == b"\x1b\x4d\x01"
    assert c.select_charset(CharsetCountry.GERMANY) == b"\x1b\x52\x02"
    assert c.select_code_page(CodePage.WPC1252) == b"\x1b\x74\x10"
    assert c.select_code_page(CodePage.PC437) == b"\x1b\x74\x00"


def test_char_size():
    assert c.char_size(1, 1) == b"\x1d\x21\x00"
    assert c.char_size(2, 3) == b"\x1d\x21\x12"  # width hi-nibble, height lo-nibble
    assert c.char_size(8, 8) == b"\x1d\x21\x77"


# =====================================================================
# positioning / margins
# =====================================================================
def test_positioning():
    assert c.justify(Justify.CENTER) == b"\x1b\x61\x01"
    assert c.justify(Justify.RIGHT) == b"\x1b\x61\x02"
    assert c.set_absolute_position(300) == b"\x1b\x24\x2c\x01"
    assert c.set_relative_position(10) == b"\x1b\x5c\x0a\x00"
    assert c.set_relative_position(-1) == b"\x1b\x5c\xff\xff"  # 65535
    assert c.set_left_margin(56) == b"\x1d\x4c\x38\x00"
    assert c.set_print_area_width(448) == b"\x1d\x57\xc0\x01"
    assert c.set_print_area_width(0) == b"\x1d\x57\x00\x00"


def test_tab_stops():
    assert c.set_tab_stops(8, 16, 24) == b"\x1b\x44\x08\x10\x18\x00"
    assert c.set_tab_stops() == b"\x1b\x44\x00"


# =====================================================================
# cutting
# =====================================================================
def test_cut():
    assert c.cut() == b"\x1d\x56\x00"
    assert c.cut(feed=40) == b"\x1d\x56\x41\x28"
    assert c.total_cut() == b"\x1b\x69"


# =====================================================================
# black-mark / mechanism
# =====================================================================
def test_black_mark_and_mechanism():
    assert c.set_black_mark_distance(80) == b"\x1d\xe7\x00\x50"  # +8.0 mm
    assert c.set_black_mark_distance(-40) == b"\x1d\xe7\x80\x28"  # -4.0 mm
    assert c.set_black_mark_distance(0) == b"\x1d\xe7\x00\x00"
    assert c.align_to_printhead() == b"\x1d\xf6"
    assert c.align_to_cutter() == b"\x1d\xf8"
    assert c.paper_recovery(11) == b"\x1c\xc1\x0b"
    assert c.paper_recovery(0) == b"\x1c\xc1\x00"
    assert c.set_virtual_paper_end(1500) == b"\x1d\xe6\x05\xdc"
    assert c.set_min_ticket_length(80) == b"\x1d\xe8\x50"


# =====================================================================
# presenter / ejector
# =====================================================================
def test_presenter_ejector():
    assert c.collect_mode(True) == b"\x1b\x43\x01"
    assert c.collect_mode(False) == b"\x1b\x43\x00"
    assert c.eject_mode() == b"\x1b\x46"
    assert c.set_presentation_offset(20) == b"\x1c\x4b\x14"
    # present: steps=1, blink, eject (E=0x45), 5s
    assert c.present_ticket(1, blink_led=True, retract=False, timeout_s=5) == b"\x1c\x50\x01\x01\x45\x05"
    # retract (R=0x52), no blink, no timeout
    assert c.present_ticket(2, retract=True) == b"\x1c\x50\x02\x00\x52\x00"


# =====================================================================
# status / queries
# =====================================================================
def test_status_queries():
    assert c.request_status(StatusType.PRINTER) == b"\x10\x04\x01"
    assert c.request_status(StatusType.PAPER) == b"\x10\x04\x04"
    assert c.request_full_status() == b"\x10\x04\x14"
    assert c.transmit_paper_sensor() == b"\x1b\x76"
    assert c.auto_status_back(paper=True, user=True, recoverable=True, unrecoverable=True) == b"\x1d\xe0\x0f"
    assert c.auto_status_back() == b"\x1d\xe0\x00"
    assert c.auto_status_back(paper=True) == b"\x1d\xe0\x01"
    assert c.transmit_device_id(0xFF) == b"\x1d\x49\xff"
    assert c.read_paper_remaining() == b"\x1d\xe1"
    assert c.read_cut_count() == b"\x1d\xe2"
    assert c.read_printed_length() == b"\x1d\xe3"
    assert c.read_retract_count() == b"\x1d\xe4"
    assert c.read_powerup_count() == b"\x1d\xe5"


# =====================================================================
# 1D barcodes
# =====================================================================
def test_barcode_1d_helpers():
    assert c.set_barcode_height(120) == b"\x1d\x68\x78"
    assert c.set_barcode_width(3) == b"\x1d\x77\x03"
    assert c.set_hri_position(HRIPosition.BELOW) == b"\x1d\x48\x02"
    assert c.set_hri_position(HRIPosition.BOTH) == b"\x1d\x48\x03"
    assert c.set_hri_font(HRIFont.B) == b"\x1d\x66\x01"


def test_barcode_1d_types():
    assert c.barcode(Barcode.CODE128, "{BABC123") == b"\x1d\x6b\x49\x08{BABC123"
    assert c.barcode(Barcode.EAN13, "123456789012") == b"\x1d\x6b\x43\x0c123456789012"
    assert c.barcode(Barcode.EAN8, "1234567") == b"\x1d\x6b\x44\x07" + b"1234567"
    assert c.barcode(Barcode.CODE39, b"ABC") == b"\x1d\x6b\x45\x03ABC"
    assert c.barcode(Barcode.CODE32, "12345678") == b"\x1d\x6b\x5a\x08" + b"12345678"


# =====================================================================
# 2D barcodes -- PDF417
# =====================================================================
def test_pdf417():
    assert c.pdf417_columns(5) == b"\x1d\x28\x6b\x03\x00\x30\x41\x05"
    assert c.pdf417_columns(0) == b"\x1d\x28\x6b\x03\x00\x30\x41\x00"
    assert c.pdf417_rows(0) == b"\x1d\x28\x6b\x03\x00\x30\x42\x00"
    assert c.pdf417_module_width(3) == b"\x1d\x28\x6b\x03\x00\x30\x43\x03"
    assert c.pdf417_module_height(3) == b"\x1d\x28\x6b\x03\x00\x30\x44\x03"
    assert c.pdf417_error_correction(2, mode=PDF417ErrorMode.RATIO) == b"\x1d\x28\x6b\x04\x00\x30\x45\x31\x02"
    assert c.pdf417_error_correction(3, mode=PDF417ErrorMode.LEVEL) == b"\x1d\x28\x6b\x04\x00\x30\x45\x30\x33"
    assert c.pdf417_store(b"AB") == b"\x1d\x28\x6b\x05\x00\x30\x50\x30AB"
    assert c.pdf417_print() == b"\x1d\x28\x6b\x03\x00\x30\x51\x30"


# =====================================================================
# 2D barcodes -- QR
# =====================================================================
def test_qr():
    assert c.qr_model(QRModel.MODEL2) == b"\x1d\x28\x6b\x04\x00\x31\x41\x32\x00"
    assert c.qr_model(QRModel.MICRO) == b"\x1d\x28\x6b\x04\x00\x31\x41\x33\x00"
    assert c.qr_version(8) == b"\x1d\x28\x6b\x03\x00\x31\x42\x08"
    assert c.qr_module_size(6) == b"\x1d\x28\x6b\x03\x00\x31\x43\x06"
    assert c.qr_error_correction(QRErrorCorrection.H) == b"\x1d\x28\x6b\x03\x00\x31\x45\x34"
    assert c.qr_error_correction(QRErrorCorrection.M) == b"\x1d\x28\x6b\x03\x00\x31\x45\x32"
    assert c.qr_store(b"AB") == b"\x1d\x28\x6b\x05\x00\x31\x50\x31AB"
    assert c.qr_print() == b"\x1d\x28\x6b\x03\x00\x31\x51\x31"
    assert c.qr_transmit_size() == b"\x1d\x28\x6b\x03\x00\x31\x52\x30"


# =====================================================================
# 2D barcodes -- AZTEC / DataMatrix
# =====================================================================
def test_aztec():
    assert c.aztec_type(AztecType.FULL) == b"\x1d\x28\x6b\x03\x00\x50\x41\x00"
    assert c.aztec_type(AztecType.RUNE) == b"\x1d\x28\x6b\x03\x00\x50\x41\x01"
    assert c.aztec_module_size(6) == b"\x1d\x28\x6b\x03\x00\x50\x43\x06"
    assert c.aztec_size(0) == b"\x1d\x28\x6b\x03\x00\x50\x44\x00"
    assert c.aztec_error_correction(0) == b"\x1d\x28\x6b\x03\x00\x50\x45\x00"
    assert c.aztec_store(b"X") == b"\x1d\x28\x6b\x04\x00\x50\x50\x34X"
    assert c.aztec_print() == b"\x1d\x28\x6b\x03\x00\x50\x51\x30"


def test_datamatrix():
    assert c.datamatrix_encoding(DataMatrixEncoding.AUTO) == b"\x1d\x28\x6b\x03\x00\x51\x41\x06"
    assert c.datamatrix_encoding(DataMatrixEncoding.ASCII) == b"\x1d\x28\x6b\x03\x00\x51\x41\x00"
    assert c.datamatrix_rotation(True) == b"\x1d\x28\x6b\x03\x00\x51\x42\x01"
    assert c.datamatrix_module_size(6) == b"\x1d\x28\x6b\x03\x00\x51\x43\x06"
    assert c.datamatrix_size(0) == b"\x1d\x28\x6b\x03\x00\x51\x44\x00"
    assert c.datamatrix_store(b"X") == b"\x1d\x28\x6b\x04\x00\x51\x50\x33X"
    assert c.datamatrix_print() == b"\x1d\x28\x6b\x03\x00\x51\x51\x33"


# =====================================================================
# images
# =====================================================================
def test_images():
    data = bytes([0xFF, 0x00] * 4)  # 2 bytes wide, 4 rows
    assert c.raster_image(2, 4, data) == b"\x1d\x76\x30\x00\x02\x00\x04\x00" + data
    assert c.raster_image(2, 4, data, mode=3) == b"\x1d\x76\x30\x03\x02\x00\x04\x00" + data
    blob = bytes(1 * 1 * 8)
    assert c.define_downloaded_bit_image(1, 1, blob) == b"\x1d\x2a\x01\x01" + blob
    assert c.print_downloaded_bit_image(0) == b"\x1d\x2f\x00"
    assert c.print_downloaded_bit_image(2) == b"\x1d\x2f\x02"


# =====================================================================
# LED bar
# =====================================================================
def test_led():
    assert c.led_bar(LedMode.OFF) == b"\x1c\x42\x43"
    assert c.led_bar(LedMode.ON) == b"\x1c\x42\x53"
    assert c.led_bar(LedMode.FLASH, LedFlashFreq.HZ_2) == b"\x1c\x42\x46\x04"
    assert c.led_color((255, 0, 0)) == b"\x1c\x4c\x43\x73\xff\x00\x00"
    assert c.led_color((0, 0, 255), target="background", persist=True) == b"\x1c\x4c\x42\x57\x00\x00\xff"
    assert c.led_color((1, 2, 3), target="foreground") == b"\x1c\x4c\x46\x77\x01\x02\x03"
    assert c.led_off() == b"\x1c\x42\x43"  # FS B OFF (stops flash too)
    assert c.led_rainbow(True) == b"\x1c\x4c\x52\x77\x01"
    assert c.led_rainbow(False) == b"\x1c\x4c\x52\x77\x00"
    assert c.led_defaults() == b"\x1c\x4c\x44\x00"


# =====================================================================
# logo / graphics
# =====================================================================
def test_logo_graphics():
    assert c.print_logo(10) == b"\x1c\x93\x00\x0a\x00\x00\x00\x00"
    assert (
        c.print_logo(10, justify=Justify.CENTER, rotate=True, border_dots=1)
        == b"\x1c\x93\x00\x0a\x81\x01\x00\x00"
    )
    assert c.print_logo(10, position_dots=80) == b"\x1c\x93\x00\x0a\x03\x00\x50\x00"
    assert c.print_graphic_bank(0, 100, 199) == b"\x1b\xfa\x00\x00\x64\x00\xc7"


def test_store_logo_flash():
    data = b"\x80\x01\xff\x00"  # width 16 px -> 2 bytes/row, 2 rows -> 4 bytes
    out = c.store_logo_flash(7, 16, 2, data, name="AB")
    # 1C 94 | nH nL | xDimH xDimL | yDimH yDimL | 00 00 | name(16) | data | 3E
    assert out[:10] == b"\x1c\x94\x00\x07\x00\x10\x00\x02\x00\x00"
    assert out[10:26] == b"AB" + b"\x00" * 14
    assert out[26:30] == data
    assert out[-1:] == b"\x3e"
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 15, 2, b"\x00" * 4)  # width not a multiple of 16
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 16, 2, b"\x00")  # wrong data length


# =====================================================================
# counters / macros
# =====================================================================
def test_counters_macros():
    assert c.counter_print_mode(3, align="right", pad_zero=True) == b"\x1d\x43\x30\x03\x01"
    assert c.counter_print_mode(0, align="right") == b"\x1d\x43\x30\x00\x00"
    assert c.counter_print_mode(3, align="left") == b"\x1d\x43\x30\x03\x02"
    assert c.counter_mode(0, 10, step=1, repeat=1) == b"\x1d\x43\x31\x00\x00\x0a\x00\x01\x01"
    assert c.set_counter(5) == b"\x1d\x43\x32\x05\x00"
    assert c.print_counter() == b"\x1d\x63"
    assert c.macro_define_start_end() == b"\x1d\x3a"
    assert c.macro_execute(2, 5, 0) == b"\x1d\x5e\x02\x05\x00"


# =====================================================================
# validation / range errors
# =====================================================================
@pytest.mark.parametrize(
    "call",
    [
        lambda: c.char_size(9, 1),
        lambda: c.char_size(1, 9),
        lambda: c.justify(5),
        lambda: c.underline(3),
        lambda: c.select_font(2),
        lambda: c.select_charset(20),
        lambda: c.set_tab_stops(*range(1, 40)),
        lambda: c.set_print_area_width(700),
        lambda: c.set_barcode_height(0),
        lambda: c.set_barcode_width(7),
        lambda: c.set_hri_position(4),
        lambda: c.barcode(Barcode.EAN13, "123"),  # too short
        lambda: c.barcode(Barcode.CODE39, b"x" * 256),  # too long
        lambda: c.qr_version(41),
        lambda: c.qr_module_size(1),
    ],
)
def test_validation_errors(call):
    with pytest.raises(CommandError):
        call()


def test_more_validation_errors():
    with pytest.raises(CommandError):
        c.pdf417_columns(31)
    with pytest.raises(CommandError):
        c.pdf417_rows(2)
    with pytest.raises(CommandError):
        c.aztec_size(40)
    with pytest.raises(CommandError):
        c.datamatrix_size(40)
    with pytest.raises(CommandError):
        c.set_black_mark_distance(2000)
    with pytest.raises(CommandError):
        c.set_min_ticket_length(10)
    with pytest.raises(CommandError):
        c.paper_recovery(12)
    with pytest.raises(CommandError):
        c.raster_image(2, 4, b"\x00")  # wrong data length
    with pytest.raises(CommandError):
        c.led_bar(LedMode.FLASH)  # FLASH needs a freq
    with pytest.raises(CommandError):
        c.led_color((0, 0, 0), target="middle")
    with pytest.raises(CommandError):
        c.set_motion_units_ext(3000, 0)
    with pytest.raises(CommandError):
        c.print_logo(70000)


def test_helper_range_errors():
    with pytest.raises(CommandError):
        c.feed_units(300)  # _u8 over range
    with pytest.raises(CommandError):
        c.set_absolute_position(70000)  # _u16le over range
    with pytest.raises(CommandError):
        c.set_motion_units_ext(0, 5000)  # y over 4080
    with pytest.raises(CommandError):
        c.present_ticket(steps=300)  # _u8 steps
    with pytest.raises(CommandError):
        c.set_barcode_height(300)
    with pytest.raises(CommandError):
        c.qr_module_size(30)
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 16, 0, b"")  # height 0


def test_review_fixes():
    # #11 symbology must be a byte (CommandError, not raw ValueError)
    with pytest.raises(CommandError):
        c.barcode(300, "12345678")
    # #9 numeric symbologies reject non-digits / odd ITF length
    with pytest.raises(CommandError):
        c.barcode(Barcode.EAN13, "12345678901X")  # 12 chars, non-digit
    with pytest.raises(CommandError):
        c.barcode(Barcode.ITF, "123")  # odd digit count
    assert c.barcode(Barcode.ITF, "1234")[:4] == b"\x1d\x6b\x46\x04"  # even ok
    # #10 tab stops must be strictly ascending
    with pytest.raises(CommandError):
        c.set_tab_stops(8, 8, 16)
    with pytest.raises(CommandError):
        c.set_tab_stops(16, 8)
    # #12 print_graphic_bank validates num_lines and the 862-line area
    with pytest.raises(CommandError):
        c.print_graphic_bank(0, 1, 1000)
    with pytest.raises(CommandError):
        c.print_graphic_bank(0, 800, 100)  # 800+100-1 > 862
    # #7 immediate + persist still turns the bar on (op 0x73, not flash-only)
    assert c.led_color((1, 2, 3), target="immediate", persist=True) == b"\x1c\x4c\x43\x73\x01\x02\x03"


def test_validation_error_branches():
    """Each builder rejects out-of-range arguments with CommandError."""
    # _u16be range (via set_virtual_paper_end) + set_print_area_width + print_logo
    with pytest.raises(CommandError):
        c.set_virtual_paper_end(70000)
    with pytest.raises(CommandError):
        c.set_print_area_width(700)
    with pytest.raises(CommandError):
        c.print_logo(70000)
    # store_logo_flash: width multiple-of-16, height range, data length
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 17, 1, b"")
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 16, 0, b"")
    with pytest.raises(CommandError):
        c.store_logo_flash(1, 16, 1, b"x")  # expected (16/8)*1 = 2 bytes
    # raster_image: mode, width_bytes, height, data length
    with pytest.raises(CommandError):
        c.raster_image(1, 1, b"\x00", mode=9)
    with pytest.raises(CommandError):
        c.raster_image(0, 1, b"")
    with pytest.raises(CommandError):
        c.raster_image(1, 3000, b"")
    with pytest.raises(CommandError):
        c.raster_image(1, 1, b"")  # expected 1 byte
    # downloaded bit image
    with pytest.raises(CommandError):
        c.define_downloaded_bit_image(0, 1, b"")
    with pytest.raises(CommandError):
        c.define_downloaded_bit_image(1, 99, b"")
    with pytest.raises(CommandError):
        c.define_downloaded_bit_image(40, 40, b"")  # x*y > 1536
    with pytest.raises(CommandError):
        c.define_downloaded_bit_image(1, 1, b"x")  # expected 8 bytes
    with pytest.raises(CommandError):
        c.print_downloaded_bit_image(9)
    # counter print mode
    with pytest.raises(CommandError):
        c.counter_print_mode(digits=9)
    with pytest.raises(CommandError):
        c.counter_print_mode(align="middle")
    # PDF417
    with pytest.raises(CommandError):
        c.pdf417_columns(99)
    with pytest.raises(CommandError):
        c.pdf417_rows(2)  # neither 0 nor 3..20
    with pytest.raises(CommandError):
        c.pdf417_module_width(9)
    with pytest.raises(CommandError):
        c.pdf417_module_height(9)
    with pytest.raises(CommandError):
        c.pdf417_error_correction(99, mode=PDF417ErrorMode.LEVEL)
    with pytest.raises(CommandError):
        c.pdf417_error_correction(99)  # ratio mode, > 40
    # QR / AZTEC / DataMatrix range checks
    with pytest.raises(CommandError):
        c.qr_version(99)
    with pytest.raises(CommandError):
        c.qr_module_size(99)
    with pytest.raises(CommandError):
        c.aztec_module_size(99)
    with pytest.raises(CommandError):
        c.aztec_size(99)
    with pytest.raises(CommandError):
        c.aztec_error_correction(99)
    with pytest.raises(CommandError):
        c.datamatrix_module_size(99)
    with pytest.raises(CommandError):
        c.datamatrix_size(99)
