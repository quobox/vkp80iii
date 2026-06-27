from _typeshed import Incomplete

import usb.core as core
import usb.util as util
import usb._objfinalizer as _objfinalizer
import usb.control as control
from itertools import groupby

__author__: Literal['Wander Lairson Costa'] = 'Wander Lairson Costa'
USBError: type[USBError]
CLASS_AUDIO: Literal[1] = 1
CLASS_COMM: Literal[2] = 2
CLASS_DATA: Literal[10] = 10
CLASS_HID: Literal[3] = 3
CLASS_HUB: Literal[9] = 9
CLASS_MASS_STORAGE: Literal[8] = 8
CLASS_PER_INTERFACE: Literal[0] = 0
CLASS_PRINTER: Literal[7] = 7
CLASS_WIRELESS_CONTROLLER: Literal[224] = 224
CLASS_VENDOR_SPEC: Literal[255] = 255
DT_CONFIG: Literal[2] = 2
DT_CONFIG_SIZE: Literal[9] = 9
DT_DEVICE: Literal[1] = 1
DT_DEVICE_SIZE: Literal[18] = 18
DT_ENDPOINT: Literal[5] = 5
DT_ENDPOINT_AUDIO_SIZE: Literal[9] = 9
DT_ENDPOINT_SIZE: Literal[7] = 7
DT_HID: Literal[33] = 33
DT_HUB: Literal[41] = 41
DT_HUB_NONVAR_SIZE: Literal[7] = 7
DT_INTERFACE: Literal[4] = 4
DT_INTERFACE_SIZE: Literal[9] = 9
DT_PHYSICAL: Literal[35] = 35
DT_REPORT: Literal[34] = 34
DT_STRING: Literal[3] = 3
ENDPOINT_ADDRESS_MASK: Literal[15] = 15
ENDPOINT_DIR_MASK: Literal[128] = 128
ENDPOINT_IN: Literal[128] = 128
ENDPOINT_OUT: Literal[0] = 0
ENDPOINT_TYPE_BULK: Literal[2] = 2
ENDPOINT_TYPE_CONTROL: Literal[0] = 0
ENDPOINT_TYPE_INTERRUPT: Literal[3] = 3
ENDPOINT_TYPE_ISOCHRONOUS: Literal[1] = 1
ENDPOINT_TYPE_MASK: Literal[3] = 3
ERROR_BEGIN: Literal[500000] = 500000
MAXALTSETTING: Literal[128] = 128
MAXCONFIG: Literal[8] = 8
MAXENDPOINTS: Literal[32] = 32
MAXINTERFACES: Literal[32] = 32
PROTOCOL_BLUETOOTH_PRIMARY_CONTROLLER: Literal[1] = 1
RECIP_DEVICE: Literal[0] = 0
RECIP_ENDPOINT: Literal[2] = 2
RECIP_INTERFACE: Literal[1] = 1
RECIP_OTHER: Literal[3] = 3
REQ_CLEAR_FEATURE: Literal[1] = 1
REQ_GET_CONFIGURATION: Literal[8] = 8
REQ_GET_DESCRIPTOR: Literal[6] = 6
REQ_GET_INTERFACE: Literal[10] = 10
REQ_GET_STATUS: Literal[0] = 0
REQ_SET_ADDRESS: Literal[5] = 5
REQ_SET_CONFIGURATION: Literal[9] = 9
REQ_SET_DESCRIPTOR: Literal[7] = 7
REQ_SET_FEATURE: Literal[3] = 3
REQ_SET_INTERFACE: Literal[11] = 11
REQ_SYNCH_FRAME: Literal[12] = 12
SUBCLASS_RF_CONTROLLER: Literal[1] = 1
TYPE_CLASS: Literal[32] = 32
TYPE_RESERVED: Literal[96] = 96
TYPE_STANDARD: Literal[0] = 0
TYPE_VENDOR: Literal[64] = 64


class Endpoint(object):
    address: Incomplete
    interval: Incomplete
    maxPacketSize: Incomplete
    type: Incomplete

    def __init__(self, ep: Incomplete) -> None: ...


class Interface(object):
    alternateSetting: Incomplete
    endpoints: list[Endpoint]
    iInterface: Incomplete
    interfaceClass: Incomplete
    interfaceNumber: Incomplete
    interfaceProtocol: Incomplete
    interfaceSubClass: Incomplete

    def __init__(self, intf: Incomplete) -> None: ...


class Configuration(object):
    iConfiguration: Incomplete
    interfaces: list[list[Interface]]
    maxPower: Incomplete
    remoteWakeup: Incomplete
    selfPowered: Incomplete
    totalLength: Incomplete
    value: Incomplete

    def __init__(self, cfg: Incomplete) -> None: ...


class DeviceHandle(_objfinalizer.AutoFinalizedObject):
    dev: Incomplete

    def __init__(self, dev: Incomplete) -> None: ...

    def bulkWrite(self, endpoint: Incomplete, buffer: Incomplete, timeout: Incomplete = 100) -> Incomplete: ...

    def bulkRead(self, endpoint: Incomplete, size: Incomplete, timeout: Incomplete = 100) -> Incomplete: ...

    def interruptWrite(self, endpoint: Incomplete, buffer: Incomplete, timeout: Incomplete = 100) -> Incomplete: ...

    def interruptRead(self, endpoint: Incomplete, size: Incomplete, timeout: Incomplete = 100) -> Incomplete: ...

    def controlMsg(self, requestType: Incomplete, request: Incomplete, buffer: Incomplete, value: Incomplete = 0, index: Incomplete = 0, timeout: Incomplete = 100) -> Incomplete: ...

    def clearHalt(self, endpoint: Incomplete) -> None: ...

    def claimInterface(self, interface: Incomplete) -> None: ...

    def releaseInterface(self) -> None: ...

    def reset(self) -> None: ...

    def resetEndpoint(self, endpoint: Incomplete) -> None: ...

    def setConfiguration(self, configuration: Incomplete) -> None: ...

    def setAltInterface(self, alternate: Incomplete) -> None: ...

    def getString(self, index: Incomplete, length: Incomplete, langid: Incomplete = None) -> Incomplete: ...

    def getDescriptor(self, desc_type: Incomplete, desc_index: Incomplete, length: Incomplete, endpoint: Incomplete = -1) -> Incomplete: ...

    def detachKernelDriver(self, interface: Incomplete) -> None: ...


class Device(object):
    configurations: list[Configuration]
    dev: Incomplete
    deviceClass: Incomplete
    deviceProtocol: Incomplete
    deviceSubClass: Incomplete
    deviceVersion: str
    devnum: Incomplete
    filename: str
    iManufacturer: Incomplete
    iProduct: Incomplete
    iSerialNumber: Incomplete
    idProduct: Incomplete
    idVendor: Incomplete
    maxPacketSize: Incomplete
    usbVersion: str

    def __init__(self, dev: Incomplete) -> None: ...

    def open(self) -> DeviceHandle: ...


class Bus(object):
    devices: list[Device]
    dirname: str
    location: Incomplete

    def __init__(self, devices: Incomplete) -> None: ...


def busses() -> Generator[Bus]: ...
