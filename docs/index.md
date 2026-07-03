# vkp80iii

Pure-Python driver for the **Custom VKP80III** thermal ticket /
receipt printer. Independent, unofficial project — not affiliated with Custom
S.p.A.

The VKP80III speaks an ESC/POS-derived command set (its *VKP80III emulation*).
This library gives you a high-level, chainable `Printer` API on top of a pure,
fully unit-tested byte encoder, with no required runtime dependencies.

## Install

```bash
pip install vkp80iii            # core (raw USB via the kernel usblp node)
pip install "vkp80iii[image]"   # + Pillow, for raster image / logo printing
pip install "vkp80iii[all]"     # + Pillow, pyusb and pyserial backends
```

## Quickstart

```python
from vkp80iii import Printer, Justify

with Printer(paper_width_mm=80) as p:       # opens /dev/usb/lp0
    p.begin()                               # reset + apply layout
    p.align(Justify.CENTER).bold().textln("CAFE DEMO").bold(False)
    p.textln("------------------------")
    p.align(Justify.LEFT).textln("1x Espresso      2.50")
    p.qrcode("https://github.com/quobox/vkp80iii")
    p.feed(3).present()                      # cut + present the ticket
```

## Where to next

- **[Guide](guide.md)** — access setup, layout/calibration, printing, status &
  kiosk monitoring, logos.
- **[API reference](api/printer.md)** — generated from the type hints and
  docstrings.

!!! note "Trademarks"
    "Custom" and "VKP80III" are trademarks of their respective owners (Custom
    S.p.A.), used here only descriptively. See the project README for the full
    disclaimer. The software is MIT-licensed and provided "as is".
