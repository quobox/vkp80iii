"""Tests for the high-level Printer API via DummyTransport."""

from __future__ import annotations

import pytest

from vkp80iii import (
    Barcode,
    CharsetCountry,
    CodePage,
    CommandError,
    DummyTransport,
    Font,
    HRIPosition,
    Justify,
    LedFlashFreq,
    Printer,
    PrintQuality,
    QRErrorCorrection,
    Underline,
)


def _p(**kw):
    return Printer(DummyTransport(), **kw)


# =====================================================================
# text + encoding
# =====================================================================
def test_text_and_lines():
    p = _p()
    p.text("Hi").newline().textln("x")
    assert bytes(p.transport.buffer) == b"Hi\x0ax\x0a"


def test_encoding_codepage_switch():
    p = _p()
    p.text("ä")  # default cp437
    assert bytes(p.transport.buffer) == b"\x84"
    p.transport.clear()
    p.code_page(CodePage.WPC1252)  # sends ESC t 0x10, sets cp1252
    assert p.encoding == "cp1252"
    p.transport.clear()
    p.text("ä")  # cp1252
    assert bytes(p.transport.buffer) == b"\xe4"


# =====================================================================
# layout: begin / apply_layout / set_print_area
# =====================================================================
def test_begin_emits_reset_margin_width():
    p = _p(paper_width_mm=54, left_offset_dots=72)
    assert p.width_dots == 432
    p.begin()
    assert bytes(p.transport.buffer) == b"\x1b\x40\x1d\x4c\x48\x00\x1d\x57\xb0\x01"


def test_set_print_area_default_uses_width():
    p = _p(paper_width_mm=54)
    p.set_print_area()
    assert bytes(p.transport.buffer) == b"\x1d\x57\xb0\x01"


# =====================================================================
# for_paper() centering factory
# =====================================================================
def test_for_paper_centers_with_default_margin():
    p = Printer.for_paper(DummyTransport(), width_mm=58)
    assert p.paper_width_mm == 55  # 58 - 2 * 1.5 mm margin
    assert p.width_dots == 440
    assert p.left_offset_dots == 12  # 1.5 mm * 8 dots/mm
    p.begin()
    # ESC @  +  GS L 12  +  GS W 440
    assert bytes(p.transport.buffer) == b"\x1b\x40\x1d\x4c\x0c\x00\x1d\x57\xb8\x01"


def test_for_paper_custom_margin():
    p = Printer.for_paper(DummyTransport(), width_mm=80, margin_mm=2)
    assert p.paper_width_mm == 76
    assert p.left_offset_dots == 16  # 2 mm * 8


def test_for_paper_zero_margin_uses_full_width():
    p = Printer.for_paper(DummyTransport(), width_mm=58, margin_mm=0)
    assert p.paper_width_mm == 58
    assert p.left_offset_dots == 0


def test_for_paper_rejects_margin_too_large():
    with pytest.raises(CommandError):
        Printer.for_paper(DummyTransport(), width_mm=3, margin_mm=1.5)


def test_for_paper_rejects_negative_margin():
    with pytest.raises(CommandError):
        Printer.for_paper(DummyTransport(), width_mm=58, margin_mm=-1)


# =====================================================================
# formatting chains return self and emit right bytes
# =====================================================================
def test_formatting_chain():
    p = _p()
    out = p.align(Justify.CENTER).bold().textln("HI").bold(False).cut()
    assert out is p
    assert bytes(p.transport.buffer) == (
        b"\x1b\x61\x01"  # center
        b"\x1b\x45\x01"  # bold on
        b"HI\x0a"
        b"\x1b\x45\x00"  # bold off
        b"\x1d\x56\x00"  # cut
    )


def test_align_helpers():
    p = _p()
    p.align_left()
    p.align_center()
    p.align_right()
    assert bytes(p.transport.buffer) == b"\x1b\x61\x00\x1b\x61\x01\x1b\x61\x02"


# =====================================================================
# barcodes
# =====================================================================
def test_qrcode_sequence():
    p = _p()
    p.qrcode("hi", module_size=6, ecc=QRErrorCorrection.M)
    assert bytes(p.transport.buffer) == (
        b"\x1d\x28\x6b\x04\x00\x31\x41\x32\x00"  # model 2
        b"\x1d\x28\x6b\x03\x00\x31\x43\x06"  # module size 6
        b"\x1d\x28\x6b\x03\x00\x31\x45\x32"  # ecc M
        b"\x1d\x28\x6b\x05\x00\x31\x50\x31hi"  # store "hi"
        b"\x1d\x28\x6b\x03\x00\x31\x51\x31"  # print
    )


def test_qrcode_with_version():
    p = _p()
    p.qrcode("x", version=8)
    # version command appears before store
    assert b"\x1d\x28\x6b\x03\x00\x31\x42\x08" in bytes(p.transport.buffer)


