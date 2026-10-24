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


def screenshot(device: AdbDevice, local_path: str):
    """Capture the current screen as a PNG and pull it to local_path."""
    remote_tmp = f'/sdcard/.byteadb_screenshot_{int(time.time())}.png'
    device.shell(f"screencap -p '{remote_tmp}'")
    try:
        device.pull(remote_tmp, local_path)
    finally:
        device.shell(f"rm -f '{remote_tmp}'")


def start_screenrecord(device: AdbDevice, remote_path: str = None,
                        time_limit_sec: int = 180, bit_rate_mbps: int = 8) -> subprocess.Popen:
    """Starts `adb shell screenrecord` in the background (as a raw subprocess
    the caller owns) and returns the Popen handle plus the remote path used,
    so the caller can later send SIGINT-equivalent (screenrecord stops
    cleanly on Ctrl+C / process end) and then pull the file."""
    from byteadb.core.adb import adb_binary
    remote_path = remote_path or f'/sdcard/byteadb_record_{int(time.time())}.mp4'
    args = [adb_binary(), '-s', device.serial, 'shell', 'screenrecord',
            '--time-limit', str(time_limit_sec), '--bit-rate', str(bit_rate_mbps * 1_000_000),
            remote_path]
    proc = subprocess.Popen(args)
    return proc, remote_path


def has_scrcpy() -> bool:
    return shutil.which('scrcpy') is not None


def mirror(serial: str, extra_args: list[str] = None) -> subprocess.Popen:
    """Launch scrcpy for live mirroring + control. Raises RuntimeError with
    an install hint if scrcpy isn't on PATH, rather than failing silently
    or trying to fake mirroring with a screenshot-polling loop."""
    if not has_scrcpy():
        raise RuntimeError(
            "scrcpy isn't installed. ByteADB uses it for live screen "
            "mirroring/control instead of reinventing video streaming — "
            "install it from https://github.com/Genymobile/scrcpy and try again."
        )
    args = ['scrcpy', '-s', serial] + (extra_args or [])
    return subprocess.Popen(args)
