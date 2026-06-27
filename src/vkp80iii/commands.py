"""Low-level command encoder for the VKP80III (native VKP80III emulation).

Every function here is **pure**: it validates its arguments and returns the
exact byte sequence the printer expects. Nothing in this module performs I/O,
which makes the whole command set unit-testable without hardware.

Byte sequences and ranges follow the *Custom VKP80III Commands Manual*
(doc. 915DX010100, VKP80III emulation chapter). Where the manual contains a
known typo, the code follows the corrected behaviour and a comment points it
out.

The high-level :class:`~vkp80iii.printer.Printer` is a thin convenience layer
on top of these builders; advanced users can call these directly and send the
bytes through any :class:`~vkp80iii.transport.Transport`.
"""

from __future__ import annotations

from .constants import (
    CR,
    DLE,
    EOT,
    ESC,
    FF,
    FS,
    GS,
    HT,
    LF,
    NUL,
    AztecType,
    Barcode,
    CharsetCountry,
    CodePage,
    DataMatrixEncoding,
    Font,
    HRIFont,
    HRIPosition,
    Justify,
    LedFlashFreq,
    LedMode,
    PDF417ErrorMode,
    PrintQuality,
    QRErrorCorrection,
    QRModel,
    StatusType,
    Underline,
)
from .exceptions import CommandError

# =========================================================================
# helpers
# =========================================================================


def _u8(value: int, name: str = "value") -> int:
    if not (0 <= int(value) <= 0xFF):
        raise CommandError(f"{name}={value!r} out of range 0..255")
    return int(value)


def _u16le(value: int, name: str = "value") -> bytes:
    if not (0 <= int(value) <= 0xFFFF):
        raise CommandError(f"{name}={value!r} out of range 0..65535")
    v = int(value)
    return bytes((v & 0xFF, (v >> 8) & 0xFF))


def _u16be(value: int, name: str = "value") -> bytes:
    if not (0 <= int(value) <= 0xFFFF):
        raise CommandError(f"{name}={value!r} out of range 0..65535")
    v = int(value)
    return bytes(((v >> 8) & 0xFF, v & 0xFF))


def _gs_paren_k(cn: int, fn: int, params: bytes = b"") -> bytes:
    """Build a ``GS ( k`` envelope: ``1D 28 6B pL pH cn fn params``.

    ``(pL + pH*256)`` is the number of bytes after ``pH`` (i.e. ``cn``, ``fn``
    and ``params``).
    """
    body = bytes((cn, fn)) + params
    return bytes((GS, 0x28, 0x6B)) + _u16le(len(body), "2D payload length") + body


# =========================================================================
# initialisation / device
# =========================================================================


def initialize() -> bytes:
    """``ESC @`` -- clear print buffer and restore power-on settings."""
    return bytes((ESC, 0x40))


def select_peripheral(enabled: bool = True, passthrough: bool = False) -> bytes:
    """``ESC =`` -- enable/disable this device (bit0) and 2nd-serial pass-through (bit7)."""
    n = (0x01 if enabled else 0x00) | (0x80 if passthrough else 0x00)
    return bytes((ESC, 0x3D, n))


def enable_keys(enabled: bool = True) -> bytes:
    """``ESC c 5`` -- enable/disable the front keys panel.

    Note: once disabled, the panel only comes back after a device reset.
    """
    return bytes((ESC, 0x63, 0x35, 0x00 if enabled else 0x01))


def set_print_quality(quality: PrintQuality | int) -> bytes:
    """``GS 0xF0`` -- select print quality/speed (high quality/normal/high speed)."""
    return bytes((GS, 0xF0, _u8(int(quality), "quality")))


def set_motion_units(x: int = 0, y: int = 0) -> bytes:
    """``GS P`` -- set horizontal (1/x") and vertical (1/y") motion units. 0 = default."""
    return bytes((GS, 0x50, _u8(x, "x"), _u8(y, "y")))


def set_density(n: int = 0x04) -> bytes:
    """``GS |`` (0x1D 0x7C) -- print density. n: 0x02..0x06 = -25%/-12.5%/0%/+12.5%/+25% (0x04 = 0%)."""
    if n not in (0x02, 0x03, 0x04, 0x05, 0x06):
        raise CommandError("density n must be 0x02..0x06")
    return bytes((GS, 0x7C, n))


def data_logger(action: int) -> bytes:
    """``FS G`` (0x1C 0x47) -- 0 = send all flash log files to host, 1 = delete them."""
    if action not in (0, 1):
        raise CommandError("data_logger action must be 0 (send) or 1 (delete)")
    return bytes((FS, 0x47, action))


def set_motion_units_ext(x: int = 0, y: int = 0) -> bytes:
    """``GS 0xD0`` -- 16-bit motion units: horiz 1/x" (x<=2040), vert 1/y" (y<=4080)."""
    if not (0 <= x <= 2040):
        raise CommandError(f"x={x} out of range 0..2040")
    if not (0 <= y <= 4080):
        raise CommandError(f"y={y} out of range 0..4080")
    return bytes((GS, 0xD0)) + _u16be(x) + _u16be(y)


# =========================================================================
# text print / feed
# =========================================================================


