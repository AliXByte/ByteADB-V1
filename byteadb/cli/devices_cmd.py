import click

from byteadb.core import adb
from byteadb.core.adb import AdbDevice, AdbError
from byteadb.cli.console import console, error, new_table, ok
from byteadb.cli.resolve import resolve_device


@click.group('devices')
def devices_group():
    """List and inspect attached/paired devices."""


@devices_group.command('list')
def devices_list():
    """Show every device adb currently knows about."""
    devices = adb.list_devices()
    if not devices:
        console.print("[byteadb.dim]No devices attached.[/]")
        return
    table = new_table("Serial", "State", "Model", "Transport", title="ByteADB · devices")
    for d in devices:
        state_style = {"device": "byteadb.ok", "unauthorized": "byteadb.warn"}.get(d.state, "byteadb.err")
        table.add_row(d.serial, f"[{state_style}]{d.state}[/]", d.model or '—', d.transport or '—')
    console.print(table)


@devices_group.command('info')
@click.option('--serial', '-s', default=None, help='Target device serial (auto-selected if only one is attached).')
def devices_info(serial):
    """Show model, Android version, battery and more for one device."""
    device = resolve_device(serial)
    info = device.info()
    table = new_table("Field", "Value", title=f"ByteADB · {device.serial}")
    labels = {
        'model': 'Model', 'manufacturer': 'Manufacturer', 'android_version': 'Android version',
        'sdk': 'SDK level', 'build_id': 'Build', 'abi': 'CPU ABI', 'serialno': 'Serial',
        'battery_level': 'Battery level (%)', 'battery_status': 'Battery status',
    }
    for key, label in labels.items():
        if key in info:
            table.add_row(label, str(info[key]) if info[key] is not None else '—')
    console.print(table)


@devices_group.command('reboot')
@click.option('--serial', '-s', default=None)
@click.option('--mode', type=click.Choice(['normal', 'recovery', 'bootloader', 'sideload']), default='normal')
def devices_reboot(serial, mode):
    """Reboot a device, optionally into recovery/bootloader/sideload."""
    device = resolve_device(serial)
    try:
        device.reboot(None if mode == 'normal' else mode)
        ok(f"Rebooting {device.serial} ({mode})")
    except AdbError as e:
        error(str(e))
