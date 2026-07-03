# vkp80iii

Pure-Python driver for the **Custom VKP80III** thermal ticket /
receipt printer. Independent, unofficial project — not affiliated with Custom
S.p.A. (see [Disclaimer & trademarks](#disclaimer--trademarks)).

The VKP80III speaks an ESC/POS-derived command set (its *VKP80III emulation*)
with Custom-specific extensions for the **presenter/ejector**, **black-mark
alignment**, the **bezel RGB LED bar**, **stored logos** and **serial-number
counters**. This library implements that command set from the official
*Commands Manual* (doc. 915DX010100) — no CUPS driver required: it writes raw
command bytes straight to the USB device.

- Zero required dependencies (Pillow / pyusb / pyserial are optional extras).
- A pure, fully unit-tested **byte encoder** (`vkp80iii.commands`) — every
  command is a small function returning the exact bytes.
- An ergonomic, chainable **`Printer`** API on top.
- **Status decoding** (paper, cover, cutter, presenter, errors) and
  maintenance counters.
- Backends for the kernel `usblp` node, raw libusb (`pyusb`), serial, and an
  in-memory dummy for tests/dry-runs.

## Install

```bash
uv sync                 # core only
uv sync --extra all     # + Pillow (images), pyusb, pyserial
```

## Quick start

```python
from vkp80iii import Printer, Justify

with Printer() as p:                       # opens /dev/usb/lp0
    p.reset()
    p.align(Justify.CENTER).char_size(2, 2).bold().textln("CAFE DEMO")
    p.bold(False).char_size(1, 1)
    p.align(Justify.LEFT).textln("1x Espresso          2.50")
    p.qrcode("https://example.com/receipt/1")
    p.feed(3).present()                     # cut + present the ticket at the bezel
```

## Device access (Linux)

The printer enumerates as a USB printer-class device, so the kernel `usblp`
driver exposes it as `/dev/usb/lp0` (owned `root:lp`). Your user needs
read/write access. Pick **one**:

**A) Add yourself to the `lp` group** (simplest):

```bash
sudo usermod -aG lp "$USER"
# log out / back in (or: newgrp lp) for the group to take effect
```

**B) Install a udev rule** (grants access by USB id, survives re-plug):

```bash
sudo tee /etc/udev/rules.d/99-vkp80iii.rules >/dev/null <<'EOF'
# Custom VKP80III
SUBSYSTEM=="usbmisc", ATTRS{idVendor}=="0dd4", ATTRS{idProduct}=="0205", MODE="0660", GROUP="lp"
KERNEL=="lp[0-9]*", SUBSYSTEMS=="usb", ATTRS{idVendor}=="0dd4", ATTRS{idProduct}=="0205", MODE="0660", GROUP="lp"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0dd4", ATTRS{idProduct}=="0205", MODE="0660", GROUP="lp"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Verify: `ls -l /dev/usb/lp0` and `lsusb | grep -i custom`.

> Bidirectional reads (status) require the `usblp` node or the `pyusb` backend.
> If you only need to print, even write-only access is enough.

## CLI

```bash
uv run python -m vkp80iii status        # paper/cover/cutter/ready + counters
uv run python -m vkp80iii info          # USB device id + ROM version
uv run python -m vkp80iii selftest      # print a demo ticket and cut
uv run python -m vkp80iii selftest --present
uv run python -m vkp80iii hexdump       # build the demo ticket, print raw bytes (no hardware)
```

## Narrow paper

The print head is a fixed 576 dots / 72 mm wide, and narrow rolls are
**centered** by the two cursors at the *rear* paper infeed. Where the logical
origin lands depends on the printer's persistent **`PRINT WIDTH`** setup value.

**Recommended (clean) fix — match `PRINT WIDTH` to the paper.** Set it once in
the printer's own setup; then the logical origin *is* the paper's left edge and
text, raster images and barcodes all align. Build the printer with `for_paper()`,
which centers your content on the roll with a small safety margin (this also
keeps left-aligned text off the head's physical non-printable left edge, which
clips the first column by 1–2 px at offset 0):

```python
p = Printer.for_paper(width_mm=58)   # 58 mm roll, 1.5 mm margin each side, centered
p.begin()
# equivalent to: Printer(paper_width_mm=55, left_offset_dots=12)  # (58−55) mm ÷ 2 × 8 = 12
```

To set `PRINT WIDTH` from the front panel: power on while holding **LINE FEED**
(prints the setup report) → press **LINE FEED** to *enter* setup → **FF** = next
parameter, **LF** = change value → step to `Print Width`, set it, then **FF**
through to the end to save (the printer reboots). Re-print the report to verify.

**Can't change the firmware setup?** `PRINT WIDTH` is a global, persistent
setting that affects *every* app using the printer, and on a shared or
panel-less unit you may not want (or be able) to touch it. The width can't be
read back over USB, so measure the offset once and pass it as `left_offset_dots`.
With `PRINT WIDTH` left at its default the paper sits to the *right* of the
logical origin, so the offset is larger than the small centering inset above —
`begin()` still applies `GS L`/`GS W` for text and `Printer.image(...)` blank-pads
raster rows to match:

```bash
uv run python -m vkp80iii calibrate   # ruler: left_offset_dots = (left-edge mm) × 8
```

Either way it's a per-paper-width setting, **not** per roll.

## Choosing a transport

```python
from vkp80iii import Printer, UsbLpTransport, PyUsbTransport, SerialTransport, DummyTransport

