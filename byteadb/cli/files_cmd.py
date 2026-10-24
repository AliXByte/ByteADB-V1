import click

from byteadb.core import files as files_core
from byteadb.cli.console import console, error, ok, new_table
from byteadb.cli.resolve import resolve_device


@click.group('files')
def files_group():
    """Browse, move and transfer files on the device."""


@files_group.command('ls')
@click.argument('path', default='/sdcard')
@click.option('--serial', '-s', default=None)
def files_ls(path, serial):
    """List a directory on the device."""
    device = resolve_device(serial)
    try:
        entries = files_core.list_dir(device, path)
    except PermissionError:
        error(f"Permission denied: {path}")
        return
    except FileNotFoundError:
        error(f"No such file or directory: {path}")
        return
    table = new_table("Name", "Type", "Size", "Permissions", title=f"ByteADB · {path}")
    for e in entries:
        kind = 'dir' if e.is_dir else ('link' if e.is_link else 'file')
        table.add_row(e.name + ('/' if e.is_dir else ''), kind, files_core.human_size(e.size), e.permissions)
    console.print(table)


@files_group.command('mkdir')
@click.argument('path')
@click.option('--serial', '-s', default=None)
def files_mkdir(path, serial):
    """Create a directory (and parents) on the device."""
    device = resolve_device(serial)
    try:
        files_core.mkdir(device, path)
        ok(f"Created {path}")
    except OSError as e:
        error(str(e))


@files_group.command('rm')
@click.argument('path')
@click.option('--recursive', '-r', is_flag=True, help='Remove directories and their contents.')
@click.option('--serial', '-s', default=None)
def files_rm(path, recursive, serial):
    """Delete a file or directory on the device."""
    device = resolve_device(serial)
    try:
        files_core.remove(device, path, recursive=recursive)
        ok(f"Removed {path}")
    except OSError as e:
        error(str(e))


@files_group.command('mv')
@click.argument('src')
@click.argument('dst')
@click.option('--serial', '-s', default=None)
def files_mv(src, dst, serial):
    """Move/rename a file or directory on the device."""
    device = resolve_device(serial)
    try:
        files_core.move(device, src, dst)
        ok(f"Moved {src} -> {dst}")
    except OSError as e:
        error(str(e))


@files_group.command('push')
@click.argument('local')
@click.argument('remote')
@click.option('--serial', '-s', default=None)
def files_push(local, remote, serial):
    """Upload a local file to the device."""
    device = resolve_device(serial)
    out = files_core.push_file(device, local, remote)
    console.print(out.strip() or f"Pushed {local} -> {remote}")


@files_group.command('pull')
@click.argument('remote')
@click.argument('local')
@click.option('--serial', '-s', default=None)
def files_pull(remote, local, serial):
    """Download a file from the device."""
    device = resolve_device(serial)
    out = files_core.pull_file(device, remote, local)
    console.print(out.strip() or f"Pulled {remote} -> {local}")
