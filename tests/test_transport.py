"""Tests for the transport backends (no real hardware touched)."""

from __future__ import annotations

import pytest

from vkp80iii import (
    DummyTransport,
    PyUsbTransport,
    SerialTransport,
    TransportError,
    TransportNotConnected,
    UsbLpTransport,
)


# =====================================================================
# DummyTransport
# =====================================================================
def test_dummy_write_read_queue():
    t = DummyTransport()
    assert t.is_open is True
    t.write(b"abc")
    t.write(b"de")
    assert bytes(t.buffer) == b"abcde"

    t.queue_read(b"XY")
    assert t.read(1) == b"X"
    assert t.read(5) == b"Y"  # fewer than requested
    assert t.read(1) == b""  # empty when drained


def test_dummy_flush_input_is_noop():
    t = DummyTransport()
    t.queue_read(b"resp")
    t.flush_input()  # must NOT drain queued (simulated) responses
    assert t.read(4) == b"resp"


def test_dummy_clear():
    t = DummyTransport()
    t.write(b"x")
    t.queue_read(b"y")
    t.clear()
    assert bytes(t.buffer) == b""
    assert t.read(1) == b""


def test_dummy_closed_raises():
    t = DummyTransport()
    t.close()
    assert t.is_open is False
    with pytest.raises(TransportNotConnected):
        t.write(b"x")
    with pytest.raises(TransportNotConnected):
        t.read(1)


def test_dummy_context_manager():
    t = DummyTransport()
    t.close()
    with t as ctx:
        assert ctx.is_open is True
        ctx.write(b"hi")
    assert t.is_open is False


# =====================================================================
# UsbLpTransport (error paths only -- never touch the real node)
# =====================================================================
def test_usblp_not_open_initially():
    t = UsbLpTransport("/definitely/not/here/lp0")
    assert t.is_open is False
    with pytest.raises(TransportNotConnected):
        t.write(b"x")


def test_usblp_open_missing_path():
    t = UsbLpTransport("/definitely/not/here/lp0")
    with pytest.raises(TransportError):
        t.open()


def test_usblp_real_io(tmp_path):
    """Exercise the real open/write/read/flush/close path against a temp file."""
    f = tmp_path / "lp"
    f.write_bytes(b"")
    t = UsbLpTransport(str(f))
    assert t.open() is t
    assert t.is_open is True
    t.write(b"hello")
    t.close()
    assert t.is_open is False
    assert f.read_bytes() == b"hello"

    r = UsbLpTransport(str(f))
    with r:  # context manager opens
        assert r.read(5, timeout=0.5) == b"hello"
        assert r.read(1, timeout=0.1) == b""  # at EOF
        r.flush_input()
    assert r.is_open is False


# =====================================================================
# SerialTransport (pyserial installed; bad port -> TransportError)
# =====================================================================
def test_serial_not_open_initially():
    t = SerialTransport("/definitely/not/here/ttyZZ")
    assert t.is_open is False
    with pytest.raises(TransportNotConnected):
        t.write(b"x")


def test_serial_open_bad_port():
    t = SerialTransport("/definitely/not/here/ttyZZ")
    with pytest.raises(TransportError):
        t.open()


# =====================================================================
# PyUsbTransport (write before open -- no USB access needed)
# =====================================================================
def test_pyusb_not_open_initially():
    t = PyUsbTransport(vendor_id=0xFFFF, product_id=0xFFFF)
    assert t.is_open is False
    with pytest.raises(TransportNotConnected):
        t.write(b"x")
    assert t.read(1) == b""  # no IN endpoint -> empty, never raises


class _FakeEpIn:
    """Stand-in for a pyusb bulk-IN endpoint: each read() returns one packet."""

    def __init__(self, packets, wMaxPacketSize=64):
        self.packets = [bytes(p) for p in packets]
        self.wMaxPacketSize = wMaxPacketSize
        self.calls = []

    def read(self, n, timeout=None):
        self.calls.append(n)
        return self.packets.pop(0) if self.packets else b""


class _FakeEpOut:
    def __init__(self):
        self.written = []

    def write(self, data, timeout=None):
        self.written.append(bytes(data))


