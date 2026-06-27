"""Transport backends for talking to a VKP80III.

The printer enumerates as a USB printer-class device, so on Linux the kernel
``usblp`` driver exposes it as a character device (typically
``/dev/usb/lp0``). Writing raw command bytes to that node drives the printer;
reading from it returns the bytes the printer sends back (real-time status,
device id, counters, ...).

Four backends are provided:

* :class:`UsbLpTransport` -- the default on Linux, talks to ``/dev/usb/lp0``.
* :class:`PyUsbTransport` -- direct libusb access (no kernel driver / udev
  rule needed), requires ``pyusb``.
* :class:`SerialTransport` -- RS232 models, requires ``pyserial``.
* :class:`DummyTransport` -- records everything written, reads nothing; for
  tests and dry runs.

All backends share the :class:`Transport` interface so the high-level
:class:`~vkp80iii.printer.Printer` does not care which one it uses.
"""

from __future__ import annotations

import contextlib
import errno
import os
import select
import time
from abc import ABC, abstractmethod
from typing import Any

from .exceptions import TransportError, TransportNotConnected

#: Custom Engineering S.p.A. USB vendor id.
USB_VENDOR_ID = 0x0DD4
#: VKP80III USB product id.
USB_PRODUCT_ID = 0x0205
#: Default character device created by the kernel ``usblp`` driver.
DEFAULT_USBLP_PATH = "/dev/usb/lp0"


class Transport(ABC):
    """Abstract bidirectional byte channel to a printer."""

    @abstractmethod
    def open(self) -> Transport:
        """Acquire the underlying resource. Returns ``self``."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying resource. Must be idempotent."""

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Send ``data`` to the printer in full."""

    @abstractmethod
    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        """Read up to ``size`` bytes, waiting at most ``timeout`` seconds.

        Returns the bytes received, which may be fewer than ``size`` (or empty)
        if the printer stops sending before the timeout elapses.
        """

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Whether the transport currently holds an open resource."""

    # -- convenience -----------------------------------------------------
    def flush_input(self) -> None:
        """Discard any pending input bytes (best effort)."""
        try:
            while self.read(4096, timeout=0.0):
                pass
        except TransportError:
            pass

    def __enter__(self) -> Transport:
        if not self.is_open:
            self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class UsbLpTransport(Transport):
    """Talk to the printer through the kernel ``usblp`` device node.

    This is the recommended backend on Linux. The user running the process
    needs read/write access to the node (group ``lp`` or a udev rule -- see
    the README).
    """

    def __init__(self, path: str = DEFAULT_USBLP_PATH) -> None:
        self.path = path
        self._fd: int | None = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def open(self) -> UsbLpTransport:
        if self._fd is not None:
            return self
        try:
            # O_RDWR: usblp is bidirectional so we can read status back.
            self._fd = os.open(self.path, os.O_RDWR)
        except FileNotFoundError as exc:
            raise TransportError(
                f"{self.path} does not exist. Is the printer connected and the "
                f"usblp kernel module loaded? (try: lsusb | grep -i custom)"
            ) from exc
        except PermissionError as exc:
            raise TransportError(
                f"No permission to open {self.path}. Add your user to the 'lp' "
                f"group or install a udev rule (see README)."
            ) from exc
        except OSError as exc:
            raise TransportError(f"Could not open {self.path}: {exc}") from exc
        return self

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None

    def write(self, data: bytes) -> None:
        if self._fd is None:
            raise TransportNotConnected("transport is not open")
        mv = memoryview(data)
        total = 0
        while total < len(mv):
            try:
                n = os.write(self._fd, mv[total:])
            except OSError as exc:
                if exc.errno == errno.EAGAIN:
                    time.sleep(0.005)
                    continue
                raise TransportError(f"write to {self.path} failed: {exc}") from exc
            if n == 0:
                raise TransportError(f"write to {self.path} returned 0 bytes")
            total += n

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        if self._fd is None:
            raise TransportNotConnected("transport is not open")
        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        remaining = size
        while remaining > 0:
            budget = max(0.0, deadline - time.monotonic())
            r, _, _ = select.select([self._fd], [], [], budget)
            if not r:
                break  # timed out waiting for more data
            try:
                chunk = os.read(self._fd, remaining)
            except OSError as exc:
                if exc.errno == errno.EAGAIN:
                    continue
                raise TransportError(f"read from {self.path} failed: {exc}") from exc
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)