def test_barcode_with_options_order():
    p = _p()
    p.barcode(Barcode.CODE128, "{BABC", height=80, width=3, hri=HRIPosition.BELOW)
    assert bytes(p.transport.buffer) == (
        b"\x1d\x68\x50"  # height 80
        b"\x1d\x77\x03"  # width 3
        b"\x1d\x48\x02"  # HRI below
        b"\x1d\x6b\x49\x05{BABC"  # code128
    )


def test_pdf417_and_datamatrix_sequences():
    p = _p()
    p.pdf417("AB", columns=0, rows=0)
    buf = bytes(p.transport.buffer)
    assert buf.startswith(b"\x1d\x28\x6b\x03\x00\x30\x41\x00")  # columns
    assert buf.endswith(b"\x1d\x28\x6b\x03\x00\x30\x51\x30")  # print
    p2 = _p()
    p2.datamatrix("AB")
    assert bytes(p2.transport.buffer).endswith(b"\x1d\x28\x6b\x03\x00\x51\x51\x33")


# =====================================================================
# images (left padding applied by the high-level path)
# =====================================================================
def test_image_left_padding():
    Image = pytest.importorskip("PIL.Image")
    img = Image.new("L", (8, 1), 0)  # 1 byte wide, all black
    p = _p(paper_width_mm=80, left_offset_dots=16)  # pad = 2 bytes
    p.image(img, threshold=128)
    # GS v 0, mode 0, width_bytes=3 (2 pad + 1), height=1, data = 00 00 ff
    assert bytes(p.transport.buffer) == b"\x1d\x76\x30\x00\x03\x00\x01\x00\x00\x00\xff"


# =====================================================================
# present / cut / led / counters
# =====================================================================
def test_present_and_cut():
    p = _p()
    p.present(steps=8, blink_led=True)
    assert bytes(p.transport.buffer) == b"\x1c\x50\x08\x01\x45\x00"
    p.transport.clear()
    p.cut()
    assert bytes(p.transport.buffer) == b"\x1d\x56\x00"


def test_led_helpers():
    p = _p()
    p.led((255, 0, 0))  # FS L immediate colour
    assert bytes(p.transport.buffer) == b"\x1c\x4c\x43\x73\xff\x00\x00"
    p.transport.clear()
    p.led_off()  # FS B OFF (stops any mode incl. flash)
    assert bytes(p.transport.buffer) == b"\x1c\x42\x43"


def test_counter_setup():
    p = _p()
    p.setup_counter(0, 10, step=1, repeat=1, digits=3, align="right", pad_zero=True)
    assert bytes(p.transport.buffer) == (
        b"\x1d\x43\x30\x03\x01"  # print mode
        b"\x1d\x43\x31\x00\x00\x0a\x00\x01\x01"  # count mode
        b"\x1d\x43\x32\x00\x00"  # set counter to start
    )
    p.transport.clear()
    p.print_counter()
    assert bytes(p.transport.buffer) == b"\x1d\x63"


# =====================================================================
# status / queries (responses queued on the dummy transport)
# =====================================================================
def test_status_roundtrip():
    p = _p()
    p.transport.queue_read(b"\x10\x0f\x00\x00\x00\x00")
    st = p.status()
    assert st.ready is True
    assert bytes(p.transport.buffer) == b"\x10\x04\x14"  # the query that was sent


def test_status_error_state():
    p = _p()
    p.transport.queue_read(b"\x10\x0f\x01\x00\x00\x01")  # no paper + cutter error
    st = p.status()
    assert st.paper_present is False
    assert st.cutter_error is True
    assert "paper not present" in st.problems()


def test_paper_status_and_is_ready():
    p = _p()
    p.transport.queue_read(b"\x00")
    assert p.paper_status().paper_present is True
    # is_ready with no reply -> StatusTimeout swallowed -> False
    assert p.is_ready() is False


def test_offline_and_error_status():
    p = _p()
    p.transport.queue_read(b"\x04")  # cover open
    assert p.offline_status()["cover_open"] is True
    p.transport.queue_read(b"\x08")  # cutter error
    assert p.error_status()["cutter_error"] is True


def test_device_id_and_readings():
    p = _p()
    p.transport.queue_read(b"\x02\x05")
    assert p.device_id() == b"\x02\x05"
    p.transport.queue_read(b"7.11")
    assert p.rom_version() == "7.11"
    p.transport.queue_read(b"785cuts")
    assert p.cut_count() == 785
    p.transport.queue_read(b"510cm")
    assert p.paper_remaining_cm() == 510


def test_enable_auto_status_back():
    p = _p()
    p.enable_auto_status_back()
    assert bytes(p.transport.buffer) == b"\x1d\xe0\x0f"


def test_context_manager_closes():
    t = DummyTransport()
    with Printer(t) as p:
        assert p.transport.is_open is True
    assert t.is_open is False