def lf() -> bytes:
    """``LF`` -- print buffer and feed one line."""
    return bytes((LF,))


def cr() -> bytes:
    """``CR`` -- print + carriage return (acts like LF only if Autofeed=CR enabled)."""
    return bytes((CR,))


def form_feed() -> bytes:
    """``ESC FF`` -- print the data buffered in page mode."""
    return bytes((ESC, FF))


def feed_units(n: int) -> bytes:
    """``ESC J`` -- print and feed ``n`` vertical motion units."""
    return bytes((ESC, 0x4A, _u8(n, "n")))


def feed_lines(n: int) -> bytes:
    """``ESC d`` -- print and feed ``n`` lines (clamped to 254 by firmware)."""
    return bytes((ESC, 0x64, _u8(n, "n")))


def backspace() -> bytes:
    """``BS`` -- move back one character position (allows overprinting)."""
    return bytes((0x08,))


def horizontal_tab() -> bytes:
    """``HT`` -- advance to the next horizontal tab stop."""
    return bytes((HT,))


# =========================================================================
# line spacing
# =========================================================================


def line_spacing_1_8() -> bytes:
    """``ESC 0`` -- set line spacing to 1/8 inch."""
    return bytes((ESC, 0x30))


def line_spacing_1_6() -> bytes:
    """``ESC 2`` -- set line spacing to 1/6 inch (default)."""
    return bytes((ESC, 0x32))


def set_line_spacing(n: int) -> bytes:
    """``ESC 3`` -- set line spacing to ``n`` vertical motion units."""
    return bytes((ESC, 0x33, _u8(n, "n")))


# =========================================================================
# character / text formatting
# =========================================================================

# ESC ! print-mode bit positions (VKP80III layout; note italic = bit 6).
_PM_FONT_B = 0x01
_PM_BOLD = 0x08
_PM_DOUBLE_HEIGHT = 0x10
_PM_DOUBLE_WIDTH = 0x20
_PM_ITALIC = 0x40
_PM_UNDERLINE = 0x80


def select_print_modes(
    *,
    font_b: bool = False,
    bold: bool = False,
    double_height: bool = False,
    double_width: bool = False,
    italic: bool = False,
    underline: bool = False,
) -> bytes:
    """``ESC !`` -- set several print modes at once (single byte bitmask)."""
    n = 0
    if font_b:
        n |= _PM_FONT_B
    if bold:
        n |= _PM_BOLD
    if double_height:
        n |= _PM_DOUBLE_HEIGHT
    if double_width:
        n |= _PM_DOUBLE_WIDTH
    if italic:
        n |= _PM_ITALIC
    if underline:
        n |= _PM_UNDERLINE
    return bytes((ESC, 0x21, n))


def set_right_spacing(n: int) -> bytes:
    """``ESC SP`` -- set right-side character spacing (n motion units, max ~32 mm)."""
    return bytes((ESC, 0x20, _u8(n, "n")))


def bold(on: bool = True) -> bytes:
    """``ESC E`` -- emphasized (bold) on/off."""
    return bytes((ESC, 0x45, 0x01 if on else 0x00))


def double_strike(on: bool = True) -> bytes:
    """``ESC G`` -- double-strike on/off (visually identical to bold here)."""
    return bytes((ESC, 0x47, 0x01 if on else 0x00))


def italic(on: bool = True) -> bytes:
    """``ESC 4`` -- italic on/off."""
    return bytes((ESC, 0x34, 0x01 if on else 0x00))


def underline(mode: Underline | int = Underline.SINGLE) -> bytes:
    """``ESC -`` -- underline off/1-dot/2-dot."""
    m = int(mode)
    if m not in (0, 1, 2):
        raise CommandError(f"underline mode {m} must be 0, 1 or 2")
    return bytes((ESC, 0x2D, m))


def upside_down(on: bool = True) -> bytes:
    """``ESC {`` -- upside-down (180°) printing. Only valid at line start."""
    return bytes((ESC, 0x7B, 0x01 if on else 0x00))


def rotate_90(on: bool = True) -> bytes:
    """``ESC V`` -- 90° clockwise rotated print mode."""
    return bytes((ESC, 0x56, 0x01 if on else 0x00))


def reverse(on: bool = True) -> bytes:
    """``GS B`` -- white-on-black reverse printing."""
    return bytes((GS, 0x42, 0x01 if on else 0x00))


def select_font(font: Font | int) -> bytes:
    """``ESC M`` -- select character font A/B (cell size also depends on pitch)."""
    f = int(font)
    if f not in (0, 1):
        raise CommandError(f"font {f} must be Font.A (0) or Font.B (1)")
    return bytes((ESC, 0x4D, f))


def select_charset(country: CharsetCountry | int) -> bytes:
    """``ESC R`` -- select an international character set (0..10)."""
    n = int(country)
    if not (0 <= n <= 0x0A):
        raise CommandError(f"charset {n} out of range 0..10")
    return bytes((ESC, 0x52, n))


def select_code_page(page: CodePage | int) -> bytes:
    """``ESC t`` -- select the active code page for the International font."""
    return bytes((ESC, 0x74, _u8(int(page), "code page")))


