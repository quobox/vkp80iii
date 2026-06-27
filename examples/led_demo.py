"""Demonstrate the bezel LED bar (no paper used).

On the tested unit (ROM 7.11) the bar shows AMBER and responds to the FS B
mode commands (on / flash / off). The FS L RGB colour commands produced no
visible colour on this firmware -- they are kept in the API for other units.
"""

import time

from vkp80iii import LedFlashFreq, LedMode, Printer
from vkp80iii import commands as c


def main() -> None:
    with Printer() as p:
        print("steady on (amber)")
        p.send(c.led_bar(LedMode.ON))
        time.sleep(2)

        print("flash @ 1 Hz")
        p.led_flash(LedFlashFreq.HZ_1)
        time.sleep(4)

        print("flash @ 5 Hz")
        p.led_flash(LedFlashFreq.HZ_5)
        time.sleep(4)

        print("off")
        p.led_off()
        time.sleep(1)

        # RGB attempt -- may stay amber / off depending on firmware
        print("RGB attempt red/green/blue (may not render)")
        for rgb in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            p.led(rgb)
            time.sleep(1.5)

        print("off")
        p.led_off()
    print("done")


if __name__ == "__main__":
    main()