Printer(UsbLpTransport("/dev/usb/lp0"))          # default
Printer(PyUsbTransport())                         # raw libusb, no kernel driver
Printer(SerialTransport("/dev/ttyS4", 115200))    # RS232 models
Printer(DummyTransport())                          # capture bytes, no hardware
```

## Feature map

| Area | API |
|------|-----|
| Text & formatting | `text/textln`, `bold`, `italic`, `underline`, `reverse`, `char_size`, `font`, `print_modes`, `upside_down`, `rotate_90` |
| Layout | `align*`, `set_tabs`/`tab`, `left_margin`, `print_area_width`, `absolute_position`, `relative_position`, `line_spacing` |
| Code pages | `code_page`, `charset` (text codec follows the page) |
| 1D barcodes | `barcode(Barcode.*, ...)` (UPC, EAN, CODE39/93/128, ITF, CODABAR, CODE32) + HRI/height/width |
| 2D barcodes | `qrcode`, `pdf417`, `aztec`, `datamatrix` (QR/PDF417 always; DataMatrix/Aztec are firmware-dependent &mdash; not implemented on the tested ROM 7.11) |
| Images / logos | `image(path_or_PIL)` (raster); `upload_logo(n, img)` stores it in flash (`FS 0x94`) &mdash; **power-cycle once afterwards** so the index is re-read &mdash; then `print_logo(n)` prints it by number (`FS 0x93`). Numbers 1/2 are the factory demo |
| Cut / present | `cut([feed])`, `present(...)`, `collect_mode`, `eject_mode`, `presentation_offset` |
| Black-mark | `align_to_printhead`, `align_to_cutter`, `black_mark_distance`, `paper_recovery`, `min_ticket_length` |
| Status | `status()`, `paper_status()`, `is_ready()`, `offline_status`, `error_status`, `enable_auto_status_back` |
| Counters (maint.) | `paper_remaining_cm`, `cut_count`, `printed_length_cm`, `retract_count`, `powerup_count` |
| Diagnostics | `density(level)`, `read_logs()` / `clear_logs()` (flash-disk text logs) |
| Serial counter | `setup_counter`, `print_counter` |
| LED bar | `led((r,g,b))`, `led_off`, `led_flash`, `led_rainbow` &mdash; on/flash/off (`FS B`) work; RGB colour (`FS L`) needs the optional RGB module (the tested unit reports "LED bar RGB: Not Present", so it shows amber only) |

## Barcodes the firmware lacks (host-rendered)

The native 2D set depends on firmware: QR and PDF417 are universal, but
DataMatrix/Aztec aren't implemented on every ROM (e.g. ROM 7.11). Because raster
printing always works, you can render *any* symbology host-side and print it as
an image &mdash; see `examples/render_2d.py` (uses `treepoem` + Ghostscript):

```python
import treepoem
from vkp80iii import Printer

img = treepoem.generate_barcode("datamatrix", "hello").convert("L")
img = img.resize((img.width * 6, img.height * 6))  # ~6 dots/module
with Printer(paper_width_mm=55, left_offset_dots=12) as p:
    p.begin().image(img, threshold=128)
    p.feed(2).present()