def char_size(width: int = 1, height: int = 1) -> bytes:
    """``GS !`` -- set character width/height multiplier (each 1..8)."""
    if not (1 <= width <= 8):
        raise CommandError(f"width {width} must be 1..8")
    if not (1 <= height <= 8):
        raise CommandError(f"height {height} must be 1..8")
    n = ((width - 1) << 4) | (height - 1)
    return bytes((GS, 0x21, n))


# =========================================================================
# positioning / justification / margins
# =========================================================================


def justify(mode: Justify | int) -> bytes:
    """``ESC a`` -- left/center/right justification."""
    m = int(mode)
    if m not in (0, 1, 2):
        raise CommandError(f"justify {m} must be 0, 1 or 2")
    return bytes((ESC, 0x61, m))


def set_absolute_position(n: int) -> bytes:
    """``ESC $`` -- set absolute horizontal print position (n motion units from line start)."""
    return bytes((ESC, 0x24)) + _u16le(n, "position")


def set_relative_position(n: int) -> bytes:
    """``ESC \\`` -- move print position relative to current (negative => 65536+n)."""
    if n < 0:
        n += 0x10000
    return bytes((ESC, 0x5C)) + _u16le(n, "offset")


def set_tab_stops(*columns: int) -> bytes:
    """``ESC D`` -- set up to 32 horizontal tab stops (ascending columns); none clears all.

    The printer stops parsing tab stops at the first value that is not greater
    than the previous one, so columns must be strictly ascending.
    """
    cols = [int(c) for c in columns]
    if len(cols) > 32:
        raise CommandError("at most 32 tab stops allowed")
    for c in cols:
        if not (1 <= c <= 0xFF):
            raise CommandError(f"tab column {c} out of range 1..255")
    if any(b <= a for a, b in zip(cols, cols[1:], strict=False)):
        raise CommandError("tab columns must be strictly ascending")
    return bytes((ESC, 0x44)) + bytes(cols) + bytes((NUL,))


def set_left_margin(n: int) -> bytes:
    """``GS L`` -- set left margin (n horizontal motion units). Valid at line start."""
    return bytes((GS, 0x4C)) + _u16le(n, "margin")


def set_print_area_width(n: int) -> bytes:
    """``GS W`` -- set printing-area width (n horizontal motion units; 0 = max)."""
    if not (0 <= n <= 640):
        raise CommandError(f"width {n} out of range 0..640")
    return bytes((GS, 0x57)) + _u16le(n, "width")


# =========================================================================
# cutting
# =========================================================================


def cut(feed: int | None = None) -> bytes:
    """``GS V`` -- total cut.

    * ``cut()`` -> total cut at the current position (``GS V 0``).
    * ``cut(feed=n)`` -> feed ``n`` motion units, then total cut (``GS V 65 n``).

    The VKP80III only supports a total cut (there is no partial cut); the
    manual's alignment workflow uses :func:`total_cut` (``ESC i``).
    """
    if feed is None:
        return bytes((GS, 0x56, 0x00))
    return bytes((GS, 0x56, 0x41, _u8(feed, "feed")))


def total_cut() -> bytes:
    """``ESC i`` -- total cut (the cut used in the manual's alignment workflows)."""
    return bytes((ESC, 0x69))


# =========================================================================
# black-mark alignment / mechanism
# =========================================================================


def set_black_mark_distance(tenths_mm: int) -> bytes:
    """``GS 0xE7`` -- alignment-point distance from black-mark edge, in 1/10 mm.

    Range -50..+999 (1/10 mm), i.e. -5 mm .. +99.9 mm. Stored in NVRAM with a
    limited number of write cycles -- do **not** send this per ticket.

    Byte order follows the manual's worked examples (high/sign byte first),
    which contradict the printed [Format]; see the manual note.
    """
    if not (-50 <= tenths_mm <= 999):
        raise CommandError(f"distance {tenths_mm} out of range -50..999 (1/10 mm)")
    if tenths_mm >= 0:
        hi, lo = (tenths_mm >> 8) & 0x7F, tenths_mm & 0xFF
    else:
        mag = -tenths_mm
        hi, lo = 0x80 | ((mag >> 8) & 0x7F), mag & 0xFF
    return bytes((GS, 0xE7, hi, lo))


def align_to_printhead() -> bytes:
    """``GS 0xF6`` -- feed until the black mark aligns under the print head (start of ticket)."""
    return bytes((GS, 0xF6))


def align_to_cutter() -> bytes:
    """``GS 0xF8`` -- feed until the black mark aligns at the cutter (end of ticket)."""
    return bytes((GS, 0xF8))


def paper_recovery(mm: int = 11) -> bytes:
    """``FS C1`` -- pull the post-cut stub back toward the head (0..11 mm, 11 = full)."""
    if not (0 <= mm <= 11):
        raise CommandError(f"recovery {mm} out of range 0..11 mm")
    return bytes((FS, 0xC1, mm))


def set_virtual_paper_end(cm: int) -> bytes:
    """``GS 0xE6`` -- residual paper length (cm) after low-paper before virtual paper-end."""
    return bytes((GS, 0xE6)) + _u16be(cm, "cm")


def set_min_ticket_length(mm: int) -> bytes:
    """``GS 0xE8`` -- minimum ticket length in mm (54..255; default 70)."""
    if not (54 <= mm <= 255):
        raise CommandError(f"length {mm} out of range 54..255 mm")
    return bytes((GS, 0xE8, mm))


