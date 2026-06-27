from _typeshed import Incomplete

from ctypes import *
import ctypes.util
import usb.util
from usb._debug import methodtrace
import logging
import errno
import sys
import usb._interop as _interop
import usb._objfinalizer as _objfinalizer
import usb.util as util
import usb.libloader
from usb.core import USBError, USBTimeoutError

OPENUSB_SUCCESS: Literal[0] = 0
OPENUSB_PLATFORM_FAILURE: Literal[-1]
OPENUSB_NO_RESOURCES: Literal[-2]
OPENUSB_NO_BANDWIDTH: Literal[-3]
OPENUSB_NOT_SUPPORTED: Literal[-4]
OPENUSB_HC_HARDWARE_ERROR: Literal[-5]
OPENUSB_INVALID_PERM: Literal[-6]
OPENUSB_BUSY: Literal[-7]
OPENUSB_BADARG: Literal[-8]
OPENUSB_NOACCESS: Literal[-9]
OPENUSB_PARSE_ERROR: Literal[-10]
OPENUSB_UNKNOWN_DEVICE: Literal[-11]
OPENUSB_INVALID_HANDLE: Literal[-12]
OPENUSB_SYS_FUNC_FAILURE: Literal[-13]
OPENUSB_NULL_LIST: Literal[-14]
OPENUSB_CB_CONTINUE: Literal[-20]
OPENUSB_CB_TERMINATE: Literal[-21]
OPENUSB_IO_STALL: Literal[-50]
OPENUSB_IO_CRC_ERROR: Literal[-51]
OPENUSB_IO_DEVICE_HUNG: Literal[-52]
OPENUSB_IO_REQ_TOO_BIG: Literal[-53]
OPENUSB_IO_BIT_STUFFING: Literal[-54]
OPENUSB_IO_UNEXPECTED_PID: Literal[-55]
OPENUSB_IO_DATA_OVERRUN: Literal[-56]
OPENUSB_IO_DATA_UNDERRUN: Literal[-57]
OPENUSB_IO_BUFFER_OVERRUN: Literal[-58]
OPENUSB_IO_BUFFER_UNDERRUN: Literal[-59]
OPENUSB_IO_PID_CHECK_FAILURE: Literal[-60]
OPENUSB_IO_DATA_TOGGLE_MISMATCH: Literal[-61]
OPENUSB_IO_TIMEOUT: Literal[-62]
OPENUSB_IO_CANCELED: Literal[-63]


def get_backend(find_library: Incomplete = None) -> _OpenUSB | None: ...
