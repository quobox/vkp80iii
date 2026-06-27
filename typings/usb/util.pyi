from _typeshed import Incomplete

__author__: Literal['Wander Lairson Costa'] = 'Wander Lairson Costa'

import operator
import array

DESC_TYPE_DEVICE: Literal[1] = 0x01
DESC_TYPE_CONFIG: Literal[2] = 0x02
DESC_TYPE_STRING: Literal[3] = 0x03
DESC_TYPE_INTERFACE: Literal[4] = 0x04
DESC_TYPE_ENDPOINT: Literal[5] = 0x05
ENDPOINT_IN: Literal[128] = 0x80
ENDPOINT_OUT: Literal[0] = 0x00
ENDPOINT_TYPE_CTRL: Literal[0] = 0x00
ENDPOINT_TYPE_ISO: Literal[1] = 0x01
ENDPOINT_TYPE_BULK: Literal[2] = 0x02
ENDPOINT_TYPE_INTR: Literal[3] = 0x03
CTRL_TYPE_STANDARD: int
CTRL_TYPE_CLASS: int
CTRL_TYPE_VENDOR: int
CTRL_TYPE_RESERVED: int
CTRL_RECIPIENT_DEVICE: Literal[0] = 0
CTRL_RECIPIENT_INTERFACE: Literal[1] = 1
CTRL_RECIPIENT_ENDPOINT: Literal[2] = 2
CTRL_RECIPIENT_OTHER: Literal[3] = 3
CTRL_OUT: Literal[0] = 0x00
CTRL_IN: Literal[128] = 0x80
SPEED_LOW: Literal[1] = 1
SPEED_FULL: Literal[2] = 2
SPEED_HIGH: Literal[3] = 3
SPEED_SUPER: Literal[4] = 4
SPEED_UNKNOWN: Literal[0] = 0


def endpoint_address(address: Incomplete) -> Incomplete: ...


def endpoint_direction(address: Incomplete) -> Incomplete: ...


def endpoint_type(bmAttributes: Incomplete) -> Incomplete: ...


def ctrl_direction(bmRequestType: Incomplete) -> Incomplete: ...


def build_request_type(direction: Incomplete, type: Incomplete, recipient: Incomplete) -> Incomplete: ...


def create_buffer(length: Incomplete) -> array[int]: ...


def find_descriptor(desc: Incomplete, find_all: Incomplete = False, custom_match: Incomplete = None, **args: Incomplete) -> Incomplete: ...


def claim_interface(device: Incomplete, interface: Incomplete) -> None: ...


def release_interface(device: Incomplete, interface: Incomplete) -> None: ...


def dispose_resources(device: Incomplete) -> None: ...


def get_langids(dev: Incomplete) -> Incomplete: ...


def get_string(dev: Incomplete, index: Incomplete, langid: Incomplete = None) -> Incomplete: ...