# =========================================================================
# presenter / ejector (Custom-specific output handling)
# =========================================================================


def collect_mode(enabled: bool) -> bytes:
    """``ESC C`` -- COLLECT mode: print uncut tickets into the bin; disabling cuts the batch."""
    return bytes((ESC, 0x43, 0x01 if enabled else 0x00))


def eject_mode() -> bytes:
    """``ESC F`` -- enable EJECT (dispenser-continuous) mode; closed by ``present_ticket``."""
    return bytes((ESC, 0x46))


def set_presentation_offset(mm: int) -> bytes:
    """``FS K`` -- extra presentation offset (mm) added to the fixed 150 mm loop in EJECT mode."""
    return bytes((FS, 0x4B, _u8(mm, "mm")))


def present_ticket(
    steps: int = 2,
    *,
    blink_led: bool = False,
    retract: bool = False,
    timeout_s: int = 0,
) -> bytes:
    """``FS P`` -- cut and present the ticket at the bezel.

    * ``steps`` -- presentation length in 5 mm steps.
    * ``blink_led`` -- blink the bezel mouth LED while presented.
    * ``retract`` -- after ``timeout_s`` retract (True) or eject (False).
      Retract falls back to eject if disabled in the printer setup.
    * ``timeout_s`` -- seconds to wait before eject/retract; 0 = hold until the
      next print job.
    """
    c = 0x52 if retract else 0x45  # 'R' / 'E'
    return bytes((FS, 0x50, _u8(steps, "steps"), 0x01 if blink_led else 0x00, c, _u8(timeout_s, "timeout_s")))


# =========================================================================
# status / queries (printer transmits a reply)
# =========================================================================


def request_status(kind: StatusType | int = StatusType.PRINTER) -> bytes:
    """``DLE EOT n`` -- real-time status request (replied to even when busy)."""
    return bytes((DLE, EOT, _u8(int(kind), "status type")))


def request_full_status() -> bytes:
    """``DLE EOT 0x14`` -- request the 6-byte full status block."""
    return bytes((DLE, EOT, 0x14))


def transmit_paper_sensor() -> bytes:
    """``ESC v`` -- transmit the 1-byte paper-sensor status (near-end + end)."""
    return bytes((ESC, 0x76))


def auto_status_back(
    paper: bool = False,
    user: bool = False,
    recoverable: bool = False,
    unrecoverable: bool = False,
) -> bytes:
    """``GS 0xE0`` -- enable/disable unsolicited automatic full-status-back per category."""
    n = (
        (0x01 if paper else 0)
        | (0x02 if user else 0)
        | (0x04 if recoverable else 0)
        | (0x08 if unrecoverable else 0)
    )
    return bytes((GS, 0xE0, n))


def transmit_device_id(n: int = 0xFF) -> bytes:
    """``GS I`` -- transmit device id/type/ROM version (n: 1/2/3 or 0xFF)."""
    return bytes((GS, 0x49, _u8(n, "n")))


def read_paper_remaining() -> bytes:
    """``GS 0xE1`` -- transmit remaining paper before virtual paper-end, e.g. ``b'510cm'``."""
    return bytes((GS, 0xE1))


def read_cut_count() -> bytes:
    """``GS 0xE2`` -- transmit total autocutter cuts, e.g. ``b'785cuts'``."""
    return bytes((GS, 0xE2))


def read_printed_length() -> bytes:
    """``GS 0xE3`` -- transmit total printed paper length, e.g. ``b'38890cm'``."""
    return bytes((GS, 0xE3))


def read_retract_count() -> bytes:
    """``GS 0xE4`` -- transmit number of retractions, e.g. ``b'512ret'``."""
    return bytes((GS, 0xE4))


def read_powerup_count() -> bytes:
    """``GS 0xE5`` -- transmit number of power-ups, e.g. ``b'512on'``."""
    return bytes((GS, 0xE5))


# =========================================================================
# bezel RGB LED bar
# =========================================================================


def led_bar(mode: LedMode | int, freq: LedFlashFreq | int | None = None) -> bytes:
    """``FS B`` -- LED bar on/off/steady/reset; ``freq`` required for FLASH mode."""
    m = int(mode)
    if m == int(LedMode.FLASH):
        if freq is None:
            raise CommandError("LedMode.FLASH requires a freq argument")
        return bytes((FS, 0x42, m, int(freq)))
    return bytes((FS, 0x42, m))


# FS L sub-targets / operations
_LED_BG = 0x42
_LED_IMMEDIATE = 0x43
_LED_DEFAULTS = 0x44
_LED_FG = 0x46
_LED_RAINBOW = 0x52
_LED_OP_WRITE_RAM_ON = 0x73
_LED_OP_WRITE_RAM = 0x77
_LED_OP_WRITE_FLASH = 0x57


def _led_op(persist: bool) -> int:
    """FS L write op: FLASH (persists) or RAM (this session only)."""
    return _LED_OP_WRITE_FLASH if persist else _LED_OP_WRITE_RAM


