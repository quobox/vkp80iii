# Guide

## Device access (Linux)

The printer appears as the kernel `usblp` node `/dev/usb/lp0`. Give your user
access by joining the `lp` group (or install the bundled `99-vkp80iii.rules`):

```bash
sudo usermod -aG lp "$USER"     # then log out/in, or for this shell:
sg lp -c 'python -m vkp80iii status'
```

`TAG+="uaccess"` does **not** work for this device — `systemd-logind` does not
grant ACLs on the usblp character node, so group ownership is the reliable path.

## Connecting & layout

```python
from vkp80iii import Printer

p = Printer(paper_width_mm=80, left_offset_dots=0)   # opens /dev/usb/lp0
p.begin()        # reset (ESC @) + apply left margin and print width
```

- `paper_width_mm` — usable print width; capped at the head's 576 dots (72 mm).
- `left_offset_dots` — horizontal offset from the printer's logical origin to
  the paper's left edge. It depends on the firmware **PRINT WIDTH** setup value
  and the paper guides. Measure it once with the ruler:

```bash
python -m vkp80iii calibrate --paper-width-mm 55
```

Then pass the measured offset (e.g. `Printer(paper_width_mm=55, left_offset_dots=12)`).

For the common case where the firmware `PRINT WIDTH` matches the paper, skip the
arithmetic and use the `for_paper()` factory — it derives the print width and the
centering offset from the physical roll width and a per-side margin:

```python
p = Printer.for_paper(width_mm=58)              # -> paper_width_mm=55, left_offset_dots=12
p = Printer.for_paper(width_mm=58, margin_mm=2) # wider safety margin (-> offset 16)
```

## Text & formatting

Formatting methods are chainable and return `self`:

```python
from vkp80iii import Justify, Underline

p.align(Justify.CENTER).bold().double_strike().textln("HEADER")
p.bold(False).double_strike(False)
p.underline(Underline.SINGLE).textln("underlined").underline(0)
p.align(Justify.LEFT).textln("normal text")
```

Text is encoded with the active code page's codec. `begin()`/`reset()` revert the
device to PC437 and resync the codec; call `p.code_page(CodePage.WPC1252)` for
Western European accents.

## Barcodes

```python
from vkp80iii import Barcode

p.barcode(Barcode.EAN13, "4006381333931")   # 1D, validated length + charset
p.qrcode("https://example.com", module_size=6)
p.pdf417("payload", columns=0)
```

!!! warning "DataMatrix / Aztec"
    The ROM 7.11 firmware does not implement DataMatrix or Aztec — the data
    leaks through as text. Render them host-side as a raster image instead (see
    `examples/render_2d.py`) and print with `p.image(...)`.

## Images & logos

```python
p.image("logo.png")                 # auto-fits width, tall images are banded
```

Logos can also be stored in flash and printed by number:

```python
p.upload_logo(200, "logo.png")      # FS 0x94
# IMPORTANT: power-cycle the printer once, then:
p.print_logo(200)
```

The printer only re-indexes flash logos on boot, so a **power-cycle after upload**
is required before `print_logo` finds the new logo. Slots 1/2 hold the factory
demo logo — use your own number (e.g. 200).

## Cutting, presenter & ejector

```python
p.cut()                 # total cut at the current position
p.cut(feed=40)          # feed then total cut
p.present()             # cut + present the ticket at the bezel
p.eject()               # eject a presented ticket to the customer
p.retract()             # pull an un-taken ticket back in
```

The VKP80III cutter is **total cut only** — there is no partial cut.

## Status & kiosk monitoring

```python
st = p.status()                     # full 6-byte status block
print(st.paper_present, st.cover_open, st.ready)
if not p.is_ready():
    ...                             # paper out / cover open / error

print(p.paper_remaining_cm(), p.cut_count())   # maintenance counters
```

For kiosk operation you can either **poll** `status()` on an interval, or have
the printer **push** status changes automatically:

```python
p.enable_auto_status_back()         # printer emits a frame whenever status changes
while True:
    frame = p.read_auto_status()    # None if nothing pending
    if frame:
        handle(frame)
```

See `examples/monitor.py` for a complete poll-and-push monitor.

## Transports

`Printer()` defaults to `UsbLpTransport` (`/dev/usb/lp0`). Other backends:

```python
from vkp80iii import Printer, PyUsbTransport, SerialTransport, DummyTransport

Printer(PyUsbTransport())                 # libusb, no kernel usblp driver
Printer(SerialTransport("/dev/ttyUSB0"))  # RS232 models
Printer(DummyTransport(), auto_open=False) # in-memory, for tests / dry runs
```
