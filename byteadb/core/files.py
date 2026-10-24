"""
ByteADB · remote file-system operations

Wraps `adb shell` listing/mkdir/rm/stat plus `adb push`/`pull` into a small,
consistent API the CLI and TUI both call. Paths are whatever the device's
shell understands (usually /sdcard/..., but also /data/local/tmp or deeper
paths on a rooted device — ByteADB doesn't restrict where you can browse,
it just honestly reports "Permission denied" when the device does).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from byteadb.core.adb import AdbDevice


@dataclass
class RemoteEntry:
    name: str
    path: str
    is_dir: bool
    is_link: bool
    size: Optional[int]
    permissions: str
    raw: str


def _parse_ls_line(line: str, parent: str) -> Optional[RemoteEntry]:
    # `ls -la` on Android's toybox: "drwxrwx--x 2 u0_a123 sdcard_rw 4096 2026-01-01 12:00 name"
    parts = line.split(None, 7)
    if len(parts) < 8:
        return None
    perms = parts[0]
    size_str = parts[4]
    name = parts[7]
    if name in ('.', '..'):
        return None
    is_link = perms.startswith('l')
    if is_link and ' -> ' in name:
        name = name.split(' -> ', 1)[0]
    is_dir = perms.startswith('d')
    try:
        size = int(size_str)
    except ValueError:
        size = None
    path = parent.rstrip('/') + '/' + name
    return RemoteEntry(name=name, path=path, is_dir=is_dir, is_link=is_link,
                        size=size, permissions=perms, raw=line)


def list_dir(device: AdbDevice, path: str) -> list[RemoteEntry]:
    out = device.shell(f"ls -la '{path}' 2>&1")
    if 'Permission denied' in out and 'total' not in out:
        raise PermissionError(f"Permission denied listing {path}")
    if 'No such file or directory' in out:
        raise FileNotFoundError(path)
    entries = []
    for line in out.splitlines():
        line = line.rstrip()
        if not line or line.startswith('total'):
            continue
        entry = _parse_ls_line(line, path)
        if entry:
            entries.append(entry)
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
    return entries


def mkdir(device: AdbDevice, path: str):
    out, code = device.shell_with_exit_code(f"mkdir -p '{path}'")
    if code != 0:
        raise OSError(out.strip() or f"failed to create {path}")


def remove(device: AdbDevice, path: str, recursive: bool = False):
    flag = '-rf' if recursive else '-f'
    out, code = device.shell_with_exit_code(f"rm {flag} '{path}'")
    if code != 0:
        raise OSError(out.strip() or f"failed to remove {path}")


def move(device: AdbDevice, src: str, dst: str):
    out, code = device.shell_with_exit_code(f"mv '{src}' '{dst}'")
    if code != 0:
        raise OSError(out.strip() or f"failed to move {src} -> {dst}")


def exists(device: AdbDevice, path: str) -> bool:
    out, code = device.shell_with_exit_code(f"[ -e '{path}' ]")
    return code == 0


def push_file(device: AdbDevice, local_path: str, remote_path: str) -> str:
    return device.push(local_path, remote_path)


def pull_file(device: AdbDevice, remote_path: str, local_path: str) -> str:
    return device.pull(remote_path, local_path)


WELL_KNOWN_PATHS = {
    'whatsapp': '/sdcard/Android/media/com.whatsapp/WhatsApp',
    'whatsapp_legacy': '/sdcard/WhatsApp',
    'screenshots': '/sdcard/Pictures/Screenshots',
    'camera': '/sdcard/DCIM/Camera',
}


def pull_dir(device: AdbDevice, remote_dir: str, local_dir: str) -> str:
    """`adb pull` is recursive for directories by default, so copying a
    whole folder category (WhatsApp media, screenshots, camera photos)
    is just a plain pull of its known path."""
    import os
    os.makedirs(local_dir, exist_ok=True)
    return device.pull(remote_dir, local_dir, timeout=600.0)


def human_size(num: Optional[int]) -> str:
    if num is None:
        return '—'
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == 'B' else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"
