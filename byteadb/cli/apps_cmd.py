import click

from byteadb.core import apps as apps_core
from byteadb.cli.console import console, error, ok, new_table
from byteadb.cli.resolve import resolve_device


@click.group('apps')
def apps_group():
    """Install, inspect and manage apps on the device."""


@apps_group.command('list')
@click.option('--user-only', is_flag=True, help='Only show user-installed apps.')
@click.option('--system-only', is_flag=True, help='Only show system apps.')
@click.option('--serial', '-s', default=None)
def apps_list(user_only, system_only, serial):
    """List installed packages."""
    device = resolve_device(serial)
    pkgs = apps_core.list_packages(device, user_only=user_only, system_only=system_only)
    table = new_table("Package", title=f"ByteADB · {len(pkgs)} package(s)")
    for p in pkgs:
        table.add_row(p)
    console.print(table)


@apps_group.command('info')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_info(package, serial):
    """Show version, APK path and granted permissions for one app."""
    device = resolve_device(serial)
    info = apps_core.app_info(device, package)
    console.print(f"[byteadb.key]Package:[/]  {info.package}")
    console.print(f"[byteadb.key]Version:[/]  {info.version_name or '—'} ({info.version_code or '—'})")
    console.print(f"[byteadb.key]APK:[/]      {info.apk_path or '—'}")
    console.print(f"[byteadb.key]System app:[/] {info.is_system}")
    if info.permissions:
        table = new_table("Permission", title="Declared permissions")
        for p in info.permissions:
            table.add_row(p)
        console.print(table)


@apps_group.command('install')
@click.argument('apk_path')
@click.option('--reinstall', '-r', is_flag=True)
@click.option('--serial', '-s', default=None)
def apps_install(apk_path, reinstall, serial):
    """Install a local APK."""
    device = resolve_device(serial)
    try:
        apps_core.install_apk(device, apk_path, reinstall=reinstall)
        ok(f"Installed {apk_path}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('uninstall')
@click.argument('package')
@click.option('--keep-data', is_flag=True)
@click.option('--serial', '-s', default=None)
def apps_uninstall(package, keep_data, serial):
    """Uninstall a package."""
    device = resolve_device(serial)
    try:
        apps_core.uninstall_package(device, package, keep_data=keep_data)
        ok(f"Uninstalled {package}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('clear')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_clear(package, serial):
    """Clear an app's data and cache."""
    device = resolve_device(serial)
    if apps_core.clear_data(device, package):
        ok(f"Cleared data for {package}")
    else:
        error(f"Failed to clear data for {package}")


@apps_group.command('force-stop')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_force_stop(package, serial):
    """Force-stop a running app."""
    device = resolve_device(serial)
    apps_core.force_stop(device, package)
    ok(f"Force-stopped {package}")


@apps_group.command('enable')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_enable(package, serial):
    """Re-enable a disabled app."""
    device = resolve_device(serial)
    try:
        apps_core.set_enabled(device, package, True)
        ok(f"Enabled {package}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('disable')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_disable(package, serial):
    """Disable an app for the current user."""
    device = resolve_device(serial)
    try:
        apps_core.set_enabled(device, package, False)
        ok(f"Disabled {package}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('launch')
@click.argument('package')
@click.option('--serial', '-s', default=None)
def apps_launch(package, serial):
    """Launch an app's main activity."""
    device = resolve_device(serial)
    try:
        apps_core.launch(device, package)
        ok(f"Launched {package}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('grant')
@click.argument('package')
@click.argument('permission')
@click.option('--serial', '-s', default=None)
def apps_grant(package, permission, serial):
    """Grant a runtime permission to an app."""
    device = resolve_device(serial)
    try:
        apps_core.grant_permission(device, package, permission)
        ok(f"Granted {permission} to {package}")
    except RuntimeError as e:
        error(str(e))


@apps_group.command('revoke')
@click.argument('package')
@click.argument('permission')
@click.option('--serial', '-s', default=None)
def apps_revoke(package, permission, serial):
    """Revoke a runtime permission from an app."""
    device = resolve_device(serial)
    try:
        apps_core.revoke_permission(device, package, permission)
        ok(f"Revoked {permission} from {package}")
    except RuntimeError as e:
        error(str(e))
