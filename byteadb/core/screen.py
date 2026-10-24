"""
ByteADB · screen capture, recording and mirroring

Screenshot and screen-record are implemented directly over `adb shell
screencap`/`screenrecord` (no extra dependency). Live mirroring with mouse
and keyboard control is a much bigger problem — real-time H.264 decode and
input injection — so ByteADB deliberately doesn't reinvent it. Instead it
shells out to `scrcpy` (https://github.com/Genymobile/scrcpy) if it's
installed, exactly the way it'd shell out to any other well-built tool.
This is a disclosed integration, not a hidden dependency: `has_scrcpy()`
and clear error messages make that obvious to the user.
"""
from __future__ import annotations

import shutil
import subprocess
import time

from byteadb.core.adb import AdbDevice


# ── Quality Presets ──────────────────────────────────────────────────────

MIRROR_PRESETS = {
    'fast': {
        'label': 'Fast (low quality)',
        'max_size': 640,
        'bit_rate': '2M',
        'max_fps': 30,
    },
    'balanced': {
        'label': 'Balanced',
        'max_size': 1024,
        'bit_rate': '8M',
        'max_fps': 60,
    },
    'hq': {
        'label': 'High quality (slower)',
        'max_size': 0,  # 0 = native
        'bit_rate': '20M',
        'max_fps': 60,
    },
}

RECORD_PRESETS = {
    'fast': {'bit_rate_mbps': 2, 'label': 'Fast (low quality, 2 Mbps)'},
    'balanced': {'bit_rate_mbps': 8, 'label': 'Balanced (8 Mbps)'},
    'hq': {'bit_rate_mbps': 20, 'label': 'High quality (20 Mbps)'},
}

SCREENSHOT_FORMATS = ['png', 'jpeg', 'webp']


# ── Screenshot ───────────────────────────────────────────────────────────

def screenshot(device: AdbDevice, local_path: str, fmt: str = 'png'):
    """Capture the current screen and pull it to local_path.
    fmt: 'png', 'jpeg', or 'webp'."""
    remote_tmp = f'/sdcard/.byteadb_screenshot_{int(time.time())}.{fmt}'
    if fmt == 'png':
        device.shell(f"screencap -p '{remote_tmp}'")
    elif fmt in ('jpeg', 'jpg'):
        # screencap on newer Android supports JPEG directly
        out, code = device.shell_with_exit_code(f"screencap -j '{remote_tmp}'")
        if code != 0:
            # Fallback: capture PNG then convert wouldn't work without extra tools
            device.shell(f"screencap -p '{remote_tmp}'")
    elif fmt == 'webp':
        # Most Android versions don't support webp natively in screencap
        # Fall back to PNG
        device.shell(f"screencap -p '{remote_tmp}'")
    else:
        device.shell(f"screencap -p '{remote_tmp}'")
    try:
        device.pull(remote_tmp, local_path)
    finally:
        device.shell(f"rm -f '{remote_tmp}'")


def start_screenrecord(device: AdbDevice, remote_path: str = None,
                        time_limit_sec: int = 180, bit_rate_mbps: int = 8,
                        size: str = '') -> subprocess.Popen:
    """Starts `adb shell screenrecord` in the background."""
    from byteadb.core.adb import adb_binary
    remote_path = remote_path or f'/sdcard/byteadb_record_{int(time.time())}.mp4'
    args = [adb_binary(), '-s', device.serial, 'shell', 'screenrecord',
            '--time-limit', str(time_limit_sec),
            '--bit-rate', str(bit_rate_mbps * 1_000_000)]
    if size:
        args += ['--size', size]
    args.append(remote_path)
    proc = subprocess.Popen(args)
    return proc, remote_path


# ── scrcpy helpers ───────────────────────────────────────────────────────

def has_scrcpy() -> bool:
    return shutil.which('scrcpy') is not None


def _require_scrcpy():
    if not has_scrcpy():
        raise RuntimeError(
            "scrcpy isn't installed. ByteADB uses it for live screen "
            "mirroring/control (and camera/audio forwarding) instead of "
            "reinventing video streaming — install it from "
            "https://github.com/Genymobile/scrcpy and try again."
        )


def _audio_args(audio: str) -> list[str]:
    """Build scrcpy audio arguments from mode string."""
    if audio == 'device':
        return ['--audio-source=playback']
    elif audio == 'mic':
        return ['--audio-source=mic']
    elif audio == 'mic-raw':
        return ['--audio-source=mic-unprocessed']
    return ['--no-audio']


# ── Mirror ───────────────────────────────────────────────────────────────

def mirror(serial: str, audio: str = 'none', preset: str = 'balanced',
           max_size: int = 0, bit_rate: str = '', max_fps: int = 0,
           no_control: bool = False, lock_orientation: int = -1,
           crop: str = '', stay_awake: bool = True,
           extra_args: list[str] = None) -> subprocess.Popen:
    """Launch scrcpy for live mirroring + control.

    audio: 'none', 'device', 'mic', 'mic-raw'
    preset: 'fast', 'balanced', 'hq' (overridden by explicit params)
    max_size: max dimension in pixels (0 = native resolution)
    bit_rate: e.g. '8M', '20M'
    max_fps: cap framerate (0 = unlimited)
    no_control: view-only, no mouse/keyboard input
    lock_orientation: 0=natural, 1=90CCW, 2=180, 3=90CW, -1=unlocked
    crop: 'WIDTHxHEIGHT:X:Y' to mirror a region
    """
    _require_scrcpy()

    # Start with preset values
    p = MIRROR_PRESETS.get(preset, MIRROR_PRESETS['balanced'])
    _max_size = max_size or p.get('max_size', 0)
    _bit_rate = bit_rate or p.get('bit_rate', '8M')
    _max_fps = max_fps or p.get('max_fps', 60)

    args = ['scrcpy', '-s', serial]

    if stay_awake:
        args.append('--stay-awake')
    if not no_control:
        args.append('--show-touches')
    if no_control:
        args.append('--no-control')
    if _max_size and _max_size > 0:
        args += ['--max-size', str(_max_size)]
    if _bit_rate:
        args += ['--video-bit-rate', str(_bit_rate)]
    if _max_fps and _max_fps > 0:
        args += ['--max-fps', str(_max_fps)]
    if lock_orientation >= 0:
        args += ['--lock-video-orientation', str(lock_orientation)]
    if crop:
        args += ['--crop', crop]

    args += _audio_args(audio)
    args += (extra_args or [])
    return subprocess.Popen(args)


