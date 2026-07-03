"""Demonstrate presenter / ejector behaviours.

    uv run python examples/presenter.py           # eject vs retract (front, safe)
    uv run python examples/presenter.py collect   # ALSO collect mode (see warning)

* EJECT  (FS P c=0x45): after the timeout the ticket is pushed out the front.
* RETRACT(FS P c=0x52): after the timeout the ticket is pulled back inside
  (or ejected if "Paper retracting" is disabled in the printer setup).
* COLLECT (ESC C): tickets feed UNCUT to the lower/kiosk output and the batch is
  cut when the mode is disabled. On a desktop unit without a kiosk bin the paper
  just feeds out the lower path -- be ready to catch/guide it.
"""

import sys
import time

from vkp80iii import Justify, Printer


def card(p: Printer, title: str, subtitle: str) -> None:
    p.align(Justify.CENTER).char_size(2, 2).bold().textln(title).bold(False).char_size(1, 1)
    p.textln(subtitle)
    p.feed(2)


def main() -> None:
    do_collect = len(sys.argv) > 1 and sys.argv[1] == "collect"

    with Printer.for_paper(width_mm=58) as p:
        p.begin()  # layout once; don't reset again between tickets (ESC @ clears modes)

        print("1) present + EJECT  -> ticket pushed out the front after 3 s")
        card(p, "EJECT", "pushed out front")
        p.present(steps=6, blink_led=True, retract=False, timeout_s=3)
        time.sleep(6)

        print("2) present + RETRACT -> pulled back inside after 3 s")
        card(p, "RETRACT", "pulled back in")
        p.present(steps=6, blink_led=True, retract=True, timeout_s=3)
        time.sleep(6)

        if do_collect:
            print("3) COLLECT mode -> 2 tickets feed UNCUT to the lower output, then batch cut")
            p.collect_mode(True)
            for i in (1, 2):
                card(p, f"COLLECT {i}/2", "uncut, lower exit")
                time.sleep(1)
            p.collect_mode(False)  # cut the accumulated batch
    print("presenter demo done")


if __name__ == "__main__":
    main()
