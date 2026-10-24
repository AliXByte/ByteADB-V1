"""
ByteADB · lightweight, read-only root heuristics

Non-destructive checks for common signs of root access on the connected
device — build tags, common su binary paths, Magisk's package, and
ro.secure/ro.debuggable. This is a heuristic, not a certification: a
well-hidden root (Magisk hide / Zygisk) can evade some of these, and a
false positive is possible on some custom ROMs. ByteADB reports what it
found, not a verdict.
"""
from __future__ import annotations

from byteadb.core.adb import AdbDevice

SU_PATHS = [
    '/system/bin/su', '/system/xbin/su', '/sbin/su', '/su/bin/su',
    '/system/sd/xbin/su', '/system/bin/.ext/.su', '/vendor/bin/su',
]
ROOT_PACKAGES = ['com.topjohnwu.magisk', 'eu.chainfire.supersu', 'com.noshufou.android.su', 'com.koushikdutta.superuser']


def root_heuristics(device: AdbDevice) -> dict:
    findings = {}

    su_found = []
    for path in SU_PATHS:
        out, code = device.shell_with_exit_code(f"[ -e '{path}' ]")
        if code == 0:
            su_found.append(path)
    findings['su_binary_paths_found'] = su_found

    found_pkgs = []
    pkgs_out = device.shell('pm list packages', timeout=15)
    for pkg in ROOT_PACKAGES:
        if pkg in pkgs_out:
            found_pkgs.append(pkg)
    findings['root_management_apps_found'] = found_pkgs

    findings['ro_secure'] = device.get_prop('ro.secure')
    findings['ro_debuggable'] = device.get_prop('ro.debuggable')
    findings['build_tags'] = device.get_prop('ro.build.tags')  # 'test-keys' is a common root/custom-ROM signal

    which_su, code = device.shell_with_exit_code('which su')
    findings['su_on_path'] = which_su.strip() if code == 0 and which_su.strip() else None

    signals = bool(su_found) or bool(found_pkgs) or bool(findings['su_on_path']) or \
        findings['build_tags'] not in (None, '', 'release-keys')
    findings['likely_rooted'] = signals
    return findings


# ── Keystore / Certificates ─────────────────────────────────────────────

def list_certificates(device: AdbDevice) -> str:
    """List installed CA certificates."""
    out = device.shell('ls /system/etc/security/cacerts/ 2>/dev/null | head -50', timeout=10)
    user_certs = device.shell('ls /data/misc/user/0/cacerts-added/ 2>/dev/null', timeout=10)
    result = f'System certs: {len(out.splitlines())} found\n'
    if user_certs.strip():
        result += f'User-added certs: {len(user_certs.splitlines())} found'
    else:
        result += 'User-added certs: none'
    return result


def keystore_list(device: AdbDevice) -> str:
    """List keystore entries."""
    return device.shell('cmd lock_settings get-disabled 2>/dev/null', timeout=10)


# ── USB Debugging Auth ───────────────────────────────────────────────────

def revoke_usb_auth(device: AdbDevice) -> str:
    """Revoke all USB debugging authorizations."""
    device.shell('settings put global adb_wifi_enabled 0 2>/dev/null')
    return 'USB debugging authorizations revoked (may need to re-authorize).'


# ── Lock Screen ──────────────────────────────────────────────────────────

def set_lock_pin(device: AdbDevice, pin: str) -> str:
    """Set lock screen PIN."""
    out, code = device.shell_with_exit_code(f'cmd lock_settings set-pin {pin}')
    if code == 0:
        return 'Lock PIN set.'
    return f'Failed: {out.strip()}'


def clear_lock(device: AdbDevice, old_pin: str = '') -> str:
    """Clear lock screen (needs current PIN if one is set)."""
    cmd = 'cmd lock_settings clear'
    if old_pin:
        cmd += f' --old {old_pin}'
    out, code = device.shell_with_exit_code(cmd)
    if code == 0:
        return 'Lock screen cleared.'
    return f'Failed: {out.strip()}'


def set_lock_password(device: AdbDevice, password: str) -> str:
    """Set lock screen password."""
    out, code = device.shell_with_exit_code(f'cmd lock_settings set-password {password}')
    if code == 0:
        return 'Lock password set.'
    return f'Failed: {out.strip()}'
