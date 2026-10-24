"""
ByteADB · core ADB process wrapper

Every other module (files, apps, shell, logcat, screen, control, settings,
wireless) is built on top of `AdbDevice` here. Nothing in ByteADB talks to
a phone except through the real `adb` binary — this is intentionally a thin,
defensive wrapper, not a reimplementation of the ADB protocol.

Design notes:
- Every call goes through `_run`, which always sets a timeout, always
  captures stdout/stderr separately, and raises a single `AdbError` with
  the real command and real stderr attached — so a caller (CLI or TUI)
  can show the user what actually happened instead of a bare traceback.
- `AdbDevice` binds every subsequent call to one serial (`-s <serial>`),
  so a multi-device session can never accidentally run a destructive
  command against the wrong phone.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


class AdbNotFoundError(RuntimeError):
    """Raised once, early, if the `adb` binary isn't on PATH."""


class AdbError(RuntimeError):
    """A non-zero exit from `adb`, carrying the exact command and stderr
    so the UI layer can show a precise, actionable error instead of a
    bare 'something went wrong'."""

    def __init__(self, command: list[str], returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr.strip()
        super().__init__(
            f"`{' '.join(command)}` exited {returncode}: {self.stderr or '(no stderr)'}"
        )


def adb_binary() -> str:
    path = shutil.which('adb')
    if not path:
        raise AdbNotFoundError(
            "adb was not found on PATH. Install Android Platform Tools and "
            "make sure the `adb` binary is on your PATH, then try again."
        )
    return path


def _run(args: list[str], timeout: Optional[float] = 20.0, input_bytes: bytes = None) -> subprocess.CompletedProcess:
    cmd = [adb_binary()] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            input=input_bytes,
        )
    except subprocess.TimeoutExpired as e:
        raise AdbError(cmd, -1, f"timed out after {timeout}s") from e
    if proc.returncode != 0:
        raise AdbError(cmd, proc.returncode, proc.stderr.decode('utf-8', 'replace'))
    return proc


@dataclass
class Device:
    serial: str
    state: str                 # device / unauthorized / offline
    model: Optional[str] = None
    transport: Optional[str] = None  # usb / tcp (wireless)

    @property
    def is_wireless(self) -> bool:
        return ':' in self.serial  # wireless serials look like ip:port


def list_devices() -> list[Device]:
    """`adb devices -l`, parsed into Device objects. Does not raise if no
    devices are attached — an empty list is a normal, expected result."""
    proc = _run(['devices', '-l'])
    out = proc.stdout.decode('utf-8', 'replace')
    devices = []
    for line in out.splitlines()[1:]:  # skip "List of devices attached"
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial, state = parts[0], parts[1]
        model = None
        for p in parts[2:]:
            if p.startswith('model:'):
                model = p.split(':', 1)[1]
        transport = 'tcp' if ':' in serial else 'usb'
        devices.append(Device(serial=serial, state=state, model=model, transport=transport))
    return devices


def start_server():
    _run(['start-server'])


def kill_server():
    _run(['kill-server'])


def restart_server():
    kill_server()
    start_server()


def forward(serial: str, local: str, remote: str) -> str:
    """`adb forward <local> <remote>`, e.g. forward('emulator-5554', 'tcp:8080', 'tcp:8080')."""
    proc = _run(['-s', serial, 'forward', local, remote], timeout=10)
    return proc.stdout.decode('utf-8', 'replace').strip()


def reverse(serial: str, remote: str, local: str) -> str:
    """`adb reverse <remote> <local>` — exposes a port on the computer to the device."""
    proc = _run(['-s', serial, 'reverse', remote, local], timeout=10)
    return proc.stdout.decode('utf-8', 'replace').strip()


def forward_list() -> list[tuple[str, str, str]]:
    """Every active forward rule across all devices, as (serial, local, remote)."""
    proc = _run(['forward', '--list'], timeout=10)
    out = proc.stdout.decode('utf-8', 'replace')
    rules = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            rules.append((parts[0], parts[1], parts[2]))
    return rules


def forward_remove(serial: str, local: str):
    _run(['-s', serial, 'forward', '--remove', local], timeout=10)


