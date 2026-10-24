"""
ByteADB · wireless connection setup

Two different ways to get a phone onto Wi-Fi ADB, both real Android
features, not something ByteADB invents:

1. Wireless debugging pairing (Android 11+) — the phone shows a pairing
   IP:port and a 6-digit code under Settings > Developer options > Wireless
   debugging > Pair device with pairing code. No USB cable needed at all.

2. Classic `adb tcpip <port>` — phone is connected by USB once, ByteADB
   switches its adbd to listen on Wi-Fi too, then you can unplug. Works on
   older Android versions where there's no pairing-code screen.
"""
from __future__ import annotations

from byteadb.core import adb
from byteadb.core.adb import AdbDevice


def pair_and_connect(pairing_host_port: str, pairing_code: str, connect_host_port: str) -> str:
    """Full Android 11+ flow: pair with the code, then connect to the
    phone's normal wireless-debugging port (shown on the same screen,
    separately from the pairing port)."""
    pair_result = adb.pair(pairing_host_port, pairing_code)
    if 'Successfully paired' not in pair_result:
        raise RuntimeError(pair_result or 'pairing failed')
    connect_result = adb.connect(connect_host_port)
    if 'connected' not in connect_result.lower():
        raise RuntimeError(connect_result or 'connect failed after a successful pairing')
    return connect_result


def enable_tcpip_mode(device: AdbDevice, port: int = 5555) -> str:
    """Switch a USB-connected device's adbd into TCP/IP listening mode.
    The device must still be reachable on the same Wi-Fi network as this
    computer — ByteADB doesn't (and can't) bridge networks for you."""
    return device.run('tcpip', str(port), timeout=10)


def device_wifi_ip(device: AdbDevice) -> str | None:
    """Best-effort: read the phone's current Wi-Fi IP so the caller can
    build the connect_host_port for enable_tcpip_mode's result."""
    out = device.shell("ip -f inet addr show wlan0 2>/dev/null")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('inet '):
            return line.split()[1].split('/')[0]
    return None
