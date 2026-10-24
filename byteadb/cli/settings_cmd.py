import click

from byteadb.core import settings as settings_core
from byteadb.cli.console import console, ok, new_table
from byteadb.cli.resolve import resolve_device


@click.group('settings')
def settings_group():
    """Read and write device settings (system/secure/global)."""


@settings_group.command('get')
@click.argument('namespace', type=click.Choice(settings_core.NAMESPACES))
@click.argument('key')
@click.option('--serial', '-s', default=None)
def settings_get(namespace, key, serial):
    """Get one setting's value."""
    device = resolve_device(serial)
    console.print(settings_core.get(device, namespace, key))


@settings_group.command('put')
@click.argument('namespace', type=click.Choice(settings_core.NAMESPACES))
@click.argument('key')
@click.argument('value')
@click.option('--serial', '-s', default=None)
def settings_put(namespace, key, value, serial):
    """Set one setting's value."""
    device = resolve_device(serial)
    settings_core.put(device, namespace, key, value)
    ok(f"{namespace}.{key} = {value}")


@settings_group.command('list')
@click.argument('namespace', type=click.Choice(settings_core.NAMESPACES))
@click.option('--serial', '-s', default=None)
def settings_list(namespace, serial):
    """List every key/value in a settings namespace."""
    device = resolve_device(serial)
    values = settings_core.list_all(device, namespace)
    table = new_table("Key", "Value", title=f"ByteADB · settings {namespace}")
    for k, v in sorted(values.items()):
        table.add_row(k, v)
    console.print(table)
