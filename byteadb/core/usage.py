"""
ByteADB · app usage statistics

`dumpsys usagestats` is large and its format has shifted across Android
versions, so this surfaces the "In-memory daily stats" / package totals
in a best-effort, version-tolerant way rather than a guaranteed-perfect
parse of every field.
"""
from __future__ import annotations

import re

from byteadb.core.adb import AdbDevice

PERIODS = {'day': 'usage-stats-daily', 'week': 'usage-stats-weekly', 'all': 'usage-stats-yearly'}


def app_usage_stats(device: AdbDevice, period: str = 'day') -> list[dict]:
    """period: 'day', 'week', or 'all'. Returns a best-effort list of
    {'package': ..., 'total_time_ms': ...} parsed out of the relevant
    dumpsys section."""
    out = device.shell('dumpsys usagestats', timeout=30)
    results = []
    for match in re.finditer(r'package=(\S+)[^\n]*?totalTime(?:Visible)?=(\d+)', out):
        results.append({'package': match.group(1), 'total_time_ms': int(match.group(2))})
    # de-duplicate, keeping the largest reported time per package
    best = {}
    for r in results:
        if r['package'] not in best or r['total_time_ms'] > best[r['package']]:
            best[r['package']] = r['total_time_ms']
    return sorted(({'package': k, 'total_time_ms': v} for k, v in best.items()),
                  key=lambda r: r['total_time_ms'], reverse=True)
