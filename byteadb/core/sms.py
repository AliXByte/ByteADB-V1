"""
ByteADB · SMS for an unattended Android device you own

Built for an unattended Android-based device — nobody physically at it,
but it needs to send an alert on its own, and you need a way to
periodically check what it's sent and received without a human there to
tap anything.

`send_sms` is a true silent send via the same internal telephony call
Android itself uses — best-effort and device/Android-version dependent,
since it needs the shell user to be allowed to reach that internal API,
which varies by OEM. There's no compose/tap-to-send fallback here on
purpose: a device with no one physically present to tap "Send" gets no
benefit from one.

`sms_log` reads the sent/received messages already on *this* connected,
ADB-authorized device — i.e. your own device's own activity log, the way
you'd tail a log file on a server you run. It goes through Android's own
content-provider query interface, which a locked-down device/Android
version may deny; that's reported honestly rather than faked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from byteadb.core.adb import AdbDevice

_TYPE_NAMES = {'1': 'received', '2': 'sent', '3': 'draft', '4': 'outbox', '5': 'failed', '6': 'queued'}


@dataclass
class SmsLogEntry:
    address: Optional[str]
    body: Optional[str]
    date: Optional[str]
    direction: Optional[str]  # 'sent' / 'received' / etc., from Android's own type column


def send_sms(device: AdbDevice, number: str, text: str) -> bool:
    """Best-effort silent send via `service call isms` (the same interface
    android.telephony.SmsManager ultimately calls into). Returns True if
    the device reported success, False if this path isn't available on
    this device/Android version — there is deliberately no tap-to-send
    fallback, since an unattended device has no one to do the tapping."""
    escaped = text.replace("'", "\\'")
    out, code = device.shell_with_exit_code(
        f"service call isms 5 i32 0 s16 \"com.android.mms.service\" "
        f"s16 \"null\" s16 '{number}' s16 \"null\" s16 '{escaped}' s16 \"null\" s16 \"null\""
    )
    return code == 0 and 'error' not in out.lower()


def sms_log(device: AdbDevice) -> list[SmsLogEntry]:
    """This device's own SMS log (sent + received), newest last, the way
    `content://sms` already stores it."""
    out = device.shell("content query --uri content://sms", timeout=30)
    if 'Permission Denial' in out or 'SecurityException' in out:
        raise PermissionError("Permission denied reading content://sms on this device/Android version.")
    if 'No result found' in out or not out.strip():
        return []
    entries = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith('Row:'):
            continue
        fields = {}
        for part in line[len('Row:'):].split(', '):
            if '=' in part:
                k, _, v = part.strip().partition('=')
                fields[k] = None if v == 'NULL' else v
        entries.append(SmsLogEntry(
            address=fields.get('address'),
            body=fields.get('body'),
            date=fields.get('date'),
            direction=_TYPE_NAMES.get(fields.get('type'), fields.get('type')),
        ))
    return entries
