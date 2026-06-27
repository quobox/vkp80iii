"""Fixtures for the opt-in hardware integration tests.

These talk to a *real* VKP80III. They are deselected by default (see the
``-m 'not hardware'`` default in pyproject) and skip cleanly when no printer is
reachable, so they never break CI or a normal ``pytest`` run.

Run against a connected printer::

    uv run pytest -m hardware                 # status / query reads only (no paper)
    VKP80III_PRINT=1 uv run pytest -m hardware # also the paper-consuming smoke tests

Environment:
    VKP80III_DEVICE   device node (default /dev/usb/lp0)
    VKP80III_PAPER_MM usable paper width in mm (default 80)
    VKP80III_OFFSET   left offset in dots (default 0)
    VKP80III_PRINT    set to 1 to allow tests that actually print/cut paper
"""

from __future__ import annotations

import os

import pytest

from vkp80iii import Printer, UsbLpTransport
from vkp80iii.exceptions import TransportError


@pytest.fixture
def printer():
    """An open Printer on the real device, or skip if none is reachable."""
    device = os.environ.get("VKP80III_DEVICE", "/dev/usb/lp0")
    paper_mm = float(os.environ.get("VKP80III_PAPER_MM", "80"))
    offset = int(os.environ.get("VKP80III_OFFSET", "0"))
    try:
        p = Printer(UsbLpTransport(device), paper_width_mm=paper_mm, left_offset_dots=offset)
    except TransportError as exc:
        pytest.skip(f"no VKP80III at {device} ({exc})")
    try:
        yield p
    finally:
        p.close()


@pytest.fixture
def print_enabled():
    """Gate paper-consuming tests behind VKP80III_PRINT=1."""
    if not os.environ.get("VKP80III_PRINT"):
        pytest.skip("set VKP80III_PRINT=1 to run paper-consuming tests")
