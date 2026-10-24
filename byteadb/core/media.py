"""
ByteADB · on-device media — open links, show a photo, play audio/video

All of these push nothing but what the user explicitly gave ByteADB (a
local URL/path) and open it with Android's own VIEW intent, the same
mechanism a browser or file manager uses to hand a file to an app.
"""
from __future__ import annotations

import time

from byteadb.core.adb import AdbDevice


def open_url(device: AdbDevice, url: str):
    device.shell(f"am start -a android.intent.action.VIEW -d '{url}'")


def _push_and_view(device: AdbDevice, local_path: str, mime: str) -> str:
    remote = f"/sdcard/.byteadb_media_{int(time.time())}_{local_path.rsplit('/', 1)[-1]}"
    device.push(local_path, remote)
    device.shell(f"am start -a android.intent.action.VIEW -d 'file://{remote}' -t '{mime}'")
    return remote


def display_photo(device: AdbDevice, local_path: str) -> str:
    """Pushes an image and opens it with the device's default image
    viewer. Returns the remote path, so the caller can clean it up later
    if they don't want it left on the device."""
    return _push_and_view(device, local_path, 'image/*')


def play_audio(device: AdbDevice, local_path: str) -> str:
    return _push_and_view(device, local_path, 'audio/*')


def play_video(device: AdbDevice, local_path: str) -> str:
    return _push_and_view(device, local_path, 'video/*')
