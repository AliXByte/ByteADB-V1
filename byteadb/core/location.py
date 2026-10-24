"""
ByteADB · last-known GPS location

There's no `content query` shortcut for location the way there is for
SMS/contacts, so this parses `dumpsys location`'s "Last Known Locations"
block — best-effort, since its exact formatting has changed across
Android versions.
"""
from __future__ import annotations

import re

from byteadb.core.adb import AdbDevice


def last_known_location(device: AdbDevice) -> dict | None:
    out = device.shell('dumpsys location', timeout=15)
    # Typical line: "    gps: Location[gps 37.422,-122.084 hAcc=5.0 et=+2h3m4s123ms]"
    match = re.search(r'(gps|network|fused|passive):\s*Location\[\S+\s+([\-\d.]+),([\-\d.]+)', out)
    if not match:
        return None
    return {
        'provider': match.group(1),
        'latitude': float(match.group(2)),
        'longitude': float(match.group(3)),
    }