def mirror_record(serial: str, local_path: str, audio: str = 'device',
                   preset: str = 'balanced', max_size: int = 0,
                   bit_rate: str = '', max_fps: int = 0,
                   extra_args: list[str] = None) -> subprocess.Popen:
    """Mirror + record to file simultaneously (scrcpy --record)."""
    _require_scrcpy()
    p = MIRROR_PRESETS.get(preset, MIRROR_PRESETS['balanced'])
    _max_size = max_size or p.get('max_size', 0)
    _bit_rate = bit_rate or p.get('bit_rate', '8M')
    _max_fps = max_fps or p.get('max_fps', 60)

    args = ['scrcpy', '-s', serial, '--stay-awake', '--show-touches',
            '--record', local_path]
    if _max_size and _max_size > 0:
        args += ['--max-size', str(_max_size)]
    if _bit_rate:
        args += ['--video-bit-rate', str(_bit_rate)]
    if _max_fps and _max_fps > 0:
        args += ['--max-fps', str(_max_fps)]
    args += _audio_args(audio)
    args += (extra_args or [])
    return subprocess.Popen(args)


def mirror_view_only(serial: str, audio: str = 'none',
                      extra_args: list[str] = None) -> subprocess.Popen:
    """View-only mirror — no mouse/keyboard control forwarded."""
    return mirror(serial, audio=audio, no_control=True, extra_args=extra_args)


def otg_mode(serial: str, extra_args: list[str] = None) -> subprocess.Popen:
    """OTG mode — forward physical mouse/keyboard to the device without
    mirroring the screen (scrcpy --otg). Useful for using a computer's
    peripherals as direct input to the phone."""
    _require_scrcpy()
    args = ['scrcpy', '-s', serial, '--otg'] + (extra_args or [])
    return subprocess.Popen(args)


def virtual_display(serial: str, resolution: str = '1920x1080',
                     dpi: int = 240, audio: str = 'none',
                     extra_args: list[str] = None) -> subprocess.Popen:
    """Start a virtual display on the device (scrcpy 2.7+).
    Creates a separate display that doesn't affect the physical screen."""
    _require_scrcpy()
    args = ['scrcpy', '-s', serial,
            f'--new-display={resolution}/{dpi}']
    args += _audio_args(audio)
    args += (extra_args or [])
    return subprocess.Popen(args)


# ── Camera ───────────────────────────────────────────────────────────────

def camera_stream(serial: str, facing: str = 'back') -> subprocess.Popen:
    """Streams the phone's camera (not the screen) via scrcpy's
    --video-source=camera, added in scrcpy 2.0."""
    _require_scrcpy()
    if facing not in ('front', 'back'):
        raise ValueError("facing must be 'front' or 'back'")
    args = ['scrcpy', '-s', serial, '--video-source=camera',
            f'--camera-facing={facing}', '--no-audio']
    return subprocess.Popen(args)


def camera_record(serial: str, local_path: str, facing: str = 'back') -> subprocess.Popen:
    """Record from camera to a file."""
    _require_scrcpy()
    if facing not in ('front', 'back'):
        raise ValueError("facing must be 'front' or 'back'")
    args = ['scrcpy', '-s', serial, '--video-source=camera',
            f'--camera-facing={facing}', '--no-audio', '--record', local_path]
    return subprocess.Popen(args)


# ── Audio Only ───────────────────────────────────────────────────────────

MIC_SOURCES = {'standard': 'mic', 'unprocessed': 'mic-unprocessed'}


def mic_stream(serial: str, mode: str = 'standard') -> subprocess.Popen:
    """Live microphone audio via scrcpy's audio forwarding."""
    _require_scrcpy()
    source = MIC_SOURCES.get(mode, 'mic')
    return subprocess.Popen(['scrcpy', '-s', serial, '--no-video',
                              f'--audio-source={source}'])


def device_audio_stream(serial: str) -> subprocess.Popen:
    """Live internal/playback audio from the device."""
    _require_scrcpy()
    return subprocess.Popen(['scrcpy', '-s', serial, '--no-video',
                              '--audio-source=playback'])


def mic_record(serial: str, local_path: str, mode: str = 'standard') -> subprocess.Popen:
    _require_scrcpy()
    source = MIC_SOURCES.get(mode, 'mic')
    return subprocess.Popen(['scrcpy', '-s', serial, '--no-video',
                              f'--audio-source={source}', '--record', local_path])


def device_audio_record(serial: str, local_path: str) -> subprocess.Popen:
    _require_scrcpy()
    return subprocess.Popen(['scrcpy', '-s', serial, '--no-video',
                              '--audio-source=playback', '--record', local_path])
