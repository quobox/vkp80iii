from _typeshed import Incomplete

from ctypes import *
import usb.util
import sys
import logging
from usb._debug import methodtrace
import usb._interop as _interop
import usb._objfinalizer as _objfinalizer
import errno
import math
from usb.core import USBError, USBTimeoutError
import usb.libloader

LIBUSB_SUCCESS: Literal[0] = 0
LIBUSB_ERROR_IO: Literal[-1]
LIBUSB_ERROR_INVALID_PARAM: Literal[-2]
LIBUSB_ERROR_ACCESS: Literal[-3]
LIBUSB_ERROR_NO_DEVICE: Literal[-4]
LIBUSB_ERROR_NOT_FOUND: Literal[-5]
LIBUSB_ERROR_BUSY: Literal[-6]
LIBUSB_ERROR_TIMEOUT: Literal[-7]
LIBUSB_ERROR_OVERFLOW: Literal[-8]
LIBUSB_ERROR_PIPE: Literal[-9]
LIBUSB_ERROR_INTERRUPTED: Literal[-10]
LIBUSB_ERROR_NO_MEM: Literal[-11]
LIBUSB_ERROR_NOT_SUPPORTED: Literal[-12]
LIBUSB_ERROR_OTHER: Literal[-99]
LIBUSB_TRANSFER_COMPLETED: Literal[0] = 0
LIBUSB_TRANSFER_ERROR: Literal[1] = 1
LIBUSB_TRANSFER_TIMED_OUT: Literal[2] = 2
LIBUSB_TRANSFER_CANCELLED: Literal[3] = 3
LIBUSB_TRANSFER_STALL: Literal[4] = 4
LIBUSB_TRANSFER_NO_DEVICE: Literal[5] = 5
LIBUSB_TRANSFER_OVERFLOW: Literal[6] = 6


def get_backend(find_library: Incomplete = None) -> _LibUSB | None: ...
