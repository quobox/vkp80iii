"""vkp80iii -- a pure-Python driver for the Custom VKP80III.

The VKP80III is a thermal ticket/receipt printer that speaks an ESC/POS-derived
command set (its "VKP80III emulation") with Custom-specific extensions for the
presenter/ejector, black-mark alignment, the bezel RGB LED bar, stored logos
and serial-number counters.

Quick start::

    from vkp80iii import Printer

    with Printer() as p:                # talks to /dev/usb/lp0
        p.textln("Hello, ticket!")
        p.qrcode("https://example.com")
        p.feed(2).cut()

For full control, the :mod:`vkp80iii.commands` module exposes one pure
byte-builder per printer command, and :mod:`vkp80iii.transport` provides the
USB / serial / dummy backends.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from . import commands
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
    PDF417ErrorMode,
    PrintQuality,
    QRErrorCorrection,
    QRModel,
    StatusType,
    Underline,
)
from .exceptions import (
    CommandError,
    PrinterError,
    StatusTimeout,
    TransportError,
    TransportNotConnected,
    VKPError,
)
from .printer import Printer
from .status import FullStatus, PaperStatus
from .transport import (
    DEFAULT_USBLP_PATH,
    USB_PRODUCT_ID,
    USB_VENDOR_ID,
    DummyTransport,
    PyUsbTransport,
    SerialTransport,
    Transport,
    UsbLpTransport,
)

try:
    __version__ = version("vkp80iii")
except PackageNotFoundError:  # not installed (e.g. running from a source tree)
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    # main API
    "Printer",
    "commands",
    # transports
    "Transport",
    "UsbLpTransport",
    "PyUsbTransport",
    "SerialTransport",
    "DummyTransport",
    "USB_VENDOR_ID",
    "USB_PRODUCT_ID",
    "DEFAULT_USBLP_PATH",
    # status
    "FullStatus",
    "PaperStatus",
    # enums / constants
    "Justify",
    "Font",
    "Underline",
    "PrintQuality",
    "Barcode",
    "HRIPosition",
    "HRIFont",
    "QRModel",
    "QRErrorCorrection",
    "PDF417ErrorMode",
    "AztecType",
    "DataMatrixEncoding",
    "CharsetCountry",
    "CodePage",
    "StatusType",
    "LedMode",
    "LedFlashFreq",
    "DOTS_PER_MM",
    "MAX_DOTS",
    # exceptions
    "VKPError",
    "TransportError",
    "TransportNotConnected",
    "StatusTimeout",
    "PrinterError",
    "CommandError",
]