class PyUsbTransport(Transport):
    """Direct libusb access via ``pyusb`` (no kernel usblp node required).

    Useful when you cannot create a udev rule, on non-Linux hosts, or when the
    usblp driver is unloaded. Requires the ``usb`` extra (``pip install
    vkp80iii[usb]``) and libusb installed on the system.
    """

    def __init__(
        self,
        vendor_id: int = USB_VENDOR_ID,
        product_id: int = USB_PRODUCT_ID,
        interface: int = 0,
    ) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.interface = interface
        self._dev = None
        self._ep_out = None
        self._ep_in = None
        self._reattach = False
        self._rxbuf = bytearray()  # bytes read from a packet beyond the requested size

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    def open(self) -> PyUsbTransport:
        if self._dev is not None:
            return self
        try:
            import usb.core
            import usb.util
        except ImportError as exc:  # pragma: no cover - optional dep
            raise TransportError(
                "PyUsbTransport requires pyusb. Install with: pip install vkp80iii[usb]"
            ) from exc

        dev = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
        if dev is None:
            raise TransportError(f"No USB device {self.vendor_id:04x}:{self.product_id:04x} found.")
        # The kernel usblp driver usually grabs the interface; detach it.
        try:
            if dev.is_kernel_driver_active(self.interface):
                dev.detach_kernel_driver(self.interface)
                self._reattach = True
        except (NotImplementedError, usb.core.USBError):
            pass

        dev.set_configuration()
        cfg = dev.get_active_configuration()
        intf = cfg[(self.interface, 0)]

        self._ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
        )
        self._ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN,
        )
        if self._ep_out is None:
            raise TransportError("No bulk OUT endpoint found on the printer.")
        self._dev = dev
        return self

    def close(self) -> None:
        if self._dev is None:
            return
        try:
            import usb.util

            usb.util.dispose_resources(self._dev)
            if self._reattach:
                with contextlib.suppress(Exception):  # pragma: no cover
                    self._dev.attach_kernel_driver(self.interface)
        finally:
            self._dev = None
            self._ep_out = None
            self._ep_in = None
            self._reattach = False
            self._rxbuf.clear()

    def write(self, data: bytes) -> None:
        if self._ep_out is None:
            raise TransportNotConnected("transport is not open")
        try:
            self._ep_out.write(data, timeout=5000)
        except Exception as exc:  # pragma: no cover - hardware dependent
            raise TransportError(f"USB write failed: {exc}") from exc

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        if self._ep_in is None or size <= 0:
            # No IN endpoint -> status reads not supported on this backend.
            return b""
        # A bulk transfer returns a whole packet (>= size); keep any surplus in
        # _rxbuf so multi-step replies (e.g. read a size header, then the body)
        # are not truncated.
        ms = max(1, int(timeout * 1000))
        while len(self._rxbuf) < size:
            try:
                chunk = self._ep_in.read(max(size, self._ep_in.wMaxPacketSize), timeout=ms)
            except Exception as exc:  # pragma: no cover - hardware dependent
                import usb.core

                if isinstance(exc, usb.core.USBTimeoutError):
                    break  # nothing more arrived in time; return what we have
                raise TransportError(f"USB read failed: {exc}") from exc
            if not len(chunk):
                break
            self._rxbuf.extend(bytes(chunk))
        out = bytes(self._rxbuf[:size])
        del self._rxbuf[:size]
        return out


class SerialTransport(Transport):
    """RS232 backend for serial VKP80III models. Requires ``pyserial``."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        rtscts: bool = True,
        **kwargs: Any,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.rtscts = rtscts
        self._kwargs = kwargs
        self._ser = None

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def open(self) -> SerialTransport:
        try:
            import serial
        except ImportError as exc:  # pragma: no cover - optional dep
            raise TransportError(
                "SerialTransport requires pyserial. Install with: pip install vkp80iii[serial]"
            ) from exc
        try:
            self._ser = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                rtscts=self.rtscts,
                timeout=1.0,
                write_timeout=5.0,
                **self._kwargs,
            )
        except Exception as exc:
            raise TransportError(f"Could not open serial port {self.port}: {exc}") from exc
        return self

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def write(self, data: bytes) -> None:
        if self._ser is None:
            raise TransportNotConnected("transport is not open")
        try:
            self._ser.write(data)
            self._ser.flush()
        except Exception as exc:
            raise TransportError(f"serial write failed: {exc}") from exc

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        if self._ser is None:
            raise TransportNotConnected("transport is not open")
        self._ser.timeout = timeout
        try:
            return self._ser.read(size)
        except Exception as exc:
            raise TransportError(f"serial read failed: {exc}") from exc


class DummyTransport(Transport):
    """In-memory transport that records writes and replays queued reads.

    Handy for unit tests and dry runs::

        t = DummyTransport()
        Printer(t).text("hi").cut()
        assert t.buffer == b"hi" + b"\\x1dV\\x00"
    """

    def __init__(self) -> None:
        self.buffer = bytearray()
        self._read_queue = bytearray()
        self._open = True

    @property
    def is_open(self) -> bool:
        return self._open

    def open(self) -> DummyTransport:
        self._open = True
        return self

    def close(self) -> None:
        self._open = False

    def flush_input(self) -> None:
        # Queued reads represent explicit simulated responses, not stale input,
        # so flushing must not drain them.
        return None

    def write(self, data: bytes) -> None:
        if not self._open:
            raise TransportNotConnected("transport is not open")
        self.buffer.extend(data)

    def read(self, size: int = 1, timeout: float = 1.0) -> bytes:
        if not self._open:
            raise TransportNotConnected("transport is not open")
        n = min(size, len(self._read_queue))
        out = bytes(self._read_queue[:n])
        del self._read_queue[:n]
        return out

    # -- test helpers ----------------------------------------------------
    def queue_read(self, data: bytes) -> None:
        """Queue bytes to be returned by subsequent :meth:`read` calls."""
        self._read_queue.extend(data)

    def clear(self) -> None:
        self.buffer.clear()
        self._read_queue.clear()
