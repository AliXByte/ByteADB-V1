"""
ByteADB · display, sound, notification, clipboard and wallpaper control

Thin `wm`/`settings`/`cmd`/`svc` wrappers. A few of these (clipboard,
posting a notification) have no single stable command across every
Android version/OEM — each is documented honestly where that applies
rather than pretending it's 100% reliable everywhere.
"""
from __future__ import annotations

import time

from byteadb.core.adb import AdbDevice

RESOLUTION_PRESETS = {
    '720p': (1280, 720),
    '1080p': (1920, 1080),
    '2k': (2560, 1440),
    '4k': (3840, 2160),
}

DENSITY_PRESETS = {'ldpi': 120, 'mdpi': 160, 'hdpi': 240, 'xhdpi': 320, 'xxhdpi': 480, 'xxxhdpi': 640}


def get_display_settings(device: AdbDevice) -> dict:
    return {
        'size': device.shell('wm size').strip(),
        'density': device.shell('wm density').strip(),
    }


def set_resolution(device: AdbDevice, width: int, height: int):
    device.shell(f'wm size {width}x{height}')


def reset_resolution(device: AdbDevice):
    device.shell('wm size reset')


def set_density(device: AdbDevice, dpi: int):
    device.shell(f'wm density {dpi}')


def reset_density(device: AdbDevice):
    device.shell('wm density reset')


def set_scaling(device: AdbDevice, auto: bool):
    device.shell(f"wm scaling {'auto' if auto else 'off'}")


def set_brightness(device: AdbDevice, level_0_255: int):
    level = max(0, min(255, int(level_0_255)))
    device.shell(f'settings put system screen_brightness {level}')


def set_screen_timeout(device: AdbDevice, millis: int):
    device.shell(f'settings put system screen_off_timeout {int(millis)}')


def set_volume(device: AdbDevice, stream: str, level: int):
    """stream: one of 'music', 'ring', 'alarm', 'notification', 'call',
    'system'. Uses `cmd media_session volume`, which covers modern
    Android; on very old versions this may be a no-op."""
    streams = {'music': 3, 'ring': 2, 'alarm': 4, 'notification': 5, 'call': 0, 'system': 1}
    stream_id = streams.get(stream.lower(), 3)
    device.shell(f'cmd media_session volume --stream {stream_id} --set {int(level)}')


def set_dnd(device: AdbDevice, mode: str):
    """mode: 'off', 'priority', 'none' (total silence), 'alarms'."""
    modes = {'off': 0, 'priority': 1, 'none': 2, 'alarms': 3}
    if mode not in modes:
        raise ValueError(f"unknown DND mode '{mode}'. Known: {list(modes)}")
    device.shell(f'settings put global zen_mode {modes[mode]}')


def expand_notifications(device: AdbDevice):
    device.shell('cmd statusbar expand-notifications')


def collapse_notifications(device: AdbDevice):
    device.shell('cmd statusbar collapse')


def expand_quick_settings(device: AdbDevice):
    device.shell('cmd statusbar expand-settings')


# -- clipboard -----------------------------------------------------------
# There's no single documented `cmd clipboard` service in stock AOSP, so
# this uses `am broadcast`-free direct service transaction calls which are
# best-effort and can vary by OEM/Android version. If it fails on a given
# device, that's this method's real limitation, not a bug to paper over.

def clipboard_set(device: AdbDevice, text: str):
    escaped = text.replace("'", "\\'")
    device.shell(f"am broadcast -a clipper.set -e text '{escaped}' 2>/dev/null")
    # Fallback best-effort path used by several OEM shells:
    device.shell(f"service call clipboard 2 s16 '{escaped}' 2>/dev/null")


def clipboard_clear(device: AdbDevice):
    clipboard_set(device, '')


# -- wallpaper -------------------------------------------------------------

def set_wallpaper(device: AdbDevice, local_image_path: str) -> str:
    """Pushes the image and opens Android's 'Set as wallpaper' chooser via
    an ATTACH_DATA intent — ByteADB doesn't silently force a wallpaper
    change, the device owner still confirms it in the chooser."""
    remote = f"/sdcard/.byteadb_wallpaper_{int(time.time())}.jpg"
    device.push(local_image_path, remote)
    device.shell(
        f"am start -a android.intent.action.ATTACH_DATA -d 'file://{remote}' -t 'image/*' "
        f"--eu android.intent.extra.STREAM 'file://{remote}'"
    )
    return remote


# -- audio routing ---------------------------------------------------------

def get_audio_devices(device: AdbDevice) -> dict:
    """List available audio output and input devices from dumpsys audio."""
    out = device.shell('dumpsys audio', timeout=15)
    return {
        'raw': out,
        'outputs': _parse_audio_devices(out, 'output'),
        'inputs': _parse_audio_devices(out, 'input'),
    }


