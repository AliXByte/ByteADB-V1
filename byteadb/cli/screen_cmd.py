import signal
import time

import click

from byteadb.core import screen as screen_core
from byteadb.cli.console import console, error, ok
from byteadb.cli.resolve import resolve_device


@click.group('screen')
def screen_group():
    """Screenshot, screen-record and live mirroring."""


@screen_group.command('shot')
@click.argument('output', default='screenshot.png')
@click.option('--serial', '-s', default=None)
def screen_shot(output, serial):
    """Capture a screenshot and save it locally."""
    device = resolve_device(serial)
    screen_core.screenshot(device, output)
    ok(f"Saved {output}")


@screen_group.command('record')
@click.argument('output', default='recording.mp4')
@click.option('--time-limit', default=180, help='Max seconds to record (screenrecord itself caps at 180s per clip).')
@click.option('--bit-rate', default=8, help='Bit rate in Mbps.')
@click.option('--serial', '-s', default=None)
def screen_record(output, time_limit, bit_rate, serial):
    """Record the screen; stop early with Ctrl+C."""
    device = resolve_device(serial)
    console.print("[byteadb.dim]Recording — press Ctrl+C to stop early.[/]")
    proc, remote_path = screen_core.start_screenrecord(device, time_limit_sec=time_limit, bit_rate_mbps=bit_rate)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        proc.wait()
        time.sleep(1)  # screenrecord needs a moment to finalize the mp4 container
    device.pull(remote_path, output)
    device.shell(f"rm -f '{remote_path}'")
    ok(f"Saved {output}")


@screen_group.command('mirror')
@click.option('--serial', '-s', default=None)
def screen_mirror(serial):
    """Live mirror + control the device via scrcpy."""
    device = resolve_device(serial)
    try:
        proc = screen_core.mirror(device.serial)
        proc.wait()
    except RuntimeError as e:
        error(str(e))
