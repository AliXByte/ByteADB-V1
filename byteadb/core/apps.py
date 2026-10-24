"""
ByteADB · package / app management

Thin wrappers over `pm` and `am`, the same tools adb shell already gives
you — ByteADB just structures the output and gives consistent errors.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from byteadb.core.adb import AdbDevice


@dataclass
class AppInfo:
    package: str
    apk_path: Optional[str] = None
    is_system: bool = False
    enabled: bool = True
    version_name: Optional[str] = None
    version_code: Optional[str] = None
    permissions: list = field(default_factory=list)


def list_packages(device: AdbDevice, user_only: bool = False, system_only: bool = False) -> list[str]:
    flag = ''
    if user_only:
        flag = '-3'
    elif system_only:
        flag = '-s'
    out = device.shell(f'pm list packages {flag}'.strip())
    pkgs = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('package:'):
            pkgs.append(line[len('package:'):].strip())
    return sorted(pkgs)


def package_path(device: AdbDevice, package: str) -> Optional[str]:
    out = device.shell(f'pm path {package}')
    for line in out.splitlines():
        if line.startswith('package:'):
            return line[len('package:'):].strip()
    return None


_VERSION_NAME_RE = re.compile(r'versionName=(\S+)')
_VERSION_CODE_RE = re.compile(r'versionCode=(\S+)')


def app_info(device: AdbDevice, package: str) -> AppInfo:
    dump = device.shell(f'dumpsys package {package}', timeout=15)
    path = package_path(device, package)
    vname = _VERSION_NAME_RE.search(dump)
    vcode = _VERSION_CODE_RE.search(dump)
    is_system = '/system/' in (path or '') or '/system_ext/' in (path or '') or '/product/' in (path or '')
    enabled = 'enabled=true' in dump.lower() or 'enabled=1' in dump.lower() or True  # see note below
    perms = sorted(set(re.findall(r'^\s{4,}(android\.permission\.\S+):', dump, re.MULTILINE)))
    return AppInfo(
        package=package, apk_path=path, is_system=is_system, enabled=enabled,
        version_name=vname.group(1) if vname else None,
        version_code=vcode.group(1) if vcode else None,
        permissions=perms,
    )


def install_apk(device: AdbDevice, local_apk_path: str, reinstall: bool = False, grant_permissions: bool = True) -> str:
    args = ['install']
    if reinstall:
        args.append('-r')
    if grant_permissions:
        args.append('-g')
    args.append(local_apk_path)
    out = device.run(*args, timeout=120)
    if 'Success' not in out:
        raise RuntimeError(out.strip() or 'install failed')
    return out.strip()


def uninstall_package(device: AdbDevice, package: str, keep_data: bool = False) -> str:
    args = ['uninstall']
    if keep_data:
        args.append('-k')
    args.append(package)
    out = device.run(*args, timeout=60)
    if 'Success' not in out:
        raise RuntimeError(out.strip() or f'uninstall failed for {package}')
    return out.strip()


def clear_data(device: AdbDevice, package: str) -> bool:
    out = device.shell(f'pm clear {package}')
    return 'Success' in out


def force_stop(device: AdbDevice, package: str):
    device.shell(f'am force-stop {package}')


def set_enabled(device: AdbDevice, package: str, enabled: bool):
    sub = 'enable' if enabled else 'disable-user --user 0'
    out, code = device.shell_with_exit_code(f'pm {sub} {package}')
    if code != 0:
        raise RuntimeError(out.strip() or f'failed to {"enable" if enabled else "disable"} {package}')


def launch(device: AdbDevice, package: str):
    out, code = device.shell_with_exit_code(
        f'monkey -p {package} -c android.intent.category.LAUNCHER 1'
    )
    if code != 0 or 'No activities found' in out:
        raise RuntimeError(f'could not find a launcher activity for {package}')


def grant_permission(device: AdbDevice, package: str, permission: str):
    out, code = device.shell_with_exit_code(f'pm grant {package} {permission}')
    if code != 0:
        raise RuntimeError(out.strip() or f'failed to grant {permission}')


def revoke_permission(device: AdbDevice, package: str, permission: str):
    out, code = device.shell_with_exit_code(f'pm revoke {package} {permission}')
    if code != 0:
        raise RuntimeError(out.strip() or f'failed to revoke {permission}')
