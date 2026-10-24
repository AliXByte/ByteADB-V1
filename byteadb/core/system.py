"""
ByteADB · system & debug — processes, services, bug reports, thermal,
SELinux, system properties, CPU/RAM/storage stats
"""
from __future__ import annotations

import re

from byteadb.core.adb import AdbDevice


# ── Process Management ───────────────────────────────────────────────────

def list_processes(device: AdbDevice) -> list[dict]:
    """List running processes (USER PID %CPU %MEM ARGS)."""
    out = device.shell('ps -A -o USER,PID,%CPU,%MEM,ARGS 2>/dev/null || ps', timeout=10)
    procs = []
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split(None, 4)
        if len(parts) >= 5:
            procs.append({
                'user': parts[0], 'pid': parts[1],
                'cpu': parts[2], 'mem': parts[3], 'name': parts[4],
            })
    return procs


def kill_process(device: AdbDevice, pid: str) -> str:
    """Kill a process by PID."""
    out, code = device.shell_with_exit_code(f'kill -9 {pid}')
    if code == 0:
        return f'Process {pid} killed.'
    return f'Failed (code {code}): {out.strip()}'


def kill_by_name(device: AdbDevice, name: str) -> str:
    """Kill all processes matching a name."""
    device.shell(f'am force-stop {name} 2>/dev/null')
    out, code = device.shell_with_exit_code(f'pkill -f {name} 2>/dev/null')
    return f'Kill signal sent to processes matching "{name}".'


# ── Services ─────────────────────────────────────────────────────────────

def list_services(device: AdbDevice) -> list[str]:
    """List available system services."""
    out = device.shell('service list', timeout=10)
    services = []
    for line in out.splitlines():
        m = re.match(r'\d+\s+(\S+):', line.strip())
        if m:
            services.append(m.group(1))
    return services


def service_info(device: AdbDevice, service_name: str) -> str:
    """Get info about a system service."""
    return device.shell(f'dumpsys {service_name} 2>/dev/null | head -50', timeout=10)


# ── Debug / Bug Report ───────────────────────────────────────────────────

def bugreport(device: AdbDevice, local_path: str = 'bugreport.zip') -> str:
    """Capture a full bug report (can take a minute+)."""
    from byteadb.core.adb import adb_binary
    import subprocess
    proc = subprocess.run(
        [adb_binary(), '-s', device.serial, 'bugreport', local_path],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode == 0:
        return f'Bug report saved to {local_path}'
    return f'Failed: {proc.stderr.strip()}'


def anr_traces(device: AdbDevice) -> str:
    """Read ANR traces (Application Not Responding)."""
    return device.shell('cat /data/anr/traces.txt 2>/dev/null || echo "No ANR traces found"',
                         timeout=10)


def crash_dumps(device: AdbDevice) -> str:
    """Read recent crash dumps."""
    out = device.shell('dumpsys dropbox --print 2>/dev/null | tail -100', timeout=15)
    return out or 'No crash dumps found.'


# ── CPU / RAM / Storage ─────────────────────────────────────────────────

def cpu_info(device: AdbDevice) -> dict:
    """CPU usage summary."""
    top_out = device.shell('top -bn1 -m5 2>/dev/null || dumpsys cpuinfo', timeout=10)
    cpuinfo = device.shell('cat /proc/cpuinfo | head -30', timeout=5)
    return {'top': top_out, 'cpuinfo': cpuinfo}


def memory_info(device: AdbDevice) -> dict:
    """RAM usage summary."""
    meminfo = device.shell('cat /proc/meminfo | head -10', timeout=5)
    dumpsys = device.shell('dumpsys meminfo -s 2>/dev/null | head -30', timeout=10)
    return {'meminfo': meminfo, 'dumpsys': dumpsys}


def storage_info(device: AdbDevice) -> str:
    """Disk usage summary."""
    return device.shell('df -h 2>/dev/null || df', timeout=10)


def app_memory_usage(device: AdbDevice, package: str) -> str:
    """Memory usage for a specific app."""
    return device.shell(f'dumpsys meminfo {package}', timeout=10)


# ── Thermal ──────────────────────────────────────────────────────────────

def thermal_status(device: AdbDevice) -> str:
    """Current thermal throttling status."""
    out = device.shell('dumpsys thermalservice 2>/dev/null', timeout=10)
    if not out.strip():
        out = device.shell('cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null', timeout=5)
    return out or 'Thermal info not available.'


# ── SELinux ──────────────────────────────────────────────────────────────

def selinux_status(device: AdbDevice) -> str:
    """Get current SELinux mode."""
    return device.shell('getenforce 2>/dev/null').strip() or 'Unknown'


def set_selinux(device: AdbDevice, enforcing: bool) -> str:
    """Set SELinux mode (requires root)."""
    mode = 'enforcing' if enforcing else 'permissive'
    out, code = device.shell_with_exit_code(f'setenforce {1 if enforcing else 0}')
    if code == 0:
        return f'SELinux set to {mode}.'
    return f'Failed (needs root): {out.strip()}'


# ── System Properties ────────────────────────────────────────────────────

def list_properties(device: AdbDevice, filter_key: str = '') -> list[tuple[str, str]]:
    """List all system properties, optionally filtered."""
    out = device.shell('getprop', timeout=10)
    props = []
    for m in re.finditer(r'\[(.+?)\]:\s*\[(.+?)\]', out):
        key, val = m.group(1), m.group(2)
        if not filter_key or filter_key.lower() in key.lower():
            props.append((key, val))
    return sorted(props)


def set_property(device: AdbDevice, key: str, value: str) -> str:
    """Set a system property (many are read-only without root)."""
    out, code = device.shell_with_exit_code(f"setprop '{key}' '{value}'")
    if code == 0:
        return f'Property {key} set to {value}.'
    return f'Failed: {out.strip()} (property may be read-only).'


# ── Network Stats per App ───────────────────────────────────────────────

def network_stats_per_app(device: AdbDevice, uid: str = '') -> str:
    """Network traffic stats (optionally per app UID)."""
    if uid:
        return device.shell(f'dumpsys netstats detail | grep -A5 "uid={uid}"', timeout=10)
    return device.shell('dumpsys netstats --uid 2>/dev/null | head -80', timeout=10)


def tcp_connections(device: AdbDevice) -> str:
    """Active TCP connections."""
    return device.shell('cat /proc/net/tcp 2>/dev/null | head -50', timeout=5)
