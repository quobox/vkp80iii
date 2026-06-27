"""Exception hierarchy for the vkp80iii package."""

from __future__ import annotations


class VKPError(Exception):
    """Base class for all errors raised by this library."""


class TransportError(VKPError):
    """A low-level I/O problem talking to the printer (open/read/write)."""


class TransportNotConnected(TransportError):
    """An operation was attempted before the transport was opened."""


class StatusTimeout(TransportError):
    """The printer did not answer a real-time status query in time."""


class PrinterError(VKPError):
    """The printer reported a fault condition (cover open, paper end, ...)."""


class CommandError(VKPError):
    """A command was built with an out-of-range or invalid argument."""
