"""
ByteADB · networking — Wi-Fi status, connectivity checks, hotspot, and
LAN discovery of your own ADB-enabled devices.

`discover_adb_hosts` is a plain TCP connect-scan of port 5555 (the
standard wireless-debugging port) across a subnet you supply — it exists
to make finding *your own* phone/tablet's IP on *your own* network fast,
the same thing `nmap -p 5555 192.168.1.0/24` does. It does not probe
anything else, does not fingerprint services, and connecting it to a
device you don't control and don't have permission to access is on you,
not something ByteADB assists with beyond this one honest connect check.
"""
from __future__ import annotations

import ipaddress
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from byteadb.core.adb import AdbDevice


def wifi_dump(device: AdbDevice) -> str:
    return device.shell('dumpsys wifi', timeout=20)


def wlan_ip_info(device: AdbDevice) -> dict:
    ip_out = device.shell('ip -f inet addr show wlan0 2>/dev/null')
    mac = device.shell('cat /sys/class/net/wlan0/address 2>/dev/null').strip()
    ip_addr = None
    for line in ip_out.splitlines():
        line = line.strip()
        if line.startswith('inet '):
            ip_addr = line.split()[1].split('/')[0]
    return {'ip': ip_addr, 'mac': mac or None, 'raw': ip_out.strip()}


def wifi_radio(device: AdbDevice, enable: bool):
    device.shell(f"svc wifi {'enable' if enable else 'disable'}")


def ping(device: AdbDevice, host: str, count: int = 4) -> str:
    return device.shell(f"ping -c {int(count)} {host}", timeout=count * 2 + 10)


def saved_wifi_networks(device: AdbDevice) -> str:
    out, code = device.shell_with_exit_code('cmd wifi list-networks')
    if code == 0 and out.strip():
        return out
    # Older Android fallback — best-effort grep of the full wifi dump.
    dump = device.shell('dumpsys wifi', timeout=20)
    lines = [l for l in dump.splitlines() if 'Configured networks' in l or l.strip().startswith('NetworkId')]
    return '\n'.join(lines) or out


def nearby_wifi_scan(device: AdbDevice) -> str:
    device.shell('cmd wifi start-scan')
    import time
    time.sleep(3)
    return device.shell('cmd wifi list-scan-results', timeout=15)


def nearby_wifi_scan_parsed(device: AdbDevice) -> list[dict]:
    """Scan nearby Wi-Fi networks and return parsed list of dicts with
    SSID, BSSID, frequency, RSSI, and security info."""
    import re, time
    device.shell('cmd wifi start-scan')
    time.sleep(3)
    raw = device.shell('cmd wifi list-scan-results', timeout=15)
    results = []
    seen_ssids: set[str] = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('BSSID') or line.startswith('--'):
            continue
        # Format: BSSID  frequency  RSSI  security  SSID
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        bssid = parts[0]
        if not re.match(r'[0-9a-fA-F:]{17}', bssid):
            continue
        ssid = parts[4].strip() if len(parts) >= 5 else ''
        if not ssid or ssid in seen_ssids:
            continue
        seen_ssids.add(ssid)
        try:
            rssi = int(parts[2])
        except ValueError:
            rssi = -100
        results.append({
            'ssid': ssid,
            'bssid': bssid,
            'freq': parts[1],
            'rssi': rssi,
            'security': parts[3],
        })
    # Sort by signal strength (strongest first)
    results.sort(key=lambda r: r['rssi'], reverse=True)
    return results


def hotspot(device: AdbDevice, start: bool):
    """Local-only Wi-Fi hotspot control. Command availability varies by
    Android version/OEM; `start-softap`/`stop-softap` (API 30+) is tried
    first, with the older `svc wifi tether` as a fallback."""
    if start:
        out, code = device.shell_with_exit_code('cmd wifi start-softap')
        if code != 0:
            device.shell('svc wifi tether enable')
    else:
        out, code = device.shell_with_exit_code('cmd wifi stop-softap')
        if code != 0:
            device.shell('svc wifi tether disable')


def discover_adb_hosts(subnet_cidr: str, ports: tuple = (5555, 5554), timeout: float = 0.3,
                        max_workers: int = 100) -> list[dict]:
    """Scans `subnet_cidr` (e.g. '192.168.1.0/24') for open TCP ports among
    `ports` — the standard ADB wireless-debugging ports — to help you find
    your own device's IP quickly instead of digging through router admin
    pages. Returns [{'ip': ..., 'port': ...}, ...] for whatever answered."""
    network = ipaddress.ip_network(subnet_cidr, strict=False)
    found = []

    def _check(ip: str, port: int):
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return {'ip': ip, 'port': port}
        except OSError:
            return None

    hosts = [str(h) for h in network.hosts()]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_check, ip, port) for ip in hosts for port in ports]
        for f in as_completed(futures):
            result = f.result()
            if result:
                found.append(result)
    found.sort(key=lambda r: (ipaddress.ip_address(r['ip']), r['port']))
    return found


