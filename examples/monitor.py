"""Kiosk monitoring -- polling or event-driven push.

    uv run python examples/monitor.py [interval_s] [max_polls]   # polling (default)
    uv run python examples/monitor.py --push [max_events]        # event-driven push

Polling asks the printer for status on a timer (simple, but up to `interval`
latency). Push (--push) tells the printer to send a status frame the *moment*
anything changes via enable_auto_status_back(), so faults are reported instantly
with no polling traffic. max_polls / max_events = 0 means run forever (Ctrl-C).

In production, forward each event line to your fleet dashboard.
"""

import sys
import time

from vkp80iii import Printer
from vkp80iii.exceptions import PrinterError, StatusTimeout

# No reply or an unparseable/short reply -- both mean "can't read status now".
NO_STATUS = (StatusTimeout, PrinterError)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def summary(st) -> str:
    return "READY" if st.ready else "NOT READY: " + ", ".join(st.problems())


def baseline(p: Printer) -> None:
    try:
        print(f"device {p.device_id().hex(' ')}  ROM {p.rom_version()}", flush=True)
        print(
            f"counters: paper~{p.paper_remaining_cm()} cm, cuts {p.cut_count()}, "
            f"printed~{p.printed_length_cm()} cm, power-ups {p.powerup_count()}",
            flush=True,
        )
        log("start: " + summary(p.status()))
    except NO_STATUS:
        print("warning: no reply to initial query", flush=True)


def run_poll(p: Printer, interval: float, max_polls: int) -> None:
    print(f"POLLING every {interval:g}s (Ctrl-C to stop) ...", flush=True)
    last = object()
    polls = 0
    while max_polls == 0 or polls < max_polls:
        try:
            key = (lambda st: (st.ready, tuple(st.problems())))(st := p.status())
            if key != last:
                log(summary(st))
                last = key
        except NO_STATUS:
            if last != "offline":
                log("NO RESPONSE (printer off / disconnected?)")
                last = "offline"
        polls += 1
        if max_polls == 0 or polls < max_polls:
            time.sleep(interval)


def run_push(p: Printer, max_events: int) -> None:
    p.enable_auto_status_back()  # GS 0xE0: printer pushes a frame on every change
    print("PUSH monitoring -- waiting for events (Ctrl-C to stop) ...", flush=True)
    events = 0
    try:
        while max_events == 0 or events < max_events:
            frame = p.read_auto_status(timeout=30)
            if frame is None:
                continue
            log(summary(frame))
            events += 1
    finally:
        # stop the printer pushing to a channel nobody is reading
        p.enable_auto_status_back(paper=False, user=False, recoverable=False, unrecoverable=False)


def main() -> None:
    args = sys.argv[1:]
    with Printer() as p:
        baseline(p)
        if args and args[0] == "--push":
            run_push(p, int(args[1]) if len(args) > 1 else 0)
        else:
            interval = float(args[0]) if args else 2.0
            max_polls = int(args[1]) if len(args) > 1 else 0
            run_poll(p, interval, max_polls)


if __name__ == "__main__":
    main()
