from _typeshed import Incomplete

import usb.util as util
import usb.core as core

ENDPOINT_HALT: Literal[0] = 0
FUNCTION_SUSPEND: Literal[0] = 0
DEVICE_REMOTE_WAKEUP: Literal[1] = 1
U1_ENABLE: Literal[48] = 48
U2_ENABLE: Literal[49] = 49
LTM_ENABLE: Literal[50] = 50


def get_status(dev: Incomplete, recipient: Incomplete = None) -> Incomplete: ...


def clear_feature(dev: Incomplete, feature: Incomplete, recipient: Incomplete = None) -> None: ...


def set_feature(dev: Incomplete, feature: Incomplete, recipient: Incomplete = None) -> None: ...


def get_descriptor(dev: Incomplete, desc_size: Incomplete, desc_type: Incomplete, desc_index: Incomplete, wIndex: Incomplete = 0) -> Incomplete: ...


def set_descriptor(dev: Incomplete, desc: Incomplete, desc_type: Incomplete, desc_index: Incomplete, wIndex: Incomplete = None) -> None: ...


def get_configuration(dev: Incomplete) -> Incomplete: ...


def set_configuration(dev: Incomplete, bConfigurationNumber: Incomplete) -> None: ...


def get_interface(dev: Incomplete, bInterfaceNumber: Incomplete) -> Incomplete: ...


def set_interface(dev: Incomplete, bInterfaceNumber: Incomplete, bAlternateSetting: Incomplete) -> None: ...
