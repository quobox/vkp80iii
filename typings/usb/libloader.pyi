from _typeshed import Incomplete

import ctypes
import ctypes.util
import logging
import os.path
import platform
import sys


class LibraryException(OSError):
    ...


class LibraryNotFoundException(LibraryException):
    ...


class NoLibraryCandidatesException(LibraryNotFoundException):
    ...


class LibraryNotLoadedException(LibraryException):
    ...


class LibraryMissingSymbolsException(LibraryException):
    ...


def locate_library(candidates: Incomplete, find_library: Incomplete = ...) -> Incomplete: ...


def load_library(lib: Incomplete, name: Incomplete = None, lib_cls: Incomplete = None) -> Incomplete: ...


def load_locate_library(candidates: Incomplete, cygwin_lib: Incomplete, name: Incomplete, win_cls: Incomplete = None, cygwin_cls: Incomplete = None, others_cls: Incomplete = None, find_library: Incomplete = None, check_symbols: Incomplete = None) -> Incomplete: ...
