"""Decoding of the status bytes the VKP80III sends back.

The printer answers real-time status requests (``DLE EOT n``), the paper-sensor
query (``ESC v``) and the full-status request (``DLE EOT 0x14``) with packed
status bytes. These helpers turn those bytes into readable dataclasses.

Bit meanings follow the VKP80III emulation "STATUS COMMANDS" chapter of the
commands manual.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import PrinterError


def _bit(value: int, mask: int) -> bool:
    return bool(value & mask)


@dataclass(frozen=True)
class PaperStatus:
    """Decoded paper situation from the paper sensor (``ESC v`` / roll sensor).

    These commands only report paper presence and low-paper; the richer paper
    flags (ticket in output, virtual paper end, black mark) are part of the full
    status -- see :class:`FullStatus`.
    """

    paper_present: bool
    low_paper: bool  # near-paper-end sensor triggered

    @classmethod
    def from_paper_sensor(cls, byte: int) -> PaperStatus:
        """Decode the single byte returned by ``ESC v``.

        bits 0-1 (0x03) -> near-paper-end (low paper); bits 2-3 (0x0C) ->
        paper-end (no paper).
        """
        low = _bit(byte, 0x03)
        end = _bit(byte, 0x0C)
        return cls(paper_present=not end, low_paper=low)

    @classmethod
    def from_roll_sensor(cls, byte: int) -> PaperStatus:
        """Decode ``DLE EOT 4`` (paper roll sensor): 0x0C low, 0x60 absent."""
        return cls(paper_present=not _bit(byte, 0x60), low_paper=_bit(byte, 0x0C))


@dataclass(frozen=True)
class FullStatus:
    """The 6-byte full-status block (``DLE EOT 0x14`` / automatic status-back).

    Byte layout: ``10 0F <paper> <user> <recoverable> <unrecoverable>``.
    """

    # paper byte (byte 3)
    paper_present: bool
    low_paper: bool
    ticket_in_output: bool
    virtual_paper_end: bool
    black_mark_over_sensor: bool
    # user byte (byte 4)
    head_up: bool
    cover_open: bool
    spooling: bool
    drag_motor_on: bool
    lf_key_pressed: bool
    ff_key_pressed: bool
    # recoverable errors (byte 5)
    head_temperature_error: bool
    comm_error: bool
    power_supply_error: bool
    command_not_acknowledged: bool
    paper_jam: bool
    black_mark_error: bool
    # unrecoverable errors (byte 6)
    cutter_error: bool
    cutter_cover_open: bool
    ram_error: bool
    eeprom_error: bool
    emitter_error: bool

    @classmethod
    def parse(cls, data: bytes) -> FullStatus:
        """Parse the 6 bytes returned for a full-status request.

        Tolerates a leading ``10 0F`` header or a bare 4-byte status block.
        """
        b = bytes(data)
        if len(b) >= 6 and b[0] == 0x10 and b[1] == 0x0F:
            paper, user, rec, unrec = b[2], b[3], b[4], b[5]
        elif len(b) >= 4:
            # Some firmwares omit the header (e.g. automatic status-back).
            paper, user, rec, unrec = b[0], b[1], b[2], b[3]
        else:
            raise PrinterError(f"full status needs >=4 bytes, got {len(b)}: {b.hex()}")
        return cls(
            paper_present=not _bit(paper, 0x01),
            low_paper=_bit(paper, 0x04),
            ticket_in_output=_bit(paper, 0x20),
            virtual_paper_end=_bit(paper, 0x40),
            black_mark_over_sensor=not _bit(paper, 0x80),
            head_up=_bit(user, 0x01),
            cover_open=_bit(user, 0x02),
            spooling=_bit(user, 0x04),
            drag_motor_on=_bit(user, 0x08),
            lf_key_pressed=_bit(user, 0x20),
            ff_key_pressed=_bit(user, 0x40),
            head_temperature_error=_bit(rec, 0x01),
            comm_error=_bit(rec, 0x02),
            power_supply_error=_bit(rec, 0x08),
            command_not_acknowledged=_bit(rec, 0x20),
            paper_jam=_bit(rec, 0x40),
            black_mark_error=_bit(rec, 0x80),
            cutter_error=_bit(unrec, 0x01),
            cutter_cover_open=_bit(unrec, 0x02),
            ram_error=_bit(unrec, 0x04),
            eeprom_error=_bit(unrec, 0x08),
            emitter_error=_bit(unrec, 0x80),
        )

    @property
    def has_error(self) -> bool:
        """True if any error flag (recoverable or unrecoverable) is set."""
        return any(
            (
                self.head_up,
                self.head_temperature_error,
                self.comm_error,
                self.power_supply_error,
                self.command_not_acknowledged,
                self.paper_jam,
                self.black_mark_error,
                self.cutter_error,
                self.cutter_cover_open,
                self.ram_error,
                self.eeprom_error,
                self.emitter_error,
            )
        )

    @property
    def ready(self) -> bool:
        """True if the printer can print right now (paper present, closed, no errors)."""
        return self.paper_present and not self.cover_open and not self.has_error

    def problems(self) -> list[str]:
        """Human-readable list of the active fault/attention flags."""
        labels = {
            "cover_open": "cover open",
            "head_up": "print head up",
            "low_paper": "paper low",
            "virtual_paper_end": "virtual paper end reached",
            "paper_jam": "paper jam",
            "head_temperature_error": "print head over temperature",
            "comm_error": "RS232 communication error",
            "power_supply_error": "power supply voltage error",
            "command_not_acknowledged": "command not acknowledged",
            "black_mark_error": "black-mark search error",
            "cutter_error": "autocutter error",
            "cutter_cover_open": "autocutter cover open",
            "ram_error": "RAM error",
            "eeprom_error": "EEPROM error",
            "emitter_error": "emitter (presenter) error",
        }
        out = [] if self.paper_present else ["paper not present"]
        out += [text for attr, text in labels.items() if getattr(self, attr)]
        return out

    def __str__(self) -> str:
        if self.ready:
            return "VKP80III: ready"
        probs = ", ".join(self.problems()) or "not ready"
        return f"VKP80III: {probs}"


def decode_offline_status(byte: int) -> dict[str, bool]:
    """Decode ``DLE EOT 2`` (off-line status) into named flags."""
    return {
        "cover_open": _bit(byte, 0x04),
        "paper_fed_by_key": _bit(byte, 0x08),
        "paper_end_stop": _bit(byte, 0x20),
        "error": _bit(byte, 0x40),
    }


def decode_error_status(byte: int) -> dict[str, bool]:
    """Decode ``DLE EOT 3`` (error status) into named flags."""
    return {
        "cutter_error": _bit(byte, 0x08),
        "unrecoverable_error": _bit(byte, 0x20),
        "auto_recoverable_error": _bit(byte, 0x40),
    }


def parse_reading(reply: bytes) -> int:
    """Parse a numeric reading reply such as ``b'510cm'`` or ``b'785cuts'``.

    Returns the leading integer (cm, count, ...). The caller knows the unit.
    """
    s = bytes(reply).decode("ascii", "ignore").strip()
    digits = ""
    for ch in s:
        if ch.isdigit():
            digits += ch
        else:
            break
    if not digits:
        raise PrinterError(f"could not parse numeric reading from {reply!r}")
    return int(digits)