def _rgb(rgb: tuple[int, int, int]) -> bytes:
    r, g, b = rgb
    return bytes((_u8(r, "r"), _u8(g, "g"), _u8(b, "b")))


def led_color(
    rgb: tuple[int, int, int],
    *,
    target: str = "immediate",
    persist: bool = False,
) -> bytes:
    """``FS L`` -- set an LED bar colour.

    * ``target`` -- ``"immediate"`` (turn the bar on now in this colour),
      ``"background"`` or ``"foreground"`` (used by flashing / shown after
      ``present_ticket``).
    * ``persist`` -- write to FLASH (survives power-off) instead of RAM. Only
      meaningful for ``"background"``/``"foreground"``; for ``"immediate"`` the
      bar is always turned on now (RAM) and ``persist`` is ignored, since there
      is no single op that both lights the bar and writes flash.
    """
    targets = {"background": _LED_BG, "foreground": _LED_FG, "immediate": _LED_IMMEDIATE}
    if target not in targets:
        raise CommandError(f"target must be one of {sorted(targets)}")
    # "immediate" always turns the bar on now; persist applies to bg/fg only
    op = _LED_OP_WRITE_RAM_ON if target == "immediate" else _led_op(persist)
    return bytes((FS, 0x4C, targets[target], op)) + _rgb(rgb)


def led_off() -> bytes:
    """``FS B`` -- turn the LED bar off, stopping any mode (incl. a ``led_bar``
    FLASH). The ``FS L`` colour-off (``0x6d``) does **not** stop an ``FS B``
    flash, so "off" must go through ``FS B``."""
    return led_bar(LedMode.OFF)


def led_rainbow(enabled: bool = True, *, persist: bool = False) -> bytes:
    """``FS L`` -- enable/disable rainbow mode (cycled during ticket presentation)."""
    op = _led_op(persist)
    return bytes((FS, 0x4C, _LED_RAINBOW, op, 0x01 if enabled else 0x00))


def led_defaults() -> bytes:
    """``FS L`` -- restore default LED colours (fg violet, bg green)."""
    return bytes((FS, 0x4C, _LED_DEFAULTS, 0x00))


# =========================================================================
# logo / graphics
# =========================================================================


def print_logo(
    number: int,
    *,
    justify: Justify | int = Justify.LEFT,
    rotate: bool = False,
    border_dots: int = 0,
    position_dots: int | None = None,
) -> bytes:
    """``FS 0x93`` -- print a stored logo by its 2-byte id.

    ``position_dots`` selects user-defined horizontal placement (overrides
    ``justify``).
    """
    if not (0 <= number <= 0xFFFF):
        raise CommandError(f"logo number {number} out of range 0..65535")
    if position_dots is not None:
        opt = 0x03
        pos = _u16le(position_dots, "position_dots")
    else:
        opt = int(justify) & 0x03
        pos = b"\x00\x00"
    if rotate:
        opt |= 0x80
    return bytes((FS, 0x93)) + _u16be(number) + bytes((opt, _u8(border_dots, "border_dots"))) + pos


