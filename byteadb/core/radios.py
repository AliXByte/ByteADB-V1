"""
ByteADB · radio toggles and mock battery

Thin `svc`/`settings`/`dumpsys battery` wrappers for things that don't
have their own dedicated module.
"""
from __future__ import annotations

from byteadb.core.adb import AdbDevice


def mobile_data(device: AdbDevice, enable: bool):
    device.shell(f"svc data {'enable' if enable else 'disable'}")


def bluetooth_radio(device: AdbDevice, enable: bool):
    device.shell(f"svc bluetooth {'enable' if enable else 'disable'}")


def nfc_radio(device: AdbDevice, enable: bool):
    device.shell(f"svc nfc {'enable' if enable else 'disable'}")


def bluetooth_connect(device: AdbDevice, mac: str) -> str:
    """Try to connect to a Bluetooth device by MAC address.
    Uses `cmd bluetooth connect` (Android 12+). On older Android,
    tries the `am broadcast` approach. Connection may require prior
    pairing from the device's settings."""
    out, code = device.shell_with_exit_code(
        f'cmd bluetooth connect {mac}'
    )
    if code == 0 and 'error' not in out.lower():
        return out.strip() or f'Connection to {mac} initiated.'
    # Fallback: try am start to open Bluetooth settings
    device.shell(f'am start -a android.settings.BLUETOOTH_SETTINGS 2>/dev/null')
    return (f'cmd bluetooth connect failed (code {code}): {out.strip()}\n'
            f'Opened Bluetooth settings as fallback — device must be paired first.')


def bluetooth_scan_nearby(device: AdbDevice) -> list[dict]:
    """Scan for nearby discoverable Bluetooth devices.
    Uses `cmd bluetooth scan` (Android 12+) or falls back to parsing
    `dumpsys bluetooth_manager` for recently discovered devices."""
    import re, time
    # Try to trigger a scan
    device.shell('cmd bluetooth scan start 2>/dev/null')
    time.sleep(5)
    device.shell('cmd bluetooth scan stop 2>/dev/null')

    results = []
    seen: set[str] = set()

    def _add(name: str, mac: str, rssi: int = -100):
        mac = mac.upper()
        if mac not in seen:
            seen.add(mac)
            results.append({'name': name.strip() or '(unknown)', 'address': mac, 'rssi': rssi})

    # Parse dumpsys bluetooth_manager for discovered (not just bonded) devices
    out = device.shell('dumpsys bluetooth_manager', timeout=15)

    # Look for scan results / discovered devices sections
    # Format varies, try multiple patterns:

    # Pattern: "XX:XX:XX:XX:XX:XX  Name: Foo  RSSI: -55"
    for m in re.finditer(r'([0-9A-Fa-f:]{17})\s+Name:\s*(.+?)(?:\s+RSSI:\s*(-?\d+))?$',
                         out, re.MULTILINE):
        rssi = int(m.group(3)) if m.group(3) else -100
        _add(m.group(2), m.group(1), rssi)

    # Pattern: "name: Foo, addr: XX:XX:XX:XX:XX:XX" (AOSP)
    for m in re.finditer(r'name:\s*(.+?)\s*,?\s*addr(?:ess)?:\s*([0-9A-Fa-f:]{17})', out):
        _add(m.group(1), m.group(2))

    # Pattern: "XX:XX:XX:XX:XX:XX (DeviceName)"
    for m in re.finditer(r'([0-9A-Fa-f:]{17})\s*\(([^)]+)\)', out):
        _add(m.group(2), m.group(1))

    # Pattern: mName=Foo...mAddress=XX:XX or mAddress=XX:XX...mName=Foo
    for m in re.finditer(r'mName=(.+?)[\r\n].*?mAddress=([0-9A-Fa-f:]{17})', out, re.DOTALL):
        _add(m.group(1), m.group(2))
    for m in re.finditer(r'mAddress=([0-9A-Fa-f:]{17}).*?mName=(.+?)[\r\n]', out, re.DOTALL):
        _add(m.group(2), m.group(1))

    # Also try `cmd bluetooth list-devices` on newer Android
    out2 = device.shell('cmd bluetooth list-devices 2>/dev/null', timeout=10)
    for m in re.finditer(r'([0-9A-Fa-f:]{17})\s+(.+)', out2):
        _add(m.group(2), m.group(1))

    results.sort(key=lambda r: r['rssi'], reverse=True)
    return results


def airplane_mode(device: AdbDevice, enable: bool):
    device.shell(f"settings put global airplane_mode_on {1 if enable else 0}")
    device.shell(f"am broadcast -a android.intent.action.AIRPLANE_MODE --ez state {'true' if enable else 'false'}")


def mock_battery_level(device: AdbDevice, level: int):
    device.shell(f'dumpsys battery set level {max(0, min(100, int(level)))}')


def mock_battery_plugged(device: AdbDevice, plugged: bool):
    device.shell('dumpsys battery set ac 1' if plugged else 'dumpsys battery unplug')


def reset_battery_mock(device: AdbDevice):
    device.shell('dumpsys battery reset')
