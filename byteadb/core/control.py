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
