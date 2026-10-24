"""
ByteADB · CLI device resolution

Every subcommand that touches a device needs the same logic: if the user
passed --serial, use it; otherwise, if exactly one device is attached, use
that one; otherwise, stop and show the list so they can pick explicitly.
Centralizing this means every command fails the same clear way instead of
each reinventing (or forgetting) this check.
"""
import sys

from byteadb.core import adb
from byteadb.core.adb import AdbDevice, AdbNotFoundError
from byteadb.cli.console import error, new_table, console


def resolve_device(serial: str = None) -> AdbDevice:
    try:
        devices = adb.list_devices()
    except AdbNotFoundError as e:
        error(str(e))
        sys.exit(1)

    if serial:
        match = next((d for d in devices if d.serial == serial), None)
        if not match:
            error(f"No attached device with serial '{serial}'. Run `byteadb devices` to see what's connected.")
            sys.exit(1)
        if match.state != 'device':
            error(f"Device '{serial}' is in state '{match.state}', not ready. "
                  f"{'Check the phone screen for an authorization prompt.' if match.state == 'unauthorized' else ''}")
            sys.exit(1)
        return AdbDevice(serial)

    ready = [d for d in devices if d.state == 'device']
    if len(ready) == 1:
        return AdbDevice(ready[0].serial)

    if not devices:
        error("No devices found. Plug one in with USB debugging enabled, "
              "or pair one wirelessly with `byteadb wireless pair`.")
    elif not ready:
        error("Device(s) found but none are ready (unauthorized/offline). "
              "Check the phone screen for an authorization prompt.")
        _print_devices(devices)
    else:
        error("Multiple devices attached — pass --serial to pick one:")
        _print_devices(devices)
    sys.exit(1)


def _print_devices(devices):
    table = new_table("Serial", "State", "Model", "Transport")
    for d in devices:
        table.add_row(d.serial, d.state, d.model or '—', d.transport or '—')
    console.print(table)
