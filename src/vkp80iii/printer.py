"""High-level, ergonomic API for the Custom VKP80III.

:class:`Printer` wraps a :class:`~vkp80iii.transport.Transport` and the pure
byte builders in :mod:`vkp80iii.commands`. Formatting/print methods are
chainable (they return ``self``); query methods return decoded values.

Example::

    from vkp80iii import Printer, Justify

    with Printer() as p:                 # opens /dev/usb/lp0
        p.align(Justify.CENTER).bold().textln("CAFE DEMO").bold(False)
        p.textln("------------------------")
        p.align(Justify.LEFT).textln("1x Espresso      2.50")
        p.qrcode("https://example.com")
        p.feed(3).present()              # cut + present the ticket
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import commands as c
from .constants import (
    DOTS_PER_MM,
    MAX_DOTS,
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
    PrintQuality,
    QRErrorCorrection,
    QRModel,
    StatusType,
    Underline,
)
from .exceptions import CommandError, PrinterError, StatusTimeout
from .status import (
    FullStatus,
    PaperStatus,
    decode_error_status,
    decode_offline_status,
    parse_reading,
)
from .transport import Transport, UsbLpTransport

if TYPE_CHECKING:  # pragma: no cover
    from PIL import Image

#: Code page -> Python codec used to encode text for that page.
_CODEPAGE_CODEC: dict[int, str] = {
    CodePage.PC437: "cp437",
    CodePage.PC850: "cp850",
    CodePage.PC860: "cp860",
    CodePage.PC863: "cp863",
    CodePage.PC865: "cp865",
    CodePage.WPC1252: "cp1252",
    CodePage.PC866: "cp866",
    CodePage.PC852: "cp852",
    CodePage.PC858: "cp858",
}


def _payload(data: bytes | str) -> bytes:
    """Coerce 2D-barcode data to bytes (str is UTF-8)."""
    return data.encode("utf-8") if isinstance(data, str) else bytes(data)


def _pad_rows(
    data: bytes, width_bytes: int, height: int, *, left: int = 0, right: int = 0
) -> tuple[bytes, int]:
    """Add ``left``/``right`` zero filler bytes to each row of a packed raster.

    Returns ``(padded_data, new_width_bytes)``. Builds one zero-filled buffer and
    copies each row into place (the filler bytes come for free), avoiding the
    per-row allocate-and-join.
    """
    if not (left or right):
        return data, width_bytes
    new_wb = width_bytes + left + right
    out = bytearray(new_wb * height)
    src = memoryview(data)
    for i in range(height):
        start = i * new_wb + left
        out[start : start + width_bytes] = src[i * width_bytes : (i + 1) * width_bytes]
    return bytes(out), new_wb


class Printer:
    """A connected VKP80III printer.

    :param transport: any :class:`~vkp80iii.transport.Transport`; defaults to
        :class:`~vkp80iii.transport.UsbLpTransport` (``/dev/usb/lp0``).
    :param codepage: initial code page, also used to pick the text codec.
    :param auto_open: open the transport immediately (default True).
    """

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        codepage: CodePage | int = CodePage.PC437,
        paper_width_mm: float = 80.0,
        left_offset_dots: int = 0,
        auto_open: bool = True,
    ) -> None:
        self.transport: Transport = transport if transport is not None else UsbLpTransport()
        self._codepage = int(codepage)
        self._encoding = _CODEPAGE_CODEC.get(self._codepage, "cp437")
        self.paper_width_mm = paper_width_mm
        #: Usable print width in dots for this paper (capped at the head's 576).
        self.width_dots = min(MAX_DOTS, int(round(paper_width_mm * DOTS_PER_MM)))
        #: Horizontal offset (dots) from the printer's logical origin to the
        #: paper's left edge. Depends on the printer's PRINT WIDTH setup value
        #: and where the paper guides hold the (centered) roll. Constant per
        #: paper width; measure once with the ruler in ``calib.py``.
        self.left_offset_dots = left_offset_dots
        if auto_open and not self.transport.is_open:
            self.transport.open()

    @classmethod
    def for_paper(
        cls,
        transport: Transport | None = None,
        *,
        width_mm: float,
        margin_mm: float = 1.5,
        codepage: CodePage | int = CodePage.PC437,
        auto_open: bool = True,
    ) -> Printer:
        """Build a Printer centered on a ``width_mm`` roll (the recommended setup).

        Assumes the firmware ``PRINT WIDTH`` matches the paper, so the logical
        origin is the paper's left edge (see the README "Narrow paper" section).
        ``margin_mm`` is inset on *each* side: the print area becomes
        ``width_mm - 2 * margin_mm`` and content is centered via
        ``left_offset_dots = round(margin_mm * DOTS_PER_MM)``. The margin also
        keeps left-aligned text off the head's physical non-printable left edge
        (offset 0 clips the first column by 1-2 px).

        This is the convenient counterpart to passing ``paper_width_mm`` +
        ``left_offset_dots`` yourself; use those directly for the software
        fallback where the firmware ``PRINT WIDTH`` is *not* matched to the paper
        and the offset is measured with ``python -m vkp80iii calibrate``.

        :param width_mm: physical paper width in mm (= firmware ``PRINT WIDTH``).
        :param margin_mm: safety/centering margin per side (default 1.5 mm =
            12 dots at 8 dots/mm).
        """
        if margin_mm < 0:
            raise CommandError(f"margin_mm must be >= 0, got {margin_mm}")
        print_width_mm = width_mm - 2 * margin_mm
        if print_width_mm <= 0:
            raise CommandError(f"margin_mm={margin_mm} leaves no print area on a {width_mm} mm roll")
        return cls(
            transport,
            codepage=codepage,
            paper_width_mm=print_width_mm,
            left_offset_dots=round(margin_mm * DOTS_PER_MM),
            auto_open=auto_open,
        )

    def set_print_area(self, dots: int | None = None) -> Printer:
        """``GS W`` -- set the printing area width (default: this paper's width)."""
        return self.send(c.set_print_area_width(self.width_dots if dots is None else dots))

    def apply_layout(self) -> Printer:
        """Send the left margin + print width for this paper (``GS L`` + ``GS W``).

        Call right after :meth:`reset` (``ESC @`` clears margins). This makes the
        paper's left edge the print origin and constrains the printable width,
        so text wrapping, centering and right-justify all use the real paper.
        """
        self.send(c.set_left_margin(self.left_offset_dots))
        return self.send(c.set_print_area_width(self.width_dots))

    def begin(self) -> Printer:
        """Convenience: :meth:`reset` then :meth:`apply_layout`."""
        return self.reset().apply_layout()

    # -- connection ------------------------------------------------------
    def open(self) -> Printer:
        if not self.transport.is_open:
            self.transport.open()
        return self

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> Printer:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- raw plumbing ----------------------------------------------------
    def send(self, data: bytes) -> Printer:
        """Send raw bytes straight to the printer."""
        self.transport.write(data)
        return self

    def _query(self, command: bytes, size: int, timeout: float) -> bytes:
        """Send a query command and read up to ``size`` reply bytes."""
        self.transport.flush_input()
        self.transport.write(command)
        return self.transport.read(size, timeout=timeout)

    # ===================================================================
    # text
    # ===================================================================
    def text(self, s: str, *, encoding: str | None = None) -> Printer:
        """Send a text string (encoded with the active code page codec)."""
        self.transport.write(s.encode(encoding or self._encoding, errors="replace"))
        return self

    def textln(self, s: str = "", *, encoding: str | None = None) -> Printer:
        """Send ``s`` followed by a line feed."""
        return self.text(s, encoding=encoding).send(c.lf())

    println = textln

    def newline(self, n: int = 1) -> Printer:
        """Emit ``n`` blank line feeds."""
        return self.send(c.lf() * n)

    # ===================================================================
    # formatting (chainable)
    # ===================================================================
    def reset(self) -> Printer:
        """``ESC @`` -- reset the printer to power-on defaults.

        This also reverts the device to its default code page (PC437), so the
        cached text codec is resynced to match.
        """
        self._codepage = int(CodePage.PC437)
        self._encoding = _CODEPAGE_CODEC[CodePage.PC437]
        return self.send(c.initialize())

    def bold(self, on: bool = True) -> Printer:
        return self.send(c.bold(on))

    def italic(self, on: bool = True) -> Printer:
        return self.send(c.italic(on))

    def underline(self, mode: Underline | int = Underline.SINGLE) -> Printer:
        return self.send(c.underline(mode))

    def double_strike(self, on: bool = True) -> Printer:
        return self.send(c.double_strike(on))

    def reverse(self, on: bool = True) -> Printer:
        """White-on-black reverse printing."""
        return self.send(c.reverse(on))

    def upside_down(self, on: bool = True) -> Printer:
        return self.send(c.upside_down(on))

    def rotate_90(self, on: bool = True) -> Printer:
        return self.send(c.rotate_90(on))

    def font(self, font: Font | int) -> Printer:
        return self.send(c.select_font(font))

    def char_size(self, width: int = 1, height: int = 1) -> Printer:
        """Character magnification (width/height each 1..8)."""
        return self.send(c.char_size(width, height))

    def print_modes(self, **kwargs: bool) -> Printer:
        """Set several modes at once: ``font_b, bold, double_height, double_width, italic, underline``."""
        return self.send(c.select_print_modes(**kwargs))

    def right_spacing(self, n: int) -> Printer:
        return self.send(c.set_right_spacing(n))

    # alignment / position
    def align(self, mode: Justify | int) -> Printer:
        return self.send(c.justify(mode))

    def align_left(self) -> Printer:
        return self.align(Justify.LEFT)

    def align_center(self) -> Printer:
        return self.align(Justify.CENTER)

    def align_right(self) -> Printer:
        return self.align(Justify.RIGHT)

    def set_tabs(self, *columns: int) -> Printer:
        return self.send(c.set_tab_stops(*columns))

    def tab(self) -> Printer:
        return self.send(c.horizontal_tab())

    def absolute_position(self, n: int) -> Printer:
        return self.send(c.set_absolute_position(n))

    def relative_position(self, n: int) -> Printer:
        return self.send(c.set_relative_position(n))

    def left_margin(self, n: int) -> Printer:
        return self.send(c.set_left_margin(n))

    def print_area_width(self, n: int) -> Printer:
        return self.send(c.set_print_area_width(n))

    # line spacing
    def line_spacing(self, n: int | None = None) -> Printer:
        """Set line spacing: ``None`` -> default 1/6", else ``n`` motion units."""
        return self.send(c.line_spacing_1_6() if n is None else c.set_line_spacing(n))

    def line_spacing_tight(self) -> Printer:
        """1/8-inch line spacing."""
        return self.send(c.line_spacing_1_8())

    # code page / charset
    def code_page(self, page: CodePage | int) -> Printer:
        """Select the active code page.

        For pages with a known Python codec (see ``_CODEPAGE_CODEC``) the text
        codec is updated to match. For any other page the codec is left
        unchanged -- set :attr:`encoding` yourself so :meth:`text` encodes
        correctly.
        """
        self._codepage = int(page)
        self._encoding = _CODEPAGE_CODEC.get(self._codepage, self._encoding)
        return self.send(c.select_code_page(page))

    def charset(self, country: CharsetCountry | int) -> Printer:
        return self.send(c.select_charset(country))

    @property
    def encoding(self) -> str:
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        self._encoding = value

    # ===================================================================
    # feed / cut / present
    # ===================================================================
    def feed(self, lines: int = 1) -> Printer:
        """Print buffer and feed ``lines`` lines."""
        return self.send(c.feed_lines(lines))

    def feed_units(self, n: int) -> Printer:
        """Print buffer and feed ``n`` vertical motion units."""
        return self.send(c.feed_units(n))

    def cut(self, feed: int | None = None) -> Printer:
        """Cut the paper (optionally feeding ``feed`` units first)."""
        return self.send(c.cut(feed=feed))

    def present(
        self,
        steps: int = 2,
        *,
        blink_led: bool = False,
        retract: bool = False,
        timeout_s: int = 0,
    ) -> Printer:
        """``FS P`` -- cut and present the ticket at the bezel.

        See :func:`vkp80iii.commands.present_ticket` for the parameter meanings.
        """
        return self.send(c.present_ticket(steps, blink_led=blink_led, retract=retract, timeout_s=timeout_s))

    def collect_mode(self, enabled: bool) -> Printer:
        """Enable/disable COLLECT mode (batch uncut tickets into the bin)."""
        return self.send(c.collect_mode(enabled))

    def eject_mode(self) -> Printer:
        """Enable EJECT (dispenser-continuous) mode; close it with :meth:`present`."""
        return self.send(c.eject_mode())

    def presentation_offset(self, mm: int) -> Printer:
        return self.send(c.set_presentation_offset(mm))

    # ===================================================================
    # black-mark alignment / mechanism
    # ===================================================================
    def align_to_printhead(self) -> Printer:
        return self.send(c.align_to_printhead())

    def align_to_cutter(self) -> Printer:
        return self.send(c.align_to_cutter())

    def black_mark_distance(self, tenths_mm: int) -> Printer:
        """Persisted in NVRAM -- set once during setup, not per ticket."""
        return self.send(c.set_black_mark_distance(tenths_mm))

    def paper_recovery(self, mm: int = 11) -> Printer:
        return self.send(c.paper_recovery(mm))

    def virtual_paper_end(self, cm: int) -> Printer:
        return self.send(c.set_virtual_paper_end(cm))

    def min_ticket_length(self, mm: int) -> Printer:
        return self.send(c.set_min_ticket_length(mm))

    # ===================================================================
    # barcodes
    # ===================================================================
    def barcode(
        self,
        symbology: Barcode | int,
        data: bytes | str,
        *,
        height: int | None = None,
        width: int | None = None,
        hri: HRIPosition | int | None = None,
        hri_font: HRIFont | int | None = None,
    ) -> Printer:
        """Print a 1D barcode, optionally configuring height/width/HRI first."""
        if height is not None:
            self.send(c.set_barcode_height(height))
        if width is not None:
            self.send(c.set_barcode_width(width))
        if hri is not None:
            self.send(c.set_hri_position(hri))
        if hri_font is not None:
            self.send(c.set_hri_font(hri_font))
        return self.send(c.barcode(symbology, data))

    def qrcode(
        self,
        data: bytes | str,
        *,
        module_size: int = 6,
        ecc: QRErrorCorrection | int = QRErrorCorrection.M,
        model: QRModel | int = QRModel.MODEL2,
        version: int = 0,
    ) -> Printer:
        """Configure and print a QR code in one call."""
        payload = _payload(data)
        self.send(c.qr_model(model))
        self.send(c.qr_module_size(module_size))
        self.send(c.qr_error_correction(ecc))
        if version:
            self.send(c.qr_version(version))
        self.send(c.qr_store(payload))
        return self.send(c.qr_print())

    def pdf417(
        self,
        data: bytes | str,
        *,
        columns: int = 0,
        rows: int = 0,
        module_width: int = 3,
        module_height: int = 3,
    ) -> Printer:
        """Configure and print a PDF417 symbol."""
        payload = _payload(data)
        self.send(c.pdf417_columns(columns))
        self.send(c.pdf417_rows(rows))
        self.send(c.pdf417_module_width(module_width))
        self.send(c.pdf417_module_height(module_height))
        self.send(c.pdf417_store(payload))
        return self.send(c.pdf417_print())

    def aztec(
        self,
        data: bytes | str,
        *,
        module_size: int = 6,
        type: AztecType | int = AztecType.FULL,
    ) -> Printer:
        """Configure and print an AZTEC symbol."""
        payload = _payload(data)
        self.send(c.aztec_type(type))
        self.send(c.aztec_module_size(module_size))
        self.send(c.aztec_store(payload))
        return self.send(c.aztec_print())

    def datamatrix(
        self,
        data: bytes | str,
        *,
        module_size: int = 6,
        encoding: DataMatrixEncoding | int = DataMatrixEncoding.AUTO,
    ) -> Printer:
        """Configure and print a DataMatrix symbol."""
        payload = _payload(data)
        self.send(c.datamatrix_encoding(encoding))
        self.send(c.datamatrix_module_size(module_size))
        self.send(c.datamatrix_store(payload))
        return self.send(c.datamatrix_print())

    # ===================================================================
    # images / logos
    # ===================================================================
    def image(
        self,
        image: Image.Image | str,
        *,
        max_width: int | None = None,
        threshold: int | None = None,
        dither: bool = True,
        invert: bool = False,
        mode: int = 0,
    ) -> Printer:
        """Print a raster image (path or PIL image). Requires Pillow.

        The image is downscaled to fit the paper width if wider. Tall images are
        split into bands automatically, since a single ``GS v 0`` is capped at
        2047 rows. The left offset is applied in whole bytes -- if the configured
        ``left_offset_dots`` is not a multiple of 8, the sub-byte remainder is
        not shifted.
        """
        from .imaging import image_to_raster

        width_bytes, height, data = image_to_raster(
            image,
            max_width=max_width or self.width_dots,
            threshold=threshold,
            dither=dither,
            invert=invert,
        )
        # Raster (GS v 0) starts at the logical origin, ignoring the GS L left
        # margin, so blank-pad each row by the left offset (whole bytes) to land
        # the image on the paper.
        pad = self.left_offset_dots // 8
        data, width_bytes = _pad_rows(data, width_bytes, height, left=pad)
        band = 1024  # rows per GS v 0 chunk (well under the 2047-row limit)
        for top in range(0, height, band):
            rows = min(band, height - top)
            chunk = data[top * width_bytes : (top + rows) * width_bytes]
            self.send(c.raster_image(width_bytes, rows, chunk, mode=mode))
        return self

    def print_logo(
        self,
        number: int,
        *,
        justify: Justify | int = Justify.LEFT,
        rotate: bool = False,
        border_dots: int = 0,
        position_dots: int | None = None,
    ) -> Printer:
        """Print a logo stored in the printer's flash by its id."""
        return self.send(
            c.print_logo(
                number,
                justify=justify,
                rotate=rotate,
                border_dots=border_dots,
                position_dots=position_dots,
            )
        )

    def upload_logo(
        self,
        number: int,
        image: Image.Image | str,
        *,
        name: str = "LOGO.BMP",
        max_width: int | None = None,
        threshold: int | None = 128,
        dither: bool = False,
        timeout: float = 8.0,
    ) -> bool:
        """Store an image into flash as logo ``number`` (``FS 0x94``).

        Returns True on success (the printer replies ``<PC1\\xAA>``), else raises
        :class:`~vkp80iii.exceptions.PrinterError`.

        IMPORTANT: the printer only re-reads its logo index on boot, so you must
        **power-cycle the printer once after uploading** before :meth:`print_logo`
        can find the new logo (otherwise it prints "FILE ERROR"). Flash has
        limited write cycles -- upload during setup, not per print. Numbers 1/2
        hold the factory demo logo; use your own (e.g. 200).
        """
        from .imaging import image_to_raster

        width_bytes, height, data = image_to_raster(
            image, max_width=max_width or self.width_dots, threshold=threshold, dither=dither
        )
        # the flash format needs the width to be a multiple of 16 px (even bytes)
        if width_bytes % 2:
            data, width_bytes = _pad_rows(data, width_bytes, height, right=1)

        reply = self._query(c.store_logo_flash(number, width_bytes * 8, height, data, name=name), 6, timeout)
        if reply[:4] == b"<PC1" and len(reply) >= 5 and reply[4] == 0xAA:
            return True
        raise PrinterError(f"logo upload failed, reply = {reply.hex(' ') or '(none)'}")

    # ===================================================================
    # LED bezel bar
    # ===================================================================
    def led(self, rgb: tuple[int, int, int], *, persist: bool = False) -> Printer:
        """Set the bezel LED bar colour (``FS L`` immediate).

        Note: on some firmware the RGB colour is only visible while a ticket is
        being presented/ejected; standalone the bar may show a default amber.
        Use :meth:`led_off` (``FS B``) to turn it off / stop a flash.
        """
        return self.send(c.led_color(rgb, target="immediate", persist=persist))

    def led_off(self) -> Printer:
        """Turn the LED bar off (stops any steady/flash/rainbow mode)."""
        return self.send(c.led_off())

    def led_flash(self, freq: LedFlashFreq | int = LedFlashFreq.HZ_2) -> Printer:
        return self.send(c.led_bar(LedMode.FLASH, freq))

    def led_rainbow(self, enabled: bool = True, *, persist: bool = False) -> Printer:
        return self.send(c.led_rainbow(enabled, persist=persist))

    # ===================================================================
    # counters
    # ===================================================================
    def setup_counter(
        self,
        start: int,
        end: int,
        *,
        step: int = 1,
        repeat: int = 1,
        digits: int = 0,
        align: str = "right",
        pad_zero: bool = False,
    ) -> Printer:
        """Configure the on-printer serial-number counter."""
        self.send(c.counter_print_mode(digits=digits, align=align, pad_zero=pad_zero))
        self.send(c.counter_mode(start, end, step=step, repeat=repeat))
        return self.send(c.set_counter(start))

    def print_counter(self) -> Printer:
        """Queue the current counter value for printing, then advance it."""
        return self.send(c.print_counter())

    # ===================================================================
    # misc
    # ===================================================================
    def print_quality(self, quality: PrintQuality | int) -> Printer:
        return self.send(c.set_print_quality(quality))

    def motion_units(self, x: int = 0, y: int = 0) -> Printer:
        return self.send(c.set_motion_units(x, y))

    def enable_keys(self, enabled: bool = True) -> Printer:
        return self.send(c.enable_keys(enabled))

    def density(self, level: int = 0) -> Printer:
        """``GS |`` -- relative print darkness, ``level`` -2..+2 (12.5% steps; 0 = default)."""
        if not (-2 <= level <= 2):
            raise CommandError("density level must be -2..+2")
        return self.send(c.set_density(0x04 + level))

    def read_logs(self, timeout: float = 3.0) -> bytes:
        """``FS G 0`` -- retrieve the flash-disk text log files (for remote diagnostics).

        The printer first sends a 4-byte size, then that many log bytes.
        """
        size = self._query(c.data_logger(0), 4, timeout)
        if len(size) < 4:
            return b""
        n = int.from_bytes(size, "little")
        return self.transport.read(n, timeout=timeout) if n else b""

    def clear_logs(self, timeout: float = 3.0) -> bool:
        """``FS G 1`` -- delete the flash-disk log files. Returns True on ACK (0x06)."""
        return self._query(c.data_logger(1), 1, timeout) == b"\x06"

    # ===================================================================
    # status / queries (need a readable transport)
    # ===================================================================
    def status(self, timeout: float = 1.0) -> FullStatus:
        """Request and decode the full 6-byte status block."""
        reply = self._query(c.request_full_status(), size=6, timeout=timeout)
        if not reply:
            raise StatusTimeout("no full-status reply from printer")
        return FullStatus.parse(reply)

    def paper_status(self, timeout: float = 1.0) -> PaperStatus:
        """Query the paper sensor (``ESC v``)."""
        reply = self._query(c.transmit_paper_sensor(), size=1, timeout=timeout)
        if not reply:
            raise StatusTimeout("no paper-sensor reply from printer")
        return PaperStatus.from_paper_sensor(reply[0])

    def is_ready(self, timeout: float = 1.0) -> bool:
        """True if the printer reports it can print right now.

        Returns False on no reply (`StatusTimeout`) or an unparseable/short
        reply (`PrinterError`) rather than propagating.
        """
        try:
            return self.status(timeout=timeout).ready
        except (StatusTimeout, PrinterError):
            return False

    def offline_status(self, timeout: float = 1.0) -> dict[str, bool]:
        reply = self._query(c.request_status(StatusType.OFFLINE), size=1, timeout=timeout)
        if not reply:
            raise StatusTimeout("no off-line status reply")
        return decode_offline_status(reply[0])

    def error_status(self, timeout: float = 1.0) -> dict[str, bool]:
        reply = self._query(c.request_status(StatusType.ERROR), size=1, timeout=timeout)
        if not reply:
            raise StatusTimeout("no error status reply")
        return decode_error_status(reply[0])

    def device_id(self, timeout: float = 1.0) -> bytes:
        """Return the 2-byte device model id (expected ``b'\\x02\\x05'``)."""
        return self._query(c.transmit_device_id(0xFF), size=2, timeout=timeout)

    def rom_version(self, timeout: float = 1.0) -> str:
        reply = self._query(c.transmit_device_id(0x03), size=4, timeout=timeout)
        return reply.decode("ascii", "ignore")

    def enable_auto_status_back(
        self,
        *,
        paper: bool = True,
        user: bool = True,
        recoverable: bool = True,
        unrecoverable: bool = True,
    ) -> Printer:
        """Make the printer push status automatically whenever it changes."""
        return self.send(
            c.auto_status_back(paper=paper, user=user, recoverable=recoverable, unrecoverable=unrecoverable)
        )

    def read_auto_status(self, timeout: float = 1.0) -> FullStatus | None:
        """Read one unsolicited automatic status-back frame, if pending.

        The frame is ``0x10 <mask> <enabled status bytes>``: the mask's low four
        bits (paper / user / recoverable / unrecoverable) say which category
        bytes follow, in that order. Categories not enabled are reported as 0.
        Returns None if no (valid) frame is pending.
        """
        head = self.transport.read(1, timeout=timeout)
        if not head or head[0] != 0x10:
            return None
        mask = self.transport.read(1, timeout=timeout)
        if not mask:
            return None
        cats = [bool(mask[0] & (1 << i)) for i in range(4)]  # paper, user, rec, unrec
        body = self.transport.read(sum(cats), timeout=timeout)
        full = bytearray(4)
        j = 0
        for i, enabled in enumerate(cats):
            if enabled and j < len(body):
                full[i] = body[j]
                j += 1
        return FullStatus.parse(bytes(full))

    # -- maintenance counters (ASCII readings) ---------------------------
    def paper_remaining_cm(self, timeout: float = 1.0) -> int:
        return parse_reading(self._query(c.read_paper_remaining(), size=16, timeout=timeout))

    def cut_count(self, timeout: float = 1.0) -> int:
        return parse_reading(self._query(c.read_cut_count(), size=16, timeout=timeout))

    def printed_length_cm(self, timeout: float = 1.0) -> int:
        return parse_reading(self._query(c.read_printed_length(), size=16, timeout=timeout))

    def retract_count(self, timeout: float = 1.0) -> int:
        return parse_reading(self._query(c.read_retract_count(), size=16, timeout=timeout))

    def powerup_count(self, timeout: float = 1.0) -> int:
        return parse_reading(self._query(c.read_powerup_count(), size=16, timeout=timeout))