def forward_remove_all(serial: str):
    _run(['-s', serial, 'forward', '--remove-all'], timeout=10)


def pair(host_port: str, pairing_code: str) -> str:
    """Android 11+ wireless-debugging pairing: `adb pair <ip:port> <code>`.
    host_port is the pairing service's ip:port shown on the phone's
    'Pair device with pairing code' screen, not the final connect port."""
    proc = _run(['pair', host_port, pairing_code], timeout=15)
    return proc.stdout.decode('utf-8', 'replace').strip()


def connect(host_port: str) -> str:
    proc = _run(['connect', host_port], timeout=15)
    return proc.stdout.decode('utf-8', 'replace').strip()


def disconnect(host_port: Optional[str] = None) -> str:
    args = ['disconnect'] + ([host_port] if host_port else [])
    proc = _run(args, timeout=10)
    return proc.stdout.decode('utf-8', 'replace').strip()


class AdbDevice:
    """Every command issued through an instance of this class is pinned to
    one device serial (`adb -s <serial> ...`), so operating on several
    phones in one session can't cross-contaminate."""

    def __init__(self, serial: str):
        self.serial = serial

    def _args(self, *args: str) -> list[str]:
        return ['-s', self.serial] + list(args)

    def run(self, *args: str, timeout: float = 20.0) -> str:
        proc = _run(self._args(*args), timeout=timeout)
        return proc.stdout.decode('utf-8', 'replace')

    def shell(self, command: str, timeout: float = 20.0) -> str:
        """Run one shell command on the device and return stdout. Exit
        codes from the *shell command itself* aren't surfaced by adb's
        transport layer the same way local failures are, so callers that
        care should check the output text (ByteADB's higher-level modules
        do this where it matters, e.g. checking `echo $?`)."""
        proc = _run(self._args('shell', command), timeout=timeout)
        return proc.stdout.decode('utf-8', 'replace')

    def shell_with_exit_code(self, command: str, timeout: float = 20.0) -> tuple[str, int]:
        wrapped = f'{command}; echo __BYTEADB_EXIT:$?'
        out = self.shell(wrapped, timeout=timeout)
        marker = '__BYTEADB_EXIT:'
        if marker in out:
            body, _, code = out.rpartition(marker)
            try:
                return body.rstrip('\n'), int(code.strip())
            except ValueError:
                return body.rstrip('\n'), -1
        return out, -1

    def push(self, local: str, remote: str, timeout: float = 120.0) -> str:
        return self.run('push', local, remote, timeout=timeout)

    def pull(self, remote: str, local: str, timeout: float = 120.0) -> str:
        return self.run('pull', remote, local, timeout=timeout)

    def reboot(self, mode: Optional[str] = None):
        """mode: None (normal), 'recovery', 'bootloader', 'sideload', 'sideload-auto-reboot'."""
        args = ['reboot'] + ([mode] if mode else [])
        self.run(*args, timeout=15)

    def root(self) -> str:
        return self.run('root', timeout=15)

    def wait_for_device(self, timeout: float = 30.0):
        self.run('wait-for-device', timeout=timeout)

    def get_prop(self, prop: str) -> str:
        return self.shell(f'getprop {prop}').strip()

    def info(self) -> dict:
        """A small, fast bundle of device facts for dashboards/headers."""
        props = {
            'model': 'ro.product.model',
            'manufacturer': 'ro.product.manufacturer',
            'android_version': 'ro.build.version.release',
            'sdk': 'ro.build.version.sdk',
            'build_id': 'ro.build.display.id',
            'abi': 'ro.product.cpu.abi',
            'serialno': 'ro.serialno',
        }
        result = {}
        for key, prop in props.items():
            try:
                result[key] = self.get_prop(prop)
            except AdbError:
                result[key] = None
        try:
            battery = self.shell('dumpsys battery')
            for line in battery.splitlines():
                line = line.strip()
                if line.startswith('level:'):
                    result['battery_level'] = line.split(':', 1)[1].strip()
                elif line.startswith('status:'):
                    result['battery_status'] = line.split(':', 1)[1].strip()
        except AdbError:
            pass
        return result
