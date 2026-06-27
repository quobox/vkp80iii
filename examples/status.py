"""Human-friendly readout of everything the VKP80III can report (no paper used).

uv run python examples/status.py
"""

from vkp80iii import Printer
from vkp80iii.exceptions import StatusTimeout

MODELS = {b"\x02\x05": "VKP80III"}


def yn(v: bool) -> str:
    return "ja" if v else "nein"


def ok(bad: bool) -> str:
    return "FEHLER" if bad else "OK"


def line(label: str, value: str) -> None:
    print(f"  {label:<28}: {value}")


def main() -> None:
    with Printer() as p:
        try:
            dev = p.device_id()
            rom = p.rom_version()
        except StatusTimeout:
            print("Keine Antwort vom Gerät – ist es an und das Kabel bidirektional?")
            return

        print("=" * 44)
        print("  VKP80III – Gerätestatus & Infos")
        print("=" * 44)

        print("\nGERÄT")
        line("Modell-ID", f"{dev.hex(' ')}  ({MODELS.get(bytes(dev), 'unbekannt')})")
        line("ROM-Version", rom)
        line("Schnittstelle", "USB (/dev/usb/lp0)")

        st = p.status()
        print("\nBEREIT ZUM DRUCKEN?  ->  " + ("JA ✓" if st.ready else "NEIN ✗"))
        if st.problems():
            line("  Hinweise", ", ".join(st.problems()))

        print("\nPAPIER")
        line("Papier eingelegt", yn(st.paper_present))
        line("Papier fast leer", yn(st.low_paper))
        line("Virtuelles Papierende erreicht", yn(st.virtual_paper_end))
        line("Ticket im Ausgabefach", yn(st.ticket_in_output))
        line("Black-Mark über Sensor", yn(st.black_mark_over_sensor))

        print("\nDECKEL / TASTEN / MECHANIK")
        line("Deckel offen", yn(st.cover_open))
        line("Druckkopf angehoben", yn(st.head_up))
        line("Autocutter-Deckel offen", yn(st.cutter_cover_open))
        line("Spooling aktiv", yn(st.spooling))
        line("Papiermotor läuft", yn(st.drag_motor_on))
        line("LINE-FEED-Taste gedrückt", yn(st.lf_key_pressed))
        line("FORM-FEED-Taste gedrückt", yn(st.ff_key_pressed))

        print("\nFEHLER (behebbar)")
        line("Kopftemperatur", ok(st.head_temperature_error))
        line("RS232-Kommunikation", ok(st.comm_error))
        line("Stromversorgung", ok(st.power_supply_error))
        line("Befehl quittiert", "OK" if not st.command_not_acknowledged else "NICHT quittiert")
        line("Papierstau", "JA" if st.paper_jam else "nein")
        line("Black-Mark-Suche", ok(st.black_mark_error))

        print("\nFEHLER (schwerwiegend)")
        line("Autocutter", ok(st.cutter_error))
        line("RAM", ok(st.ram_error))
        line("EEPROM", ok(st.eeprom_error))
        line("Emitter (Presenter)", ok(st.emitter_error))

        print("\nWARTUNGSZÄHLER")
        try:
            cm = p.paper_remaining_cm()
            line("Papier übrig (bis Virt.-Ende)", f"{cm} cm  ({cm / 100:.1f} m)")
            line("Schnitte gesamt", str(p.cut_count()))
            pl = p.printed_length_cm()
            line("Gedruckt gesamt", f"{pl} cm  ({pl / 100:.1f} m)")
            line("Retracts (Papier-Einzüge)", str(p.retract_count()))
            line("Einschaltungen", str(p.powerup_count()))
        except StatusTimeout:
            line("Zähler", "(keine Antwort)")
        print()


if __name__ == "__main__":
    main()
