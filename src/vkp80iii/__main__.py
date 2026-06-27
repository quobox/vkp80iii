"""Command-line entry point: ``python -m vkp80iii <command>``.

Commands:
  status      query and print the printer status + counters
  info        show USB device id / ROM version
  selftest    print a short demo ticket and present/cut
  calibrate   print a mm ruler to measure the horizontal offset of narrow paper
  hexdump     build the selftest ticket but print the raw bytes (no hardware)

Use ``--paper-width-mm`` and ``--left-offset-dots`` to match your roll (see the
README "Narrow paper" section).
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import commands as c
from .constants import Justify
from .exceptions import PrinterError, StatusTimeout, TransportError
from .printer import Printer
from .transport import DEFAULT_USBLP_PATH, DummyTransport, UsbLpTransport


def _build_selftest(p: Printer) -> None:
    p.begin()  # reset + apply paper width / left offset
    p.align(Justify.CENTER)
    p.char_size(2, 2).bold().textln("VKP80III").bold(False).char_size(1, 1)
    p.textln("python driver self-test")
    p.textln(f"v{__version__}")
    p.textln("--------------------------------")
    p.align(Justify.LEFT)
    p.textln("Normal text")
    p.bold().textln("Bold text").bold(False)
    p.underline().textln("Underlined").underline(0)
    p.italic().textln("Italic").italic(False)
    p.reverse().textln(" Reversed ").reverse(False)
    p.newline()
    p.align(Justify.CENTER)
    p.qrcode("https://github.com/quobox/vkp80iii", module_size=5)
    p.feed(3)


def cmd_status(args: argparse.Namespace) -> int:
    with _printer(args) as p:
        try:
            st = p.status()
        except (StatusTimeout, PrinterError):
            print("no status reply (check power / bidirectional cable)", file=sys.stderr)
            return 2
        print(st)
        for name in ("paper_present", "low_paper", "cover_open", "ticket_in_output", "ready"):
            print(f"  {name:<18}: {getattr(st, name)}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    with _printer(args) as p:
        try:
            print(f"device id  : {p.device_id().hex(' ')}")
            print(f"rom version: {p.rom_version()!r}")
        except StatusTimeout:
            print("no reply from device", file=sys.stderr)
            return 2
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    with _printer(args) as p:
        _build_selftest(p)
        if args.cut:
            p.cut()
        else:
            p.present(steps=8, blink_led=True, timeout_s=args.timeout)
    print("self-test ticket sent")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Print a 0..70 mm ruler so you can read where the paper edges fall."""
    with _printer(args) as p:
        p.reset()
        p.align(Justify.LEFT)
        for mm in range(0, 71, 10):
            p.send(c.set_absolute_position(mm * 8))
            p.text(str(mm))
        p.send(c.lf())
        for mm in range(0, 71, 5):
            p.send(c.set_absolute_position(mm * 8))
            p.text(":")
        p.send(c.lf())
        p.feed(2)
        p.present(steps=8, blink_led=True, timeout_s=args.timeout)
    print(
        "ruler printed. Read the mm value at the LEFT paper edge -> left_offset_dots = mm*8;\n"
        "width = (right edge mm - left edge mm) * 8."
    )
    return 0


def cmd_hexdump(args: argparse.Namespace) -> int:
    t = DummyTransport()
    p = Printer(
        t, paper_width_mm=args.paper_width_mm, left_offset_dots=args.left_offset_dots, auto_open=False
    )
    _build_selftest(p)
    p.cut()
    data = bytes(t.buffer)
    print(f"# self-test = {len(data)} bytes")
    print(data.hex(" "))
    return 0


def _printer(args: argparse.Namespace) -> Printer:
    kw = {"paper_width_mm": args.paper_width_mm, "left_offset_dots": args.left_offset_dots}
    if args.dry_run:
        return Printer(DummyTransport(), **kw)
    try:
        return Printer(UsbLpTransport(args.device), **kw)
    except TransportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def main(argv: list[str] | None = None) -> int:
    # Shared options live on a parent parser so they work AFTER the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--device", default=DEFAULT_USBLP_PATH, help=f"device node (default {DEFAULT_USBLP_PATH})"
    )
    common.add_argument(
        "--paper-width-mm", type=float, default=80.0, help="usable print width in mm (default 80)"
    )
    common.add_argument(
        "--left-offset-dots", type=int, default=0, help="horizontal offset to the paper's left edge in dots"
    )
    common.add_argument(
        "--timeout", type=int, default=0, help="present timeout seconds (0 = hold until taken)"
    )
    common.add_argument("--dry-run", action="store_true", help="use a dummy transport (no hardware)")

    parser = argparse.ArgumentParser(
        prog="vkp80iii", description="Custom VKP80III thermal printer CLI", parents=[common]
    )
    parser.add_argument("--version", action="version", version=f"vkp80iii {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="query printer status", parents=[common]).set_defaults(func=cmd_status)
    sub.add_parser("info", help="show device id / ROM version", parents=[common]).set_defaults(func=cmd_info)
    st = sub.add_parser("selftest", help="print a demo ticket", parents=[common])
    st.add_argument("--cut", action="store_true", help="plain cut instead of present")
    st.set_defaults(func=cmd_selftest)
    sub.add_parser(
        "calibrate", help="print a mm ruler to measure paper offset", parents=[common]
    ).set_defaults(func=cmd_calibrate)
    sub.add_parser("hexdump", help="dump the self-test bytes (no hardware)", parents=[common]).set_defaults(
        func=cmd_hexdump
    )

    args = parser.parse_args(argv)
    if not (0 <= args.timeout <= 255):
        parser.error("--timeout must be between 0 and 255 seconds")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