def wifi_connect(device: AdbDevice, ssid: str, password: str = None,
                  security: str = 'wpa') -> str:
    """Connect the device to a Wi-Fi network by SSID.
    Uses `cmd wifi connect-network` (Android 11+). Falls back to
    `am start` intent on older versions (less reliable)."""
    if password:
        sec_map = {'wpa': 'wpa2', 'wpa2': 'wpa2', 'wpa3': 'wpa3', 'wep': 'wep'}
        sec = sec_map.get(security.lower(), 'wpa2')
        out, code = device.shell_with_exit_code(
            f'cmd wifi connect-network "{ssid}" {sec} "{password}"'
        )
        if code == 0:
            return out or 'Connection initiated.'
        # Fallback for older Android
        out2 = device.shell(
            f'am start -a android.settings.WIFI_SETTINGS '
            f'--es "ssid" "{ssid}" 2>&1'
        )
        return f'cmd wifi failed (code {code}): {out}\nOpened Wi-Fi settings as fallback.'
    else:
        # Open network (no password)
        out, code = device.shell_with_exit_code(
            f'cmd wifi connect-network "{ssid}" open'
        )
        if code == 0:
            return out or 'Connection initiated.'
        return f'Failed (code {code}): {out}'


# ── Port Forwarding ──────────────────────────────────────────────────────

def port_forward(device: AdbDevice, local_port: int, remote_port: int) -> str:
    """Forward a local TCP port to the device (`adb forward`)."""
    out = device.run('forward', f'tcp:{local_port}', f'tcp:{remote_port}')
    return out.strip() or f'Forwarding localhost:{local_port} → device:{remote_port}'


def port_reverse(device: AdbDevice, remote_port: int, local_port: int) -> str:
    """Reverse forward: device port → computer port (`adb reverse`)."""
    out = device.run('reverse', f'tcp:{remote_port}', f'tcp:{local_port}')
    return out.strip() or f'Reverse: device:{remote_port} → localhost:{local_port}'


def list_forwards(device: AdbDevice) -> str:
    return device.run('forward', '--list')


def remove_forwards(device: AdbDevice) -> str:
    device.run('forward', '--remove-all')
    return 'All port forwards removed.'


def list_reverses(device: AdbDevice) -> str:
    return device.run('reverse', '--list')


def remove_reverses(device: AdbDevice) -> str:
    device.run('reverse', '--remove-all')
    return 'All reverse forwards removed.'


# ── Proxy ────────────────────────────────────────────────────────────────

def set_proxy(device: AdbDevice, host: str, port: int) -> str:
    device.shell(f'settings put global http_proxy {host}:{port}')
    return f'Proxy set to {host}:{port}.'


def get_proxy(device: AdbDevice) -> str:
    return device.shell('settings get global http_proxy').strip() or 'No proxy set.'


def clear_proxy(device: AdbDevice) -> str:
    device.shell('settings put global http_proxy :0')
    return 'Proxy cleared.'


# ── DNS ──────────────────────────────────────────────────────────────────

def get_dns(device: AdbDevice) -> dict:
    private_dns = device.shell('settings get global private_dns_mode').strip()
    private_dns_host = device.shell('settings get global private_dns_specifier').strip()
    dns1 = device.get_prop('net.dns1') or ''
    dns2 = device.get_prop('net.dns2') or ''
    return {'dns1': dns1, 'dns2': dns2,
            'private_dns_mode': private_dns, 'private_dns_host': private_dns_host}


def set_private_dns(device: AdbDevice, hostname: str) -> str:
    device.shell('settings put global private_dns_mode hostname_mode')
    device.shell(f'settings put global private_dns_specifier {hostname}')
    return f'Private DNS set to {hostname}.'


def disable_private_dns(device: AdbDevice) -> str:
    device.shell('settings put global private_dns_mode off')
    return 'Private DNS disabled.'


def auto_private_dns(device: AdbDevice) -> str:
    device.shell('settings put global private_dns_mode opportunistic')
    return 'Private DNS set to automatic.'


# ── VPN ──────────────────────────────────────────────────────────────────

def vpn_status(device: AdbDevice) -> str:
    out = device.shell('dumpsys connectivity | grep -i vpn', timeout=10)
    return out.strip() or 'No active VPN detected.'


def local_subnet_guess() -> str | None:
    """Best-effort guess of 'this computer's own /24' to default the LAN
    scan's subnet field to something sane, by opening a UDP socket to a
    public address (nothing is actually sent) and reading the local
    endpoint it would have used."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        parts = ip.split('.')
        return '.'.join(parts[:3]) + '.0/24'
    except OSError:
        return None
