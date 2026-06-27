from _typeshed import Incomplete

from ctypes import *
import errno
import os
import usb.backend
import usb.util
import sys
from usb.core import USBError, USBTimeoutError
from usb._debug import methodtrace
import usb._interop as _interop
import logging
import usb.libloader


def get_backend(find_library: Incomplete = None) -> _LibUSB | None: ...