def test_pyusb_read_buffers_packet_surplus():
    # A bulk transfer returns a whole packet; surplus beyond the requested size
    # must be buffered and served on the next read (the #5 truncation fix).
    t = PyUsbTransport()
    t._dev = object()
    ep = _FakeEpIn([b"ABCDEF"], wMaxPacketSize=64)
    t._ep_in = ep
    assert t.read(2) == b"AB"
    assert ep.calls == [64]  # one transfer, sized max(2, wMaxPacketSize)
    assert t.read(3) == b"CDE"  # served from buffer, no new transfer
    assert t.read(1) == b"F"
    assert ep.calls == [64]
    assert t.read(1) == b""  # buffer drained, next packet empty


def test_pyusb_read_multistep_no_truncation():
    # read a 4-byte size header, then the body, even when one packet holds both.
    t = PyUsbTransport()
    t._dev = object()
    ep = _FakeEpIn([b"\x03\x00\x00\x00xyz"])
    t._ep_in = ep
    assert t.read(4) == b"\x03\x00\x00\x00"
    assert t.read(3) == b"xyz"
    assert ep.calls == [64]  # both served from a single transfer


def test_pyusb_read_accumulates_across_packets():
    t = PyUsbTransport()
    t._dev = object()
    ep = _FakeEpIn([b"AB", b"CD"], wMaxPacketSize=2)
    t._ep_in = ep
    assert t.read(4) == b"ABCD"  # two packets coalesced
    assert ep.calls == [4, 4]


def test_pyusb_read_zero_size():
    t = PyUsbTransport()
    t._dev = object()
    t._ep_in = _FakeEpIn([b"AB"])
    assert t.read(0) == b""


def test_pyusb_write_and_close(monkeypatch):
    import usb.util

    monkeypatch.setattr(usb.util, "dispose_resources", lambda dev: None)
    t = PyUsbTransport()
    t._dev = object()
    out = _FakeEpOut()
    t._ep_out = out
    t._ep_in = _FakeEpIn([b"Z"])
    t._rxbuf.extend(b"left-over")
    t.write(b"hi")
    assert out.written == [b"hi"]
    t.close()
    assert t.is_open is False
    assert t._ep_out is None and t._ep_in is None
    assert bytes(t._rxbuf) == b""  # buffer cleared on close


# =====================================================================
# SerialTransport (fake pyserial object -- no real port)
# =====================================================================
class _FakeSerial:
    def __init__(self, read_value=b"", fail=None):
        self.is_open = True
        self.written = []
        self.flushed = 0
        self.timeout = None
        self._read_value = read_value
        self._fail = fail

    def write(self, data):
        if self._fail == "write":
            raise OSError("boom")
        self.written.append(bytes(data))

    def flush(self):
        self.flushed += 1

    def read(self, n):
        if self._fail == "read":
            raise OSError("boom")
        return self._read_value[:n]

    def close(self):
        self.is_open = False


def test_pyusb_close_noop_when_not_open():
    PyUsbTransport().close()  # no _dev -> returns without touching usb


def test_serial_close_noop_when_not_open():
    SerialTransport("/dev/ttyX").close()  # no _ser -> returns cleanly


def test_serial_read_before_open_raises():
    t = SerialTransport("/dev/ttyX")
    with pytest.raises(TransportNotConnected):
        t.read(1)


def test_serial_write_read_close_with_fake():
    t = SerialTransport("/dev/ttyX")
    t._ser = _FakeSerial(read_value=b"OK")
    assert t.is_open is True
    t.write(b"hi")
    assert t._ser.written == [b"hi"] and t._ser.flushed == 1
    assert t.read(2, timeout=0.5) == b"OK"
    assert t._ser.timeout == 0.5  # timeout applied before the read
    t.close()
    assert t.is_open is False


def test_serial_io_errors_wrap_as_transporterror():
    tw = SerialTransport("/dev/ttyX")
    tw._ser = _FakeSerial(fail="write")
    with pytest.raises(TransportError):
        tw.write(b"x")
    tr = SerialTransport("/dev/ttyX")
    tr._ser = _FakeSerial(fail="read")
    with pytest.raises(TransportError):
        tr.read(1)
