import subprocess

import click

from byteadb.core.adb import adb_binary
from byteadb.cli.console import console
from byteadb.cli.resolve import resolve_device


@click.command('shell')
@click.argument('command', required=False, default=None)
@click.option('--serial', '-s', default=None)
def shell_cmd(command, serial):
    """Run one shell command, or open an interactive shell with no arguments."""
    device = resolve_device(serial)
    if command:
        out = device.shell(command, timeout=30)
        console.print(out, end='')
        return

    console.print(f"[byteadb.dim]Interactive shell on {device.serial} — Ctrl+D or 'exit' to leave.[/]")
    subprocess.run([adb_binary(), '-s', device.serial, 'shell'])
