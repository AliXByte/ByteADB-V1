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


def install_split_apks(device: AdbDevice, local_apk_paths: list[str], reinstall: bool = False) -> str:
    """`adb install-multiple` for apps shipped as several split APKs
    (base + config splits), the way Play Store delivers app bundles."""
    args = ['install-multiple']
    if reinstall:
        args.append('-r')
    args.extend(local_apk_paths)
    out = device.run(*args, timeout=180)
    if 'Success' not in out:
        raise RuntimeError(out.strip() or 'split install failed')
    return out.strip()


def extract_apk(device: AdbDevice, package: str, local_dir: str) -> list[str]:
    """Pulls every APK (base + splits, if any) for an installed package
    into local_dir. Returns the local file paths written."""
    import os
    out = device.shell(f'pm path {package}')
    remote_paths = [line[len('package:'):].strip() for line in out.splitlines() if line.startswith('package:')]
    if not remote_paths:
        raise RuntimeError(f"no APK path found for '{package}' — is it installed?")
    os.makedirs(local_dir, exist_ok=True)
    local_paths = []
    for remote in remote_paths:
        name = remote.rsplit('/', 1)[-1]
        local_path = os.path.join(local_dir, name)
        device.pull(remote, local_path)
        local_paths.append(local_path)
    return local_paths


def restart(device: AdbDevice, package: str):
    force_stop(device, package)
    launch(device, package)


def suspend(device: AdbDevice, package: str):
    device.shell(f'pm suspend {package}')


def unsuspend(device: AdbDevice, package: str):
    device.shell(f'pm unsuspend {package}')


def ignore_battery_optimization(device: AdbDevice, package: str, whitelist: bool = True):
    sign = '+' if whitelist else '-'
    device.shell(f'dumpsys deviceidle whitelist {sign}{package}')


def battery_optimization_whitelist(device: AdbDevice) -> list[str]:
    out = device.shell('dumpsys deviceidle whitelist')
    pkgs = []
    for line in out.splitlines():
        line = line.strip()
        if ',' in line:
            parts = line.split(',')
            if len(parts) >= 2 and '.' in parts[1]:
                pkgs.append(parts[1])
    return pkgs


def set_default_home(device: AdbDevice, component: str):
    """component is a full ComponentInfo string, e.g.
    'com.android.launcher3/.Launcher' (see `current_home` to find it)."""
    device.shell(f'cmd package set-home-activity {component}')


def current_home(device: AdbDevice) -> str | None:
    out = device.shell('cmd package resolve-activity -a android.intent.action.MAIN '
                        '-c android.intent.category.HOME')
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('packageName='):
            return line[len('packageName='):].strip()
    return None


# ── Permissions Management ───────────────────────────────────────────────

def list_permissions(device: AdbDevice, package: str) -> dict:
    """List granted and denied runtime permissions for a package."""
    out = device.shell(f'dumpsys package {package}', timeout=15)
    granted = []
    denied = []
    in_perms = False
    for line in out.splitlines():
        line_s = line.strip()
        if 'runtime permissions:' in line_s.lower() or 'install permissions:' in line_s.lower():
            in_perms = True
            continue
        if in_perms:
            if not line_s or (not line_s.startswith('android.permission') and ':' not in line_s):
                if not line_s.startswith(' '):
                    in_perms = False
                continue
            if ': granted=true' in line_s:
                perm = line_s.split(':')[0].strip()
                granted.append(perm)
            elif ': granted=false' in line_s:
                perm = line_s.split(':')[0].strip()
                denied.append(perm)
    return {'granted': sorted(granted), 'denied': sorted(denied)}


def grant_all_permissions(device: AdbDevice, package: str) -> str:
    """Grant all runtime permissions for a package."""
    perms = list_permissions(device, package)
    count = 0
    for p in perms.get('denied', []):
        try:
            grant_permission(device, package, p)
            count += 1
        except RuntimeError:
            pass
    return f'Granted {count} permissions.'


def revoke_all_permissions(device: AdbDevice, package: str) -> str:
    """Revoke all runtime permissions for a package."""
    perms = list_permissions(device, package)
    count = 0
    for p in perms.get('granted', []):
        try:
            revoke_permission(device, package, p)
            count += 1
        except RuntimeError:
            pass
    return f'Revoked {count} permissions.'


# ── Intent Sender ────────────────────────────────────────────────────────

def send_intent(device: AdbDevice, action: str, data: str = '',
                package: str = '', component: str = '',
                extras: dict = None, intent_type: str = 'activity') -> str:
    """Send a custom intent. intent_type: 'activity', 'broadcast', 'service'."""
    cmd_map = {'activity': 'am start', 'broadcast': 'am broadcast', 'service': 'am startservice'}
    cmd = cmd_map.get(intent_type, 'am start')
    parts = [cmd, f'-a {action}']
    if data:
        parts.append(f"-d '{data}'")
    if package and component:
        parts.append(f'-n {package}/{component}')
    elif package:
        parts.append(f'-p {package}')
    if extras:
        for k, v in extras.items():
            if isinstance(v, bool):
                parts.append(f'--ez {k} {str(v).lower()}')
            elif isinstance(v, int):
                parts.append(f'--ei {k} {v}')
            else:
                parts.append(f"-es {k} '{v}'")
    full_cmd = ' '.join(parts)
    out = device.shell(full_cmd)
    return out.strip() or f'Intent sent: {action}'


# ── Deep Link Tester ─────────────────────────────────────────────────────

def open_deep_link(device: AdbDevice, uri: str) -> str:
    """Open a deep link / URI on the device."""
    out = device.shell(f"am start -a android.intent.action.VIEW -d '{uri}'")
    return out.strip() or f'Opened: {uri}'


# ── Component Enable/Disable ────────────────────────────────────────────

def set_component_enabled(device: AdbDevice, component: str, enabled: bool) -> str:
    """Enable or disable an app component (package/class)."""
    state = 'enable' if enabled else 'disable'
    out, code = device.shell_with_exit_code(f'pm {state} {component}')
    if code == 0:
        return f'Component {state}d: {component}'
    return f'Failed: {out.strip()}'


# ── App Backup ───────────────────────────────────────────────────────────

def backup_app(device: AdbDevice, package: str, local_path: str) -> str:
    """Backup an app and its data to a local .ab file."""
    from byteadb.core.adb import adb_binary
    import subprocess
    proc = subprocess.run(
        [adb_binary(), '-s', device.serial, 'backup', '-f', local_path,
         '-apk', '-obb', package],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode == 0:
        return f'Backup saved to {local_path} (confirm on device if prompted).'
    return f'Backup failed: {proc.stderr.strip()}'


def restore_backup(device: AdbDevice, local_path: str) -> str:
    """Restore from a .ab backup file."""
    from byteadb.core.adb import adb_binary
    import subprocess
    proc = subprocess.run(
        [adb_binary(), '-s', device.serial, 'restore', local_path],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode == 0:
        return f'Restore initiated (confirm on device if prompted).'
    return f'Restore failed: {proc.stderr.strip()}'


# ── App Downloads List ───────────────────────────────────────────────────

def list_downloads(device: AdbDevice) -> str:
    """List files in the Downloads folder."""
    return device.shell('ls -la /sdcard/Download/ 2>/dev/null', timeout=10)
