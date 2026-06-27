# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-26

Initial release.

### Added

- High-level, chainable `Printer` API and a pure, fully unit-tested low-level
  `commands` byte encoder for the native VKP80III emulation.
- Text & formatting: bold, italic, underline, double-strike, reverse,
  upside-down, 90° rotation, fonts, character size, code pages and international
  character sets, alignment, tabs, margins, line spacing.
- Barcodes: 1D (UPC, EAN, CODE39/93/128, ITF, CODABAR, CODE32) and 2D
  (QR, PDF417; DataMatrix/Aztec where the firmware supports them).
- Raster image printing from Pillow images, plus flash-logo upload
  (`upload_logo`) and print-by-number (`print_logo`).
- Cutting and presenter/ejector control: cut, present, retract, COLLECT and
  EJECT modes; black-mark alignment workflow.
- Status & monitoring: full/paper/offline/error status decoding,
  `enable_auto_status_back` (push) and polling, maintenance counters, device id
  and ROM version, flash log retrieval; bezel LED bar control.
- Transports: `UsbLpTransport` (kernel `usblp`), `PyUsbTransport` (libusb),
  `SerialTransport` (RS232) and an in-memory `DummyTransport` for tests/dry runs.
- CLI (`vkp80iii` / `python -m vkp80iii`): `status`, `info`, `selftest`,
  `calibrate`, `hexdump`.
- Examples: receipt, full feature showcase, polling/push monitor, presenter
  modes, LED demo, host-rendered 2D codes, and logo printing (raster + flash).
- Typed package (`py.typed`); ships type stubs for the untyped `pyusb`.
- Zero required runtime dependencies; optional `image` / `usb` / `serial` extras.

[Unreleased]: https://github.com/quobox/vkp80iii/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/quobox/vkp80iii/releases/tag/v0.1.0
