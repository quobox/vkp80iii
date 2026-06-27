"""Tests for status-byte decoding."""

from __future__ import annotations

import pytest

from vkp80iii import FullStatus, PaperStatus
from vkp80iii.exceptions import PrinterError
from vkp80iii.status import decode_error_status, decode_offline_status, parse_reading


# =====================================================================
# FullStatus
# =====================================================================
def test_full_status_ready():
    st = FullStatus.parse(b"\x10\x0f\x00\x00\x00\x00")
    assert st.ready is True
    assert st.paper_present is True
    assert st.has_error is False
    assert st.cover_open is False
    assert st.problems() == []
    assert "ready" in str(st)


def test_full_status_paper_byte_bits():
    assert FullStatus.parse(b"\x10\x0f\x01\x00\x00\x00").paper_present is False
    assert FullStatus.parse(b"\x10\x0f\x04\x00\x00\x00").low_paper is True
    assert FullStatus.parse(b"\x10\x0f\x20\x00\x00\x00").ticket_in_output is True
    assert FullStatus.parse(b"\x10\x0f\x40\x00\x00\x00").virtual_paper_end is True
    # bit7 set => black mark NOT over sensor
    assert FullStatus.parse(b"\x10\x0f\x80\x00\x00\x00").black_mark_over_sensor is False


def test_full_status_user_byte_bits():
    st = lambda b: FullStatus.parse(bytes((0x10, 0x0F, 0x00, b, 0x00, 0x00)))  # noqa: E731
    assert st(0x01).head_up is True
    assert st(0x02).cover_open is True
    assert st(0x04).spooling is True
    assert st(0x08).drag_motor_on is True
    assert st(0x20).lf_key_pressed is True
    assert st(0x40).ff_key_pressed is True


def test_full_status_recoverable_byte_bits():
    st = lambda b: FullStatus.parse(bytes((0x10, 0x0F, 0x00, 0x00, b, 0x00)))  # noqa: E731
    assert st(0x01).head_temperature_error is True
    assert st(0x02).comm_error is True
    assert st(0x08).power_supply_error is True
    assert st(0x20).command_not_acknowledged is True
    assert st(0x40).paper_jam is True
    assert st(0x80).black_mark_error is True


def test_full_status_unrecoverable_byte_bits():
    st = lambda b: FullStatus.parse(bytes((0x10, 0x0F, 0x00, 0x00, 0x00, b)))  # noqa: E731
    assert st(0x01).cutter_error is True
    assert st(0x02).cutter_cover_open is True
    assert st(0x04).ram_error is True
    assert st(0x08).eeprom_error is True
    assert st(0x80).emitter_error is True


def test_full_status_has_error_and_problems():
    st = FullStatus.parse(b"\x10\x0f\x01\x02\x00\x01")  # no paper + cover open + cutter error
    assert st.paper_present is False
    assert st.cover_open is True
    assert st.cutter_error is True
    assert st.has_error is True
    assert st.ready is False
    probs = st.problems()
    assert "paper not present" in probs
    assert "cover open" in probs
    assert "autocutter error" in probs


def test_full_status_bare_4_bytes():
    # automatic status-back may omit the 10 0F header
    st = FullStatus.parse(b"\x01\x00\x00\x00")
    assert st.paper_present is False


def test_full_status_too_short():
    with pytest.raises(PrinterError):
        FullStatus.parse(b"\x10\x0f")


# =====================================================================
# PaperStatus
# =====================================================================
def test_paper_sensor():
    assert PaperStatus.from_paper_sensor(0x00) == PaperStatus(paper_present=True, low_paper=False)
    assert PaperStatus.from_paper_sensor(0x03).low_paper is True
    assert PaperStatus.from_paper_sensor(0x0C).paper_present is False
    ps = PaperStatus.from_paper_sensor(0x0F)
    assert ps.low_paper is True and ps.paper_present is False


def test_roll_sensor():
    assert PaperStatus.from_roll_sensor(0x00).paper_present is True
    assert PaperStatus.from_roll_sensor(0x0C).low_paper is True
    assert PaperStatus.from_roll_sensor(0x60).paper_present is False


# =====================================================================
# DLE EOT 2 / 3 decoders
# =====================================================================
def test_offline_status_decode():
    assert decode_offline_status(0x04)["cover_open"] is True
    assert decode_offline_status(0x08)["paper_fed_by_key"] is True
    assert decode_offline_status(0x20)["paper_end_stop"] is True
    assert decode_offline_status(0x40)["error"] is True
    assert decode_offline_status(0x12)["error"] is False  # baseline bits only


def test_error_status_decode():
    assert decode_error_status(0x08)["cutter_error"] is True
    assert decode_error_status(0x20)["unrecoverable_error"] is True
    assert decode_error_status(0x40)["auto_recoverable_error"] is True


# =====================================================================
# numeric readings
# =====================================================================
@pytest.mark.parametrize(
    "reply,expected",
    [
        (b"785cuts", 785),
        (b"510cm", 510),
        (b"38890cm", 38890),
        (b"512ret", 512),
        (b"512on", 512),
        (b"0cm", 0),
    ],
)
def test_parse_reading(reply, expected):
    assert parse_reading(reply) == expected


def test_parse_reading_invalid():
    with pytest.raises(PrinterError):
        parse_reading(b"")
    with pytest.raises(PrinterError):
        parse_reading(b"cm")