def store_logo_flash(
    number: int,
    width: int,
    height: int,
    data: bytes,
    name: str = "LOGO.BMP",
) -> bytes:
    """``FS 0x94`` -- store a 1-bit image into flash as logo ``number``.

    * ``width`` must be a multiple of 16 (pixels).
    * ``data`` -- ``(width // 8) * height`` bytes, row-major, MSB = leftmost
      dot, 1 = black (same packing as :func:`raster_image`).
    * ``name`` -- up to 16 bytes, NUL-padded (an extension is added by the
      device if absent).

    The printer replies ``<PC1\\xAA>`` on success / ``<PC0>`` on failure; use
    :meth:`vkp80iii.printer.Printer.upload_logo`, which reads and checks it.
    """
    if not (0 <= number <= 0xFFFF):
        raise CommandError("logo number out of range 0..65535")
    if width <= 0 or width % 16 != 0:
        raise CommandError("width must be a positive multiple of 16")
    if not (1 <= height <= 0xFFFF):
        raise CommandError("height out of range 1..65535")
    expected = (width // 8) * height
    if len(data) != expected:
        raise CommandError(f"data is {len(data)} bytes, expected (width/8)*height = {expected}")
    name_bytes = name.encode("ascii", "replace")[:16]
    name_bytes += b"\x00" * (16 - len(name_bytes))
    buf = bytearray((FS, 0x94))
    buf += _u16be(number) + _u16be(width) + _u16be(height) + b"\x00\x00"
    buf += name_bytes
    buf += data
    buf.append(0x3E)
    return bytes(buf)


def print_graphic_bank(source: int, start_line: int = 1, num_lines: int = 862) -> bytes:
    """``ESC 0xFA`` -- print a graphic page/logo (source 0=RAM page, 1=logo1, 2=logo2).

    The graphic area is 862 dot lines tall; ``start_line`` + ``num_lines`` must
    stay within it.
    """
    if source not in (0, 1, 2):
        raise CommandError("source must be 0 (RAM), 1 (logo1) or 2 (logo2)")
    if not (1 <= start_line <= 862):
        raise CommandError(f"start_line {start_line} out of range 1..862")
    if not (1 <= num_lines <= 862):
        raise CommandError(f"num_lines {num_lines} out of range 1..862")
    if start_line + num_lines - 1 > 862:
        raise CommandError("start_line + num_lines exceeds the 862-dot graphic area")
    return bytes((ESC, 0xFA, source)) + _u16be(start_line) + _u16be(num_lines)


# =========================================================================
# images (raster / bit image)
# =========================================================================


def raster_image(width_bytes: int, height: int, data: bytes, mode: int = 0) -> bytes:
    """``GS v 0`` -- print a raster (row-major) bit image.

    * ``width_bytes`` -- bytes per row = ceil(width_in_dots / 8).
    * ``height`` -- number of dot rows.
    * ``data`` -- ``width_bytes * height`` bytes, MSB = leftmost dot, 1 = black.
    * ``mode`` -- 0 normal, 1 double-width, 2 double-height, 3 quadruple.
    """
    if mode not in (0, 1, 2, 3):
        raise CommandError("mode must be 0..3")
    if not (1 <= width_bytes <= 0xFFFF):
        raise CommandError("width_bytes out of range 1..65535")
    if not (1 <= height <= 2047):
        raise CommandError("height out of range 1..2047")
    expected = width_bytes * height
    if len(data) != expected:
        raise CommandError(f"data is {len(data)} bytes, expected width_bytes*height = {expected}")
    return (
        bytes((GS, 0x76, 0x30, mode))
        + _u16le(width_bytes, "width_bytes")
        + _u16le(height, "height")
        + bytes(data)
    )


def define_downloaded_bit_image(x_bytes: int, y_bytes: int, data: bytes) -> bytes:
    """``GS *`` -- define the downloaded bit image (x_bytes*y_bytes <= 1536)."""
    if not (1 <= x_bytes <= 0xFF):
        raise CommandError("x_bytes out of range 1..255")
    if not (1 <= y_bytes <= 0x30):
        raise CommandError("y_bytes out of range 1..48")
    if x_bytes * y_bytes > 1536:
        raise CommandError("x_bytes * y_bytes must be <= 1536")
    expected = x_bytes * y_bytes * 8
    if len(data) != expected:
        raise CommandError(f"data is {len(data)} bytes, expected x*y*8 = {expected}")
    return bytes((GS, 0x2A, x_bytes, y_bytes)) + bytes(data)


def print_downloaded_bit_image(mode: int = 0) -> bytes:
    """``GS /`` -- print the image defined by ``define_downloaded_bit_image`` (mode 0..3)."""
    if mode not in (0, 1, 2, 3):
        raise CommandError("mode must be 0..3")
    return bytes((GS, 0x2F, mode))


# =========================================================================
# 1D barcodes
# =========================================================================


def set_barcode_height(dots: int) -> bytes:
    """``GS h`` -- set 1D barcode height in dots (1..255; default 162)."""
    if not (1 <= dots <= 0xFF):
        raise CommandError("height out of range 1..255 dots")
    return bytes((GS, 0x68, dots))


def set_barcode_width(module: int) -> bytes:
    """``GS w`` -- set 1D barcode module width (1..6; default 3)."""
    if not (1 <= module <= 6):
        raise CommandError("module width out of range 1..6")
    return bytes((GS, 0x77, module))


def set_hri_position(position: HRIPosition | int) -> bytes:
    """``GS H`` -- set HRI text position (none/above/below/both)."""
    p = int(position)
    if p not in (0, 1, 2, 3):
        raise CommandError("HRI position must be 0..3")
    return bytes((GS, 0x48, p))


def set_hri_font(font: HRIFont | int) -> bytes:
    """``GS f`` -- set HRI text font A/B."""
    f = int(font)
    if f not in (0, 1):
        raise CommandError("HRI font must be 0 or 1")
    return bytes((GS, 0x66, f))


# Length rules (min, max) per symbology, used to validate data before sending.
_BARCODE_RULES: dict[int, tuple[int, int]] = {
    Barcode.UPC_A: (11, 12),
    Barcode.UPC_E: (11, 12),
    Barcode.EAN13: (12, 13),
    Barcode.EAN8: (7, 8),
    Barcode.CODE39: (1, 255),
    Barcode.ITF: (2, 254),
    Barcode.CODABAR: (2, 255),
    Barcode.CODE93: (1, 255),
    Barcode.CODE128: (2, 255),
    Barcode.CODE32: (8, 9),
}

# Symbologies that accept ASCII digits 0-9 only.
_BARCODE_NUMERIC = frozenset(
    {Barcode.UPC_A, Barcode.UPC_E, Barcode.EAN13, Barcode.EAN8, Barcode.ITF, Barcode.CODE32}
)


def barcode(symbology: Barcode | int, data: bytes | str) -> bytes:
    """``GS k`` -- print a 1D barcode (length-prefixed "format 2" form).

    For CODE128 the data must begin with a code-set selector, e.g. ``"{B"``
    before ASCII text. ``str`` data is encoded as Latin-1. Data length and (for
    the numeric symbologies) the digits-only character set are validated.
    """
    if isinstance(data, str):
        data = data.encode("latin-1")
    m = _u8(int(symbology), "symbology")
    rule = _BARCODE_RULES.get(m)
    if rule is not None:
        lo, hi = rule
        if not (lo <= len(data) <= hi):
            raise CommandError(
                f"barcode data length {len(data)} out of range {lo}..{hi} for symbology 0x{m:02X}"
            )
    if m in _BARCODE_NUMERIC and not all(0x30 <= b <= 0x39 for b in data):
        raise CommandError(f"symbology 0x{m:02X} accepts ASCII digits 0-9 only")
    if m == int(Barcode.ITF) and len(data) % 2:
        raise CommandError("ITF requires an even number of digits")
    if len(data) > 255:
        raise CommandError("barcode data too long (max 255 bytes)")
    return bytes((GS, 0x6B, m, len(data))) + data


# =========================================================================
# 2D barcodes -- PDF417
# =========================================================================

_PDF417 = 0x30


def pdf417_columns(n: int = 0) -> bytes:
    """``GS ( k`` Fn065 -- PDF417 data columns (0 = auto, 1..30)."""
    if not (0 <= n <= 30):
        raise CommandError("columns out of range 0..30")
    return _gs_paren_k(_PDF417, 0x41, bytes((n,)))


def pdf417_rows(n: int = 0) -> bytes:
    """``GS ( k`` Fn066 -- PDF417 rows (0 = auto, else 3..20)."""
    if n != 0 and not (3 <= n <= 20):
        raise CommandError("rows must be 0 (auto) or 3..20")
    return _gs_paren_k(_PDF417, 0x42, bytes((n,)))


def pdf417_module_width(n: int = 3) -> bytes:
    """``GS ( k`` Fn067 -- PDF417 module width (2..8)."""
    if not (2 <= n <= 8):
        raise CommandError("module width out of range 2..8")
    return _gs_paren_k(_PDF417, 0x43, bytes((n,)))


def pdf417_module_height(n: int = 3) -> bytes:
    """``GS ( k`` Fn068 -- PDF417 module height (2..8)."""
    if not (2 <= n <= 8):
        raise CommandError("module height out of range 2..8")
    return _gs_paren_k(_PDF417, 0x44, bytes((n,)))


def pdf417_error_correction(value: int = 1, mode: PDF417ErrorMode | int = PDF417ErrorMode.RATIO) -> bytes:
    """``GS ( k`` Fn069 -- PDF417 ECC by fixed level (0..8) or ratio (1..40 => n*10%)."""
    m = int(mode)
    if m == int(PDF417ErrorMode.LEVEL):
        if not (0 <= value <= 8):
            raise CommandError("ECC level out of range 0..8")
        n = 0x30 + value
    else:
        if not (1 <= value <= 40):
            raise CommandError("ECC ratio out of range 1..40")
        n = value
    return _gs_paren_k(_PDF417, 0x45, bytes((m, n)))


def pdf417_store(data: bytes) -> bytes:
    """``GS ( k`` Fn080 -- store PDF417 data in the symbol save area."""
    return _gs_paren_k(_PDF417, 0x50, bytes((0x30,)) + bytes(data))


def pdf417_print() -> bytes:
    """``GS ( k`` Fn081 -- encode and print the stored PDF417 data."""
    return _gs_paren_k(_PDF417, 0x51, bytes((0x30,)))


# =========================================================================
# 2D barcodes -- QR Code
# =========================================================================

_QR = 0x31


def qr_model(model: QRModel | int = QRModel.MODEL2) -> bytes:
    """``GS ( k`` Fn165 -- QR model (Model 2 / MicroQR)."""
    return _gs_paren_k(_QR, 0x41, bytes((int(model), 0x00)))


def qr_version(n: int = 0) -> bytes:
    """``GS ( k`` Fn166 -- QR version (0 = auto, 1..40)."""
    if not (0 <= n <= 40):
        raise CommandError("QR version out of range 0..40")
    return _gs_paren_k(_QR, 0x42, bytes((n,)))


def qr_module_size(n: int = 6) -> bytes:
    """``GS ( k`` Fn167 -- QR module dot size (2..24)."""
    if not (2 <= n <= 24):
        raise CommandError("QR module size out of range 2..24")
    return _gs_paren_k(_QR, 0x43, bytes((n,)))


def qr_error_correction(level: QRErrorCorrection | int = QRErrorCorrection.M) -> bytes:
    """``GS ( k`` Fn169 -- QR error-correction level (AUTO/L/M/Q/H)."""
    return _gs_paren_k(_QR, 0x45, bytes((int(level),)))


def qr_store(data: bytes) -> bytes:
    """``GS ( k`` Fn180 -- store QR data in the symbol save area."""
    return _gs_paren_k(_QR, 0x50, bytes((0x31,)) + bytes(data))


def qr_print() -> bytes:
    """``GS ( k`` Fn181 -- print the stored QR data."""
    return _gs_paren_k(_QR, 0x51, bytes((0x31,)))


def qr_transmit_size() -> bytes:
    """``GS ( k`` Fn182 -- transmit the size of the stored QR symbol."""
    return _gs_paren_k(_QR, 0x52, bytes((0x30,)))


# =========================================================================
# 2D barcodes -- AZTEC
# =========================================================================

_AZTEC = 0x50


def aztec_type(t: AztecType | int = AztecType.FULL) -> bytes:
    """``GS ( k`` FnP65 -- AZTEC type (full / rune)."""
    return _gs_paren_k(_AZTEC, 0x41, bytes((int(t),)))


def aztec_module_size(n: int = 6) -> bytes:
    """``GS ( k`` FnP67 -- AZTEC module dot size (2..24)."""
    if not (2 <= n <= 24):
        raise CommandError("AZTEC module size out of range 2..24")
    return _gs_paren_k(_AZTEC, 0x43, bytes((n,)))


def aztec_size(n: int = 0) -> bytes:
    """``GS ( k`` FnP68 -- AZTEC layout/size (0 = auto, 1..36)."""
    if not (0 <= n <= 0x24):
        raise CommandError("AZTEC size out of range 0..36")
    return _gs_paren_k(_AZTEC, 0x44, bytes((n,)))


def aztec_error_correction(n: int = 0) -> bytes:
    """``GS ( k`` FnP69 -- AZTEC error correction (0 = auto, 1..4)."""
    if not (0 <= n <= 4):
        raise CommandError("AZTEC ECC out of range 0..4")
    return _gs_paren_k(_AZTEC, 0x45, bytes((n,)))


def aztec_store(data: bytes) -> bytes:
    """``GS ( k`` FnP80 -- store AZTEC data in the symbol save area."""
    return _gs_paren_k(_AZTEC, 0x50, bytes((0x34,)) + bytes(data))


def aztec_print() -> bytes:
    """``GS ( k`` FnP81 -- print the stored AZTEC data."""
    return _gs_paren_k(_AZTEC, 0x51, bytes((0x30,)))


# =========================================================================
# 2D barcodes -- DataMatrix
# =========================================================================

_DATAMATRIX = 0x51


def datamatrix_encoding(enc: DataMatrixEncoding | int = DataMatrixEncoding.AUTO) -> bytes:
    """``GS ( k`` FnQ65 -- DataMatrix encoding scheme."""
    return _gs_paren_k(_DATAMATRIX, 0x41, bytes((int(enc),)))


def datamatrix_rotation(rotate: bool = False) -> bytes:
    """``GS ( k`` FnQ66 -- DataMatrix rotation on/off."""
    return _gs_paren_k(_DATAMATRIX, 0x42, bytes((0x01 if rotate else 0x00,)))


def datamatrix_module_size(n: int = 6) -> bytes:
    """``GS ( k`` FnQ67 -- DataMatrix module dot size (2..24)."""
    if not (2 <= n <= 24):
        raise CommandError("DataMatrix module size out of range 2..24")
    return _gs_paren_k(_DATAMATRIX, 0x43, bytes((n,)))


def datamatrix_size(n: int = 0) -> bytes:
    """``GS ( k`` FnQ68 -- DataMatrix symbol size (0 = auto, 1..29)."""
    if not (0 <= n <= 0x1D):
        raise CommandError("DataMatrix size out of range 0..29")
    return _gs_paren_k(_DATAMATRIX, 0x44, bytes((n,)))


def datamatrix_store(data: bytes) -> bytes:
    """``GS ( k`` FnQ80 -- store DataMatrix data in the symbol save area."""
    return _gs_paren_k(_DATAMATRIX, 0x50, bytes((0x33,)) + bytes(data))


def datamatrix_print() -> bytes:
    """``GS ( k`` FnQ81 -- encode and print the stored DataMatrix data."""
    return _gs_paren_k(_DATAMATRIX, 0x51, bytes((0x33,)))


# =========================================================================
# counters
# =========================================================================


def counter_print_mode(digits: int = 0, align: str = "right", pad_zero: bool = False) -> bytes:
    """``GS C 0`` -- counter print format: digit count, alignment, zero-padding."""
    if not (0 <= digits <= 5):
        raise CommandError("digits out of range 0..5")
    if align == "left":
        m = 0x02
    elif align == "right":
        m = 0x01 if pad_zero else 0x00
    else:
        raise CommandError("align must be 'left' or 'right'")
    return bytes((GS, 0x43, 0x30, digits, m))


def counter_mode(start: int, end: int, step: int = 1, repeat: int = 1) -> bytes:
    """``GS C 1`` -- counter range/step/repeat (start<end counts up, start>end counts down)."""
    return (
        bytes((GS, 0x43, 0x31))
        + _u16le(start, "start")
        + _u16le(end, "end")
        + bytes((_u8(step, "step"), _u8(repeat, "repeat")))
    )


def set_counter(value: int) -> bytes:
    """``GS C 2`` -- set the current counter value."""
    return bytes((GS, 0x43, 0x32)) + _u16le(value, "value")


def print_counter() -> bytes:
    """``GS c`` -- queue the current counter value for printing and advance it."""
    return bytes((GS, 0x63))


# =========================================================================
# macros
# =========================================================================


def macro_define_start_end() -> bytes:
    """``GS :`` -- start (or end) macro definition."""
    return bytes((GS, 0x3A))


def macro_execute(times: int, delay: int, mode: int = 0) -> bytes:
    """``GS ^`` -- execute the macro ``times`` times with ``delay`` (x100 ms) between runs."""
    return bytes((GS, 0x5E, _u8(times, "times"), _u8(delay, "delay"), _u8(mode, "mode")))