def test_all_wrappers_emit_and_chain():
    """Exercise every chainable wrapper; each must return self and emit bytes."""
    p = _p(paper_width_mm=55, left_offset_dots=24)
    out = (
        p.reset()
        .bold()
        .italic()
        .double_strike()
        .reverse()
        .upside_down()
        .rotate_90()
        .underline(Underline.SINGLE)
        .underline(0)
        .font(Font.A)
        .char_size(2, 2)
        .print_modes(bold=True)
        .right_spacing(2)
        .align_left()
        .align_center()
        .align_right()
        .set_tabs(8, 16)
        .tab()
        .absolute_position(10)
        .relative_position(5)
        .left_margin(8)
        .print_area_width(400)
        .line_spacing()
        .line_spacing(30)
        .line_spacing_tight()
        .charset(CharsetCountry.USA)
        .code_page(CodePage.PC850)
        .feed()
        .feed_units(10)
        .newline(2)
        .collect_mode(True)
        .eject_mode()
        .presentation_offset(5)
        .align_to_printhead()
        .align_to_cutter()
        .black_mark_distance(80)
        .paper_recovery(11)
        .virtual_paper_end(240)
        .min_ticket_length(80)
        .print_quality(PrintQuality.NORMAL)
        .motion_units()
        .enable_keys()
        .density(0)
        .led((1, 2, 3))
        .led_off()
        .led_flash(LedFlashFreq.HZ_2)
        .led_rainbow()
        .print_logo(7)
        .set_print_area()
        .apply_layout()
    )
    assert out is p
    assert len(p.transport.buffer) > 0


def test_2d_and_counter_wrappers():
    p = _p()
    p.aztec("X").pdf417("Y").setup_counter(0, 10, digits=3).print_counter()
    assert len(p.transport.buffer) > 0


def test_queries_full():
    p = _p()
    p.transport.queue_read(b"\x04")  # offline: cover open
    assert p.offline_status()["cover_open"] is True
    p.transport.queue_read(b"\x08")  # error: cutter
    assert p.error_status()["cutter_error"] is True
    p.transport.queue_read(b"7.11")
    assert p.rom_version() == "7.11"
    p.transport.queue_read(b"512on")
    assert p.powerup_count() == 512
    p.transport.queue_read(b"512ret")
    assert p.retract_count() == 512
    p.transport.queue_read(b"38890cm")
    assert p.printed_length_cm() == 38890
    # auto-status-back frame
    p.transport.queue_read(b"\x10\x0f\x00\x00\x00\x00")
    assert p.read_auto_status().ready is True
    assert p.read_auto_status() is None  # nothing pending


def test_logs_and_density():
    p = _p()
    p.transport.queue_read(b"\x04\x00\x00\x00LOGS")  # 4-byte LE size=4, then "LOGS"
    assert p.read_logs() == b"LOGS"
    p.transport.queue_read(b"\x06")  # ACK
    assert p.clear_logs() is True
    p.transport.clear()
    p.density(2)
    assert bytes(p.transport.buffer) == b"\x1d\x7c\x06"  # 0x04 + 2


def test_upload_logo():
    Image = pytest.importorskip("PIL.Image")
    img = Image.new("L", (16, 2), 0)  # 16 px wide (2 bytes, multiple of 16), all black
    p = _p()
    p.transport.queue_read(b"<PC1\xaa>")  # success reply
    assert p.upload_logo(5, img, name="X.BMP", threshold=128) is True
    assert bytes(p.transport.buffer).startswith(b"\x1c\x94\x00\x05\x00\x10\x00\x02")


def test_reset_resyncs_codec():
    p = _p()
    p.code_page(CodePage.WPC1252)
    assert p.encoding == "cp1252"
    p.reset()  # ESC @ reverts the device to PC437
    assert p.encoding == "cp437"


def test_status_short_reply_handled():
    from vkp80iii.exceptions import PrinterError

    p = _p()
    p.transport.queue_read(b"\x10")  # 1-byte (short) reply
    with pytest.raises(PrinterError):
        p.status()
    p.transport.clear()
    p.transport.queue_read(b"\x10")
    assert p.is_ready() is False  # short reply swallowed -> not ready


def test_read_auto_status_partial_frame():
    p = _p()
    # mask 0x03 (paper+user only): 0x10 0x03 <paper=0x01 no paper> <user=0x02 cover open>
    p.transport.queue_read(b"\x10\x03\x01\x02")
    st = p.read_auto_status()
    assert st is not None
    assert st.paper_present is False
    assert st.cover_open is True
    assert st.has_error is False  # recoverable/unrecoverable default to 0


def test_image_chunks_tall_image():
    Image = pytest.importorskip("PIL.Image")
    img = Image.new("L", (8, 2500), 0)  # 2500 rows > the 2047 GS v 0 limit
    p = _p(paper_width_mm=80)
    p.image(img, threshold=128)
    # 2500 rows / 1024-row bands -> 3 separate GS v 0 commands
    assert bytes(p.transport.buffer).count(b"\x1d\x76\x30") == 3
