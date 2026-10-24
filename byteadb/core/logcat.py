"""
ByteADB · logcat streaming

`adb logcat` is long-running, so this module doesn't use the request/response
`AdbDevice.shell()` helper — it opens its own subprocess and yields lines as
they arrive, for both the CLI (prints them) and the TUI (feeds a live widget).
"""
from __future__ import annotations

import subprocess
from typing import Iterator, Optional

from byteadb.core.adb import adb_binary


def stream(serial: str, level: Optional[str] = None, tag_filter: Optional[str] = None,
           clear_first: bool = False) -> Iterator[str]:
    """Yield logcat lines as they arrive. Runs until the caller stops
    iterating (e.g. breaks out of a `for` loop) or the process ends."""
    binary = adb_binary()
    if clear_first:
        subprocess.run([binary, '-s', serial, 'logcat', '-c'], timeout=10)

    args = [binary, '-s', serial, 'logcat', '-v', 'threadtime']
    if level:
        args += ['*:' + level]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        for line in proc.stdout:
            line = line.rstrip('\n')
            if tag_filter and tag_filter.lower() not in line.lower():
                continue
            yield line
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def clear(serial: str):
    subprocess.run([adb_binary(), '-s', serial, 'logcat', '-c'], timeout=10, check=True)


LEVELS = ['V', 'D', 'I', 'W', 'E', 'F']  # Verbose, Debug, Info, Warn, Error, Fatal