```

Any generator that yields a PIL image works (`qrcode`, `pdf417gen`,
`pylibdmtx`, `aztec_code_generator`, ...).

## Kiosk operation & remote monitoring

Everything needed to run unattended is in the command set (reviewed against the
manual — there is **no reboot/restart command**; `ESC @` is only a soft init):

* **Health polling** — `status()` returns a `FullStatus` with `ready` plus every
  flag (paper present/low, virtual paper-end, cover open, head up, jam, cutter,
  RAM/EEPROM, etc.); `is_ready()` and `problems()` summarise it. See
  `examples/monitor.py` for a polling loop that reports changes.
* **Event-driven push** — `enable_auto_status_back()` makes the printer send a
  status frame whenever a category changes (no polling); read them with
  `read_auto_status()`.
* **Consumables / wear** — `paper_remaining_cm()`, `cut_count()`,
  `printed_length_cm()`, `retract_count()`, `powerup_count()` for proactive
  paper-refill and maintenance alerts.
* **Output handling** — presenter modes for self-service: `present()` (eject),
  `present(retract=True)` (retract uncollected tickets), `collect_mode()` (drop
  uncut to the bin). See `examples/presenter.py`.
* **Diagnostics** — `read_logs()` pulls the printer's flash-disk text logs;
  `device_id()` / `rom_version()` for inventory.

```bash
uv run python examples/monitor.py        # poll + report status changes (Ctrl-C)
uv run python examples/monitor.py 5 0    # every 5 s, forever
```

## Black-mark ticket workflow

For pre-printed tickets with a black mark:

```python
p.align_to_printhead()     # start-of-ticket alignment
# ... print the ticket ...
p.align_to_cutter()        # end-of-ticket alignment
p.total_cut()              # ESC i total cut (GS V may not fire the cutter on presenter units)
p.paper_recovery(11)       # pull the stub back so the next ticket starts clean
```

## Low-level access

Every command is also available as a pure function returning bytes:

```python
from vkp80iii import commands as c
data = c.initialize() + c.justify(1) + b"Hello\n" + c.cut()
Printer().send(data)
```

## Development

```bash
uv sync                 # dev tools: pytest, ruff, pyrefly
uv run pytest                       # 130 tests, no hardware needed
uv run pytest --cov=vkp80iii        # + coverage report (fail_under=90, ~92%)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run pyrefly check                # type-check (src/)
uv run --group docs mkdocs serve    # live-preview the docs site at :8000
```

Full documentation (guide + API reference generated from the docstrings) lives in
`docs/` and is built with **MkDocs Material + mkdocstrings**, published to
[quobox.github.io/vkp80iii](https://quobox.github.io/vkp80iii/) on push to
`master`. The vendor manuals are kept locally under `manuals/` (gitignored;
copyrighted, not redistributed).

Lint/format (`ruff`) and the type-checker (`pyrefly`) are configured in
`pyproject.toml`; the source is clean (`ruff`: no findings, `pyrefly`: 0 errors).

`pyusb` ships no type stubs ([pyusb#470](https://github.com/pyusb/pyusb/issues/470)),
so `typings/usb/` holds stubs generated with `pyrefly stubgen` (with
`usb.core.find` hand-refined to `Device | None`); `pyrefly`'s `search-path` points
there. Regenerate with:

```bash
uv run pyrefly stubgen "$(uv run python -c 'import usb,os;print(os.path.dirname(usb.__file__))')" -o typings
```

### Tests

Coverage (all byte-accurate, hardware-free):

| File | Area |
|------|------|
| `test_commands.py` | every low-level encoder + range/validation errors |
| `test_printer.py` | high-level `Printer` API, layout, barcode/QR sequences, status round-trips |
| `test_status.py` | full/paper/offline/error status bit decoding, numeric readings |
| `test_transport.py` | `DummyTransport` behaviour + backend error paths |
| `test_imaging.py` | PIL → raster packing, threshold, resize, invert |

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE). Copyright © 2026 Quobox UG (haftungsbeschränkt) and contributors.

## Disclaimer & trademarks

This is an **independent, unofficial** library. It is **not affiliated with,
authorized by, sponsored by, or endorsed by Custom S.p.A.**

"Custom", "VKP80III", and related product names are trademarks of their respective
owners (Custom S.p.A.). They are used here **only descriptively / nominatively** to
identify the hardware this software interoperates with; no trademark license is
granted or implied.

The software is provided "as is" under the MIT License, without warranty of any
kind — use it with your hardware at your own risk.
