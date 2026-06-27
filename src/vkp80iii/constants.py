"""Enumerations and named constants for the VKP80III command set.

Values are the raw bytes the printer expects, so an :class:`enum.IntEnum`
member can be passed straight through to the command builders.
"""

from __future__ import annotations

from enum import IntEnum

# --- ASCII control codes used throughout the protocol --------------------
NUL = 0x00
HT = 0x09
LF = 0x0A
FF = 0x0C
CR = 0x0D
DLE = 0x10
EOT = 0x04
ESC = 0x1B
FS = 0x1C
GS = 0x1D

#: Printer resolution: 8 dots/mm = 203 dpi, head width 576 dots (72 mm).
DOTS_PER_MM = 8
MAX_DOTS = 576


class Justify(IntEnum):
    """Horizontal justification (ESC a)."""

    LEFT = 0
    CENTER = 1
    RIGHT = 2


class Font(IntEnum):
    """Character font (ESC M / FS %)."""

    A = 0  # 12x24, ~42 columns on 72 mm
    B = 1  # 9x17, ~56 columns


class Underline(IntEnum):
    """Underline thickness (ESC -)."""

    NONE = 0
    SINGLE = 1
    DOUBLE = 2


class PrintQuality(IntEnum):
    """Print quality / speed (GS F0, command 0x1D 0xF0)."""

    HIGH_QUALITY = 0
    NORMAL = 1
    HIGH_SPEED = 2


# --- 1D barcodes (GS k) --------------------------------------------------
class Barcode(IntEnum):
    """1D barcode symbologies for :func:`~vkp80iii.commands.barcode`.

    These are the "format 2" selectors (length-prefixed form, ``GS k m n
    d1..dn``), which the library uses because it can carry the full byte
    range and an explicit length.
    """

    UPC_A = 0x41
    UPC_E = 0x42
    EAN13 = 0x43
    EAN8 = 0x44
    CODE39 = 0x45
    ITF = 0x46
    CODABAR = 0x47
    CODE93 = 0x48
    CODE128 = 0x49
    CODE32 = 0x5A


class HRIPosition(IntEnum):
    """Human-readable interpretation text position (GS H)."""

    NONE = 0
    ABOVE = 1
    BELOW = 2
    BOTH = 3


class HRIFont(IntEnum):
    """Font for HRI characters (GS f)."""

    A = 0
    B = 1


# --- 2D barcodes (GS ( k) ------------------------------------------------
class QRModel(IntEnum):
    """QR Code model (GS ( k fn=165)."""

    MODEL2 = 0x32
    MICRO = 0x33


class QRErrorCorrection(IntEnum):
    """QR error-correction level (GS ( k fn=169)."""

    AUTO = 0x30
    L = 0x31  # ~7%
    M = 0x32  # ~15%
    Q = 0x33  # ~25%
    H = 0x34  # ~30%


class PDF417ErrorMode(IntEnum):
    """PDF417 ECC selection mode (GS ( k fn=069)."""

    LEVEL = 0x30  # fixed level 0..8
    RATIO = 0x31  # n x 10% of data


class AztecType(IntEnum):
    """AZTEC symbol type (GS ( k fn=P65)."""

    FULL = 0x00
    RUNE = 0x01


class DataMatrixEncoding(IntEnum):
    """DataMatrix encoding scheme (GS ( k fn=Q65)."""

    ASCII = 0x00
    C40 = 0x01
    TEXT = 0x02
    X12 = 0x03
    EDIFACT = 0x04
    BASE256 = 0x05
    AUTO = 0x06


# --- International character sets (ESC R) ---------------------------------
class CharsetCountry(IntEnum):
    """International character set (ESC R). Common subset."""

    USA = 0
    FRANCE = 1
    GERMANY = 2
    UK = 3
    DENMARK_I = 4
    SWEDEN = 5
    ITALY = 6
    SPAIN_I = 7
    JAPAN = 8
    NORWAY = 9
    DENMARK_II = 10


class CodePage(IntEnum):
    """Character code table (ESC t). Common subset of the supported pages.

    The full set depends on the code pages installed on the device; selecting
    a missing page leaves the current one in use.
    """

    PC437 = 0  # USA / Standard Europe
    KATAKANA = 1
    PC850 = 2  # Multilingual
    PC860 = 3  # Portuguese
    PC863 = 4  # Canadian-French
    PC865 = 5  # Nordic
    WPC1252 = 16  # Windows Latin-1
    PC866 = 17  # Cyrillic
    PC852 = 18  # Latin-2
    PC858 = 19  # Euro


# --- Real-time status (DLE EOT n) ----------------------------------------
class StatusType(IntEnum):
    """Argument ``n`` for the real-time status request (DLE EOT n)."""

    PRINTER = 1
    OFFLINE = 2
    ERROR = 3
    PAPER = 4
    PRESENTER = 5  # ticket in output / presenter sensors


# --- Bezel LED bar (FS B / FS L) -----------------------------------------
class LedMode(IntEnum):
    """Bezel RGB LED bar mode (FS B, 0x1C 0x42)."""

    OFF = 0x43  # 'C'
    FLASH = 0x46  # 'F' (needs a frequency byte)
    RESET = 0x52  # 'R'
    ON = 0x53  # 'S' steady


class LedFlashFreq(IntEnum):
    """Flash frequency for :data:`LedMode.FLASH`."""

    HZ_0_25 = 0x01
    HZ_0_5 = 0x02
    HZ_1 = 0x03
    HZ_2 = 0x04
    HZ_3 = 0x05
    HZ_4 = 0x06
    HZ_5 = 0x07
    HZ_6 = 0x08
    HZ_8 = 0x09
    HZ_12 = 0x0A
