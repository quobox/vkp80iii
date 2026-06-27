"""Integration tests against a real VKP80III (opt-in, marked ``hardware``).

The status/query tests are non-destructive (no paper) and assert that the real
read path + decoding round-trips. The print tests consume paper and need
``VKP80III_PRINT=1``; their output must be eyeballed -- they only assert that the
command path completes without error.
"""

from __future__ import annotations

import pytest

from vkp80iii import FullStatus, Justify, PaperStatus

pytestmark = pytest.mark.hardware


# --- non-destructive status / query reads (no paper consumed) -------------
def test_device_id(printer):
    dev_id = printer.device_id()
    assert len(dev_id) == 2  # VKP80III model id (expected b"\x02\x05")


def test_rom_version(printer):
    version = printer.rom_version()
    assert isinstance(version, str) and version.strip()


def test_full_status_round_trips(printer):
    st = printer.status()
    assert isinstance(st, FullStatus)
    assert isinstance(st.ready, bool)
    assert isinstance(st.paper_present, bool)


def test_paper_status_round_trips(printer):
    ps = printer.paper_status()
    assert isinstance(ps, PaperStatus)
    assert isinstance(ps.paper_present, bool)


def test_is_ready_returns_bool(printer):
    assert isinstance(printer.is_ready(), bool)


def test_maintenance_counters(printer):
    assert printer.cut_count() >= 0
    assert printer.powerup_count() >= 0
    assert printer.printed_length_cm() >= 0
    assert printer.paper_remaining_cm() >= 0


# --- paper-consuming smoke tests (need VKP80III_PRINT=1; eyeball output) ---
# Eject with .present() (FS P: cut + present at the bezel), NOT .cut() (GS V):
# on this presenter unit GS V does not actuate the cutter, so a .cut() smoke test
# would pass without ever cutting or ejecting (false green). FS P both cuts and
# pushes the ticket out the front bezel.
def test_print_and_present(printer, print_enabled):
    (
        printer.begin()
        .align(Justify.CENTER)
        .bold()
        .textln("VKP80III INTEGRATION TEST")
        .bold(False)
        .align(Justify.LEFT)
        .textln("If you can read this, the print path works.")
        .feed(2)
        .present()
    )


def test_qrcode_prints(printer, print_enabled):
    printer.begin().align(Justify.CENTER).qrcode("https://github.com/quobox/vkp80iii").feed(3).present()