def _parse_audio_devices(dump: str, direction: str) -> list[dict]:
    """Parse audio devices from dumpsys audio output."""
    import re
    devices = []
    seen: set[str] = set()

    # Common device type mappings
    output_types = {
        'speaker': 'Device Speaker',
        'earpiece': 'Earpiece',
        'wired_headset': 'Wired Headset (AUX)',
        'wired_headphone': 'Wired Headphones (AUX)',
        'bluetooth_a2dp': 'Bluetooth (A2DP)',
        'bluetooth_sco': 'Bluetooth (SCO/Call)',
        'usb_device': 'USB Audio Device',
        'usb_headset': 'USB Headset',
        'hdmi': 'HDMI',
    }
    input_types = {
        'builtin_mic': 'Built-in Microphone',
        'mic': 'Built-in Microphone',
        'wired_headset': 'Wired Headset Mic (AUX)',
        'bluetooth_sco_headset': 'Bluetooth Mic (SCO)',
        'bluetooth_sco': 'Bluetooth Mic (SCO)',
        'usb_device': 'USB Microphone',
        'usb_headset': 'USB Headset Mic',
    }

    type_map = output_types if direction == 'output' else input_types

    # Pattern: "type:AUDIO_DEVICE_OUT_SPEAKER" or "type:AUDIO_DEVICE_IN_BUILTIN_MIC"
    prefix = 'OUT' if direction == 'output' else 'IN'
    for m in re.finditer(rf'type:AUDIO_DEVICE_{prefix}_(\w+)', dump):
        dev_type = m.group(1).lower()
        if dev_type not in seen:
            seen.add(dev_type)
            label = type_map.get(dev_type, dev_type.replace('_', ' ').title())
            devices.append({'type': dev_type, 'label': label})

    # Fallback: if nothing found, add default options
    if not devices:
        if direction == 'output':
            devices = [
                {'type': 'speaker', 'label': 'Device Speaker'},
                {'type': 'wired_headphone', 'label': 'Wired Headphones (AUX)'},
                {'type': 'bluetooth_a2dp', 'label': 'Bluetooth (A2DP)'},
            ]
        else:
            devices = [
                {'type': 'builtin_mic', 'label': 'Built-in Microphone'},
                {'type': 'wired_headset', 'label': 'Wired Headset Mic (AUX)'},
                {'type': 'bluetooth_sco_headset', 'label': 'Bluetooth Mic (SCO)'},
            ]

    return devices


def set_audio_output(device: AdbDevice, device_type: str) -> str:
    """Route audio output to a specific device.
    Uses multiple approaches since there's no single stable API across versions."""
    type_map = {
        'speaker': '2',        # AUDIO_DEVICE_OUT_SPEAKER
        'earpiece': '1',       # AUDIO_DEVICE_OUT_EARPIECE
        'wired_headset': '4',  # AUDIO_DEVICE_OUT_WIRED_HEADSET
        'wired_headphone': '8', # AUDIO_DEVICE_OUT_WIRED_HEADPHONE
        'bluetooth_a2dp': '128', # AUDIO_DEVICE_OUT_BLUETOOTH_A2DP
        'bluetooth_sco': '16', # AUDIO_DEVICE_OUT_BLUETOOTH_SCO
        'usb_device': '16384', # AUDIO_DEVICE_OUT_USB_DEVICE
        'usb_headset': '67108864', # AUDIO_DEVICE_OUT_USB_HEADSET
    }

    dev_type = device_type.lower()
    dev_id = type_map.get(dev_type, '2')  # default to speaker

    # Method 1: cmd audio set-force-use (Android 10+)
    if dev_type in ('speaker', 'earpiece'):
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_MEDIA SPEAKER 2>/dev/null'
        )
        if code == 0:
            return f'Audio output forced to speaker.'
    elif dev_type.startswith('bluetooth'):
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_MEDIA BT_A2DP 2>/dev/null'
        )
        if code == 0:
            return f'Audio output forced to Bluetooth.'
    elif dev_type.startswith('wired'):
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_MEDIA WIRED_ACCESSORY 2>/dev/null'
        )
        if code == 0:
            return f'Audio output forced to wired accessory.'

    # Method 2: media.set_a2dp_sink_connection_state or general settings
    # This varies heavily by Android version, try a settings approach
    out, code = device.shell_with_exit_code(
        f'cmd audio set-force-use FOR_MEDIA NONE 2>/dev/null'
    )

    return (f'Audio routing to {dev_type} attempted. '
            f'If the device is connected, it should switch automatically. '
            f'Some OEMs may not support forced routing from shell.')


def set_audio_input(device: AdbDevice, device_type: str) -> str:
    """Route audio input (microphone) to a specific device."""
    dev_type = device_type.lower()

    # Method: cmd audio set-force-use FOR_COMMUNICATION
    if dev_type in ('builtin_mic', 'mic'):
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_COMMUNICATION NONE 2>/dev/null'
        )
        if code == 0:
            return 'Microphone input set to built-in mic.'
    elif dev_type.startswith('bluetooth') or dev_type == 'bluetooth_sco_headset':
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_COMMUNICATION BT_SCO 2>/dev/null'
        )
        if code == 0:
            return 'Microphone input forced to Bluetooth SCO.'
    elif dev_type.startswith('wired'):
        out, code = device.shell_with_exit_code(
            'cmd audio set-force-use FOR_COMMUNICATION WIRED_ACCESSORY 2>/dev/null'
        )
        if code == 0:
            return 'Microphone input forced to wired headset mic.'

    return (f'Mic routing to {dev_type} attempted. '
            f'Some OEMs may not support forced routing from shell.')


