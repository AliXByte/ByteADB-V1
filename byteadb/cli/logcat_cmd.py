import click

from byteadb.core import logcat as logcat_core
from byteadb.cli.console import console, ok
from byteadb.cli.resolve import resolve_device

LEVEL_STYLE = {
    'E': 'bold red', 'F': 'bold red', 'W': 'bold yellow',
    'I': 'bold green', 'D': 'cyan', 'V': 'grey62',
}


@click.group('logcat')
def logcat_group():
    """Stream or clear the device's log buffer."""


@logcat_group.command('tail')
@click.option('--level', type=click.Choice(logcat_core.LEVELS), default=None, help='Minimum log level.')
@click.option('--tag', default=None, help='Only show lines containing this text (simple substring filter).')
@click.option('--clear', 'clear_first', is_flag=True, help='Clear the buffer before streaming.')
@click.option('--serial', '-s', default=None)
def logcat_tail(level, tag, clear_first, serial):
    """Live-stream logcat. Press Ctrl+C to stop."""
    device = resolve_device(serial)
    try:
        for line in logcat_core.stream(device.serial, level=level, tag_filter=tag, clear_first=clear_first):
            style = 'white'
            for lvl, s in LEVEL_STYLE.items():
                if f' {lvl}/' in line or f' {lvl} ' in line:
                    style = s
                    break
            console.print(line, style=style, markup=False, highlight=False)
    except KeyboardInterrupt:
        console.print("\n[byteadb.dim]stopped[/]")


@logcat_group.command('clear')
@click.option('--serial', '-s', default=None)
def logcat_clear(serial):
    """Clear the device's log buffer."""
    device = resolve_device(serial)
    logcat_core.clear(device.serial)
    ok("Log buffer cleared")
