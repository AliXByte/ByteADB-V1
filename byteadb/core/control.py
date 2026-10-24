"""
ByteADB · device control — input injection and power actions

Thin wrappers over `adb shell input` and `adb reboot`.
"""
from __future__ import annotations

from byteadb.core.adb import AdbDevice

# A curated set of the keyevents people actually reach for, named clearly
# instead of making every caller memorize Android's numeric KEYCODEs.
KEYEVENTS = {
    'home': 'KEYCODE_HOME',
    'back': 'KEYCODE_BACK',
    'recents': 'KEYCODE_APP_SWITCH',
    'power': 'KEYCODE_POWER',
    'volume_up': 'KEYCODE_VOLUME_UP',
    'volume_down': 'KEYCODE_VOLUME_DOWN',
    'mute': 'KEYCODE_VOLUME_MUTE',
    'camera': 'KEYCODE_CAMERA',
    'enter': 'KEYCODE_ENTER',
    'delete': 'KEYCODE_DEL',
    'menu': 'KEYCODE_MENU',
    'wakeup': 'KEYCODE_WAKEUP',
    'sleep': 'KEYCODE_SLEEP',
    'up': 'KEYCODE_DPAD_UP',
    'down': 'KEYCODE_DPAD_DOWN',
    'left': 'KEYCODE_DPAD_LEFT',
    'right': 'KEYCODE_DPAD_RIGHT',
    'tab': 'KEYCODE_TAB',
    'escape': 'KEYCODE_ESCAPE',
    'call': 'KEYCODE_CALL',
    'endcall': 'KEYCODE_ENDCALL',
    'notification': 'KEYCODE_NOTIFICATION',
    'settings': 'KEYCODE_SETTINGS',
    'screenshot': 'KEYCODE_SYSRQ',
}

REBOOT_MODES = [None, 'recovery', 'bootloader', 'sideload', 'sideload-auto-reboot']


def tap(device: AdbDevice, x: int, y: int):
    device.shell(f'input tap {x} {y}')


def swipe(device: AdbDevice, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    device.shell(f'input swipe {x1} {y1} {x2} {y2} {duration_ms}')


def text(device: AdbDevice, value: str):
    # Android's `input text` chokes on raw spaces; %s is its escape for one.
    escaped = value.replace(' ', '%s').replace("'", "\\'")
    device.shell(f"input text '{escaped}'")


def keyevent(device: AdbDevice, name: str):
    code = KEYEVENTS.get(name.lower())
    if not code:
        raise ValueError(f"unknown keyevent '{name}'. Known: {', '.join(sorted(KEYEVENTS))}")
    device.shell(f'input keyevent {code}')


def reboot(device: AdbDevice, mode: str = None):
    if mode not in REBOOT_MODES:
        raise ValueError(f"unknown reboot mode '{mode}'. Known: {REBOOT_MODES}")
    device.reboot(mode)


def power_off(device: AdbDevice):
    """Shuts the device down. `svc power shutdown` is the most broadly
    supported path; `reboot -p` is tried as a fallback on devices where
    the service call isn't available."""
    out, code = device.shell_with_exit_code('svc power shutdown')
    if code != 0:
        device.shell('reboot -p')


def lock(device: AdbDevice):
    """Locks the device. If the screen is currently on, one POWER keyevent
    turns it off, which locks it (assuming a lock screen is configured)."""
    keyevent(device, 'power')


def long_press(device: AdbDevice, x: int, y: int, duration_ms: int = 1000):
    """Long press at (x, y) for duration_ms."""
    device.shell(f'input swipe {x} {y} {x} {y} {duration_ms}')


def pinch(device: AdbDevice, cx: int, cy: int, start_dist: int = 200,
          end_dist: int = 50, duration_ms: int = 300):
    """Simulate a pinch gesture (zoom out). Requires Android's `input`
    to support multi-touch, which not all versions do."""
    # Best-effort: use two sequential swipes toward center
    device.shell(f'input swipe {cx - start_dist} {cy} {cx - end_dist} {cy} {duration_ms}')
    device.shell(f'input swipe {cx + start_dist} {cy} {cx + end_dist} {cy} {duration_ms}')


def spread(device: AdbDevice, cx: int, cy: int, start_dist: int = 50,
           end_dist: int = 200, duration_ms: int = 300):
    """Simulate a spread/zoom-in gesture."""
    device.shell(f'input swipe {cx - start_dist} {cy} {cx - end_dist} {cy} {duration_ms}')
    device.shell(f'input swipe {cx + start_dist} {cy} {cx + end_dist} {cy} {duration_ms}')


def open_url(device: AdbDevice, url: str):
    """Open a URL in the default browser."""
    device.shell(f"am start -a android.intent.action.VIEW -d '{url}'")


def open_settings(device: AdbDevice, section: str = '') -> str:
    """Open a specific settings page. section: e.g. 'wifi', 'bluetooth',
    'display', 'sound', 'battery', 'storage', 'apps', 'security', 'location'."""
    settings_map = {
        '': 'android.settings.SETTINGS',
        'wifi': 'android.settings.WIFI_SETTINGS',
        'bluetooth': 'android.settings.BLUETOOTH_SETTINGS',
        'display': 'android.settings.DISPLAY_SETTINGS',
        'sound': 'android.settings.SOUND_SETTINGS',
        'battery': 'android.intent.action.POWER_USAGE_SUMMARY',
        'storage': 'android.settings.INTERNAL_STORAGE_SETTINGS',
        'apps': 'android.settings.APPLICATION_SETTINGS',
        'security': 'android.settings.SECURITY_SETTINGS',
        'location': 'android.settings.LOCATION_SOURCE_SETTINGS',
        'accessibility': 'android.settings.ACCESSIBILITY_SETTINGS',
        'date': 'android.settings.DATE_SETTINGS',
        'language': 'android.settings.LOCALE_SETTINGS',
        'developer': 'android.settings.APPLICATION_DEVELOPMENT_SETTINGS',
        'about': 'android.settings.DEVICE_INFO_SETTINGS',
        'accounts': 'android.settings.SYNC_SETTINGS',
        'nfc': 'android.settings.NFC_SETTINGS',
        'hotspot': 'android.settings.TETHER_SETTINGS',
        'vpn': 'android.settings.VPN_SETTINGS',
        'data_usage': 'android.settings.DATA_USAGE_SETTINGS',
        'notifications': 'android.settings.NOTIFICATION_SETTINGS',
    }
    action = settings_map.get(section, f'android.settings.{section.upper()}_SETTINGS')
    device.shell(f'am start -a {action}')
    return f'Opened settings: {section or "main"}'