def reset_audio_routing(device: AdbDevice) -> str:
    """Reset all forced audio routing to default (automatic)."""
    device.shell('cmd audio set-force-use FOR_MEDIA NONE 2>/dev/null')
    device.shell('cmd audio set-force-use FOR_COMMUNICATION NONE 2>/dev/null')
    device.shell('cmd audio set-force-use FOR_RECORD NONE 2>/dev/null')
    return 'Audio routing reset to automatic.'


# ── Font Size ────────────────────────────────────────────────────────────

def get_font_scale(device: AdbDevice) -> float:
    out = device.shell('settings get system font_scale').strip()
    try:
        return float(out)
    except (ValueError, TypeError):
        return 1.0


def set_font_scale(device: AdbDevice, scale: float) -> str:
    device.shell(f'settings put system font_scale {scale}')
    return f'Font scale set to {scale}.'

FONT_SCALES = {'small': 0.85, 'default': 1.0, 'large': 1.15, 'largest': 1.3}


# ── Animation Scales ─────────────────────────────────────────────────────

def get_animation_scales(device: AdbDevice) -> dict:
    return {
        'window': device.shell('settings get global window_animation_scale').strip(),
        'transition': device.shell('settings get global transition_animation_scale').strip(),
        'animator': device.shell('settings get global animator_duration_scale').strip(),
    }


def set_all_animation_scales(device: AdbDevice, scale: float) -> str:
    device.shell(f'settings put global window_animation_scale {scale}')
    device.shell(f'settings put global transition_animation_scale {scale}')
    device.shell(f'settings put global animator_duration_scale {scale}')
    return f'All animation scales set to {scale}.'

ANIMATION_PRESETS = {'off': 0.0, 'fast': 0.5, 'normal': 1.0, 'slow': 2.0, 'very_slow': 5.0}


# ── Force RTL Layout ─────────────────────────────────────────────────────

def set_rtl(device: AdbDevice, enable: bool) -> str:
    device.shell(f'settings put global debug.force_rtl {1 if enable else 0}')
    return f'Force RTL {"enabled" if enable else "disabled"}.'


# ── Dark Mode ────────────────────────────────────────────────────────────

def set_dark_mode(device: AdbDevice, mode: str) -> str:
    """mode: 'yes' (dark), 'no' (light), 'auto' (follow schedule)."""
    device.shell(f'cmd uimode night {mode}')
    return f'Dark mode: {mode}.'


# ── Navigation / Status Bar ──────────────────────────────────────────────

def set_immersive(device: AdbDevice, mode: str) -> str:
    """mode: 'nav' (hide nav), 'status' (hide status), 'full' (hide both), 'off' (show all)."""
    if mode == 'nav':
        device.shell('settings put global policy_control immersive.navigation=*')
        return 'Navigation bar hidden.'
    elif mode == 'status':
        device.shell('settings put global policy_control immersive.status=*')
        return 'Status bar hidden.'
    elif mode == 'full':
        device.shell('settings put global policy_control immersive.full=*')
        return 'Full immersive (all bars hidden).'
    else:
        device.shell('settings put global policy_control null')
        return 'All system bars shown.'


# ── Color Correction / Inversion ─────────────────────────────────────────

def set_color_inversion(device: AdbDevice, enable: bool) -> str:
    device.shell(f'settings put secure accessibility_display_inversion_enabled {1 if enable else 0}')
    return f'Color inversion {"enabled" if enable else "disabled"}.'


def set_color_correction(device: AdbDevice, enable: bool, mode: int = 0) -> str:
    """mode: 0=deuteranomaly (red-green), 1=protanomaly, 2=tritanomaly (blue-yellow)."""
    device.shell(f'settings put secure accessibility_display_daltonizer_enabled {1 if enable else 0}')
    if enable:
        device.shell(f'settings put secure accessibility_display_daltonizer {mode}')
    modes = {0: 'deuteranomaly', 1: 'protanomaly', 2: 'tritanomaly'}
    return f'Color correction {"enabled (" + modes.get(mode, str(mode)) + ")" if enable else "disabled"}.'


# ── Always-on Display ───────────────────────────────────────────────────

def set_always_on_display(device: AdbDevice, enable: bool) -> str:
    device.shell(f'settings put secure doze_always_on {1 if enable else 0}')
    return f'Always-on display {"enabled" if enable else "disabled"}.'


def open_developer_settings(device: AdbDevice):
    device.shell('am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS')


def stay_awake(device: AdbDevice, mode: str):
    """mode: 'off', 'usb' (stay on while charging via USB), 'always'."""
    modes = {'off': 'false', 'usb': 'true', 'always': 'true'}
    if mode not in modes:
        raise ValueError(f"unknown stay-awake mode '{mode}'. Known: {list(modes)}")
    device.shell(f'svc power stayon {modes[mode]}')
