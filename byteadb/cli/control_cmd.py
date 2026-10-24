import click

from byteadb.core import control as control_core
from byteadb.cli.console import ok, error
from byteadb.cli.resolve import resolve_device


@click.group('control')
def control_group():
    """Simulate input: taps, swipes, text and key presses."""


@control_group.command('tap')
@click.argument('x', type=int)
@click.argument('y', type=int)
@click.option('--serial', '-s', default=None)
def control_tap(x, y, serial):
    """Tap a screen coordinate."""
    device = resolve_device(serial)
    control_core.tap(device, x, y)
    ok(f"Tapped ({x}, {y})")


@control_group.command('swipe')
@click.argument('x1', type=int)
@click.argument('y1', type=int)
@click.argument('x2', type=int)
@click.argument('y2', type=int)
@click.option('--duration', default=300, help='Swipe duration in ms.')
@click.option('--serial', '-s', default=None)
def control_swipe(x1, y1, x2, y2, duration, serial):
    """Swipe from one coordinate to another."""
    device = resolve_device(serial)
    control_core.swipe(device, x1, y1, x2, y2, duration)
    ok(f"Swiped ({x1},{y1}) -> ({x2},{y2})")


@control_group.command('text')
@click.argument('value')
@click.option('--serial', '-s', default=None)
def control_text(value, serial):
    """Type text into the currently focused field."""
    device = resolve_device(serial)
    control_core.text(device, value)
    ok("Text sent")


@control_group.command('key')
@click.argument('name')
@click.option('--serial', '-s', default=None)
def control_key(name, serial):
    """Send a named keyevent (home, back, power, volume_up, ...)."""
    device = resolve_device(serial)
    try:
        control_core.keyevent(device, name)
        ok(f"Sent keyevent '{name}'")
    except ValueError as e:
        error(str(e))


@control_group.command('reboot')
@click.option('--mode', type=click.Choice(['normal', 'recovery', 'bootloader', 'sideload']), default='normal')
@click.option('--serial', '-s', default=None)
def control_reboot(mode, serial):
    """Reboot the device (normal or into recovery/bootloader/sideload)."""
    device = resolve_device(serial)
    control_core.reboot(device, None if mode == 'normal' else mode)
    ok(f"Rebooting ({mode})")
