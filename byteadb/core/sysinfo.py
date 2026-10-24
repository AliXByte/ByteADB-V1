"""
ByteADB · extended device/account/SIM/Bluetooth/battery information

`AdbDevice.info()` (in core/adb.py) is the small, fast bundle used for
dashboard headers. Everything here is the deeper, slower stuff you ask
for explicitly: full build/security info, accounts, SIM/operator,
Bluetooth, locale, and the full battery dump.
"""
from __future__ import annotations

import re

from byteadb.core.adb import AdbDevice


def full_device_info(device: AdbDevice) -> dict:
    props = {
        'model': 'ro.product.model',
        'manufacturer': 'ro.product.manufacturer',
        'brand': 'ro.product.brand',
        'device': 'ro.product.device',
        'board': 'ro.product.board',
        'chipset': 'ro.board.platform',
        'android_version': 'ro.build.version.release',
        'sdk': 'ro.build.version.sdk',
        'security_patch': 'ro.build.version.security_patch',
        'build_id': 'ro.build.display.id',
        'build_fingerprint': 'ro.build.fingerprint',
        'abi': 'ro.product.cpu.abi',
        'serialno': 'ro.serialno',
        'android_id_prop': 'ro.boot.serialno',
        'debuggable': 'ro.debuggable',
        'secure': 'ro.secure',
        'tags': 'ro.build.tags',
    }
    result = {k: device.get_prop(v) or None for k, v in props.items()}
    enc = device.shell('getprop ro.crypto.state').strip()
    result['encryption_state'] = enc or 'unknown'
    # IMEI needs a privileged API on modern Android and is usually blocked
    # for the shell user — try, and report honestly if it isn't available.
    imei_out = device.shell('service call iphonesubinfo 1 2>&1')
    imei = _extract_imei(imei_out)
    result['imei'] = imei or 'not accessible from this shell (needs a privileged API)'
    android_id = device.shell("settings get secure android_id").strip()
    result['android_id'] = android_id or None
    return result


def _extract_imei(raw: str) -> str | None:
    chars = re.findall(r"'(.)'", raw)
    if not chars:
        return None
    digits = ''.join(c for c in chars if c.isdigit())
    return digits or None


def accounts(device: AdbDevice) -> list[dict]:
    """Account *names and types* only (e.g. a Google account's email and
    'com.google') — never auth tokens, which `dumpsys account` doesn't
    expose to begin with.
    Tries multiple parsing approaches — `dumpsys account` output format
    varies across Android versions and OEMs.

    Some OEMs (notably Xiaomi/MIUI/HyperOS) censor account names in
    `dumpsys account` output (e.g. ali***@gmail.com). We try several
    alternative sources to get uncensored names."""
    seen: set[str] = set()
    results = []

    def _add(name: str, acct_type: str):
        name = name.strip()
        acct_type = acct_type.strip()
        if not name:
            return
        key = f"{name}|{acct_type}"
        if key not in seen:
            seen.add(key)
            results.append({'name': name, 'type': acct_type})

    def _is_censored(name: str) -> bool:
        """Check if name contains OEM censoring stars."""
        return '**' in name or '***' in name

    # ── Method 1: content provider query (uncensored on most OEMs) ────
    # Query raw_contacts for account_name/account_type — this bypasses
    # the dumpsys censoring that Xiaomi/MIUI applies.
    try:
        cr_out = device.shell(
            'content query --uri content://com.android.contacts/raw_contacts '
            '--projection account_name:account_type 2>/dev/null',
            timeout=10,
        )
        for m in re.finditer(r'account_name=([^,\s]+)\s*,?\s*account_type=([^,\s\r\n]+)', cr_out):
            _add(m.group(1), m.group(2))
        # Also try reversed column order
        for m in re.finditer(r'account_type=([^,\s]+)\s*,?\s*account_name=([^,\s\r\n]+)', cr_out):
            _add(m.group(2), m.group(1))
    except Exception:
        pass

    # ── Method 2: `dumpsys account` (standard, but may be censored) ───
    out = device.shell('dumpsys account', timeout=15)

    # Format 1: Account {name=user@gmail.com, type=com.google}
    for m in re.finditer(r'Account\s*\{name=([^,]+),\s*type=([^}]+)\}', out):
        _add(m.group(1), m.group(2))
    # Format 2: name=user@gmail.com  type=com.google (some OEMs, line-based)
    for m in re.finditer(r'name=(\S+@\S+)\s+type=(\S+)', out):
        _add(m.group(1), m.group(2))
    # Format 3: "User xxx" sections with account lines
    for m in re.finditer(r'(?:Account|account)\s*:\s*(\S+)\s*,\s*(\S+)', out):
        _add(m.group(1), m.group(2))

    # ── Method 3: `cmd account list` (Android 12+) ───────────────────
    try:
        cmd_out = device.shell('cmd account list 2>/dev/null', timeout=10)
        for m in re.finditer(r'Account\s*\{name=([^,]+),\s*type=([^}]+)\}', cmd_out):
            _add(m.group(1), m.group(2))
        # Some versions output: "name  type" per line
        for m in re.finditer(r'^\s*(\S+@\S+)\s+(\S+)\s*$', cmd_out, re.MULTILINE):
            _add(m.group(1), m.group(2))
    except Exception:
        pass

    # ── De-duplicate: prefer uncensored version of same account ───────
    # If we got both "ali***@gmail.com" and "alisport1308@gmail.com" for
    # the same type, drop the censored one.
    if results:
        clean: list[dict] = []
        by_type: dict[str, list[dict]] = {}
        for r in results:
            by_type.setdefault(r['type'], []).append(r)
        for acct_type, entries in by_type.items():
            uncensored = [e for e in entries if not _is_censored(e['name'])]
            censored = [e for e in entries if _is_censored(e['name'])]
            if uncensored:
                # Keep all uncensored entries
                clean.extend(uncensored)
                # Only keep censored if no uncensored match could cover it
                for c in censored:
                    # Check if any uncensored entry could be the same account
                    prefix = c['name'].split('*')[0]
                    if not any(u['name'].startswith(prefix) for u in uncensored):
                        clean.append(c)
            else:
                clean.extend(censored)
        results = clean

    return results


def sim_info(device: AdbDevice) -> dict:
    props = {
        'operator': 'gsm.operator.alpha',
        'operator_numeric': 'gsm.operator.numeric',
        'sim_state': 'gsm.sim.state',
        'sim_operator': 'gsm.sim.operator.alpha',
        'network_type': 'gsm.network.type',
        'country_iso': 'gsm.operator.iso-country',
    }
    result = {k: device.get_prop(v) or None for k, v in props.items()}
    # Try to read phone number(s) — multiple methods, varies by Android/OEM
    numbers = _get_phone_numbers(device)
    if numbers:
        result['phone_number'] = numbers
    else:
        result['phone_number'] = 'not accessible from this shell'
    return result


def _get_phone_numbers(device: AdbDevice) -> str | None:
    """Best-effort phone number retrieval. Most Android versions restrict
    phone number access to privileged apps, so this often fails — we try
    several paths and return the first that works."""
    # Method 1: telephony.manager service call (getLine1Number)
    out = device.shell('service call iphonesubinfo 15 2>/dev/null').strip()
    num = _extract_service_string(out)
    if num and any(c.isdigit() for c in num):
        return num
    # Method 2: dumpsys telephony.registry
    out = device.shell('dumpsys telephony.registry 2>/dev/null', timeout=10)
    for m in re.finditer(r'mLine1Number\s*=\s*(\+?\d[\d\s-]{5,})', out):
        return m.group(1).strip()
    # Method 3: SIM-related getprop
    for prop in ('gsm.sim.operator.numeric', 'ril.ecclist'):
        pass  # these don't contain phone numbers — skip
    num_prop = device.get_prop('gsm.msisdn')
    if num_prop and any(c.isdigit() for c in num_prop):
        return num_prop
    # Method 4: content provider (works on some older Android)
    out = device.shell(
        "content query --uri content://telephony/siminfo "
        "--projection number 2>/dev/null"
    ).strip()
    for m in re.finditer(r'number=(\+?\d[\d\s-]{5,})', out):
        return m.group(1).strip()
    return None


def _extract_service_string(raw: str) -> str | None:
    """Extract a string from Android `service call` Parcel output."""
    chars = re.findall(r"'(.)'", raw)
    if not chars:
        return None
    return ''.join(c for c in chars if c != '.').strip() or None


def bluetooth_devices(device: AdbDevice) -> list[dict]:
    """Paired/bonded Bluetooth devices by name and MAC, parsed from
    `dumpsys bluetooth_manager`. Tries multiple output formats across
    Android versions and OEMs (Samsung, Xiaomi/MIUI, AOSP).
    No vendor/OUI lookup — that needs an offline vendor database
    ByteADB doesn't ship."""
    out = device.shell('dumpsys bluetooth_manager', timeout=15)
    seen: set[str] = set()
    results = []

    def _add(name: str, mac: str):
        mac = mac.upper()
        if mac not in seen:
            seen.add(mac)
            results.append({'name': name.strip(), 'address': mac})

    # Format 1: "name: Foo, addr: AA:BB:CC:DD:EE:FF" (AOSP classic)
    for m in re.finditer(r'name:\s*(.+?)\s*,?\s*addr(?:ess)?:\s*([0-9A-Fa-f:]{17})', out):
        _add(m.group(1), m.group(2))
    # Format 2: "AA:BB:CC:DD:EE:FF  Name: Foo" (some Samsung/MIUI)
    for m in re.finditer(r'([0-9A-Fa-f:]{17})\s+Name:\s*(.+)', out):
        _add(m.group(2), m.group(1))
    # Format 3: Bonded devices section listing "XX:XX:XX:XX:XX:XX (DeviceName)"
    for m in re.finditer(r'([0-9A-Fa-f:]{17})\s*\(([^)]+)\)', out):
        _add(m.group(2), m.group(1))
    # Format 4: lines with "mAddress=XX:XX:XX:XX:XX:XX" and nearby "mName=Foo"
    for m in re.finditer(r'mName=(.+?)[\r\n].*?mAddress=([0-9A-Fa-f:]{17})', out, re.DOTALL):
        _add(m.group(1), m.group(2))
    for m in re.finditer(r'mAddress=([0-9A-Fa-f:]{17}).*?mName=(.+?)[\r\n]', out, re.DOTALL):
        _add(m.group(2), m.group(1))

    # Fallback: also try `dumpsys bluetooth_manager --bonded-devices` on newer Android
    if not results:
        out2 = device.shell('dumpsys bluetooth_manager --bonded-devices 2>/dev/null', timeout=10)
        for m in re.finditer(r'([0-9A-Fa-f:]{17})', out2):
            mac = m.group(1).upper()
            if mac not in seen:
                seen.add(mac)
                results.append({'name': '(unknown)', 'address': mac})

    return results


def battery_full(device: AdbDevice) -> dict:
    out = device.shell('dumpsys battery')
    result = {}
    for line in out.splitlines():
        line = line.strip()
        if ':' in line:
            k, _, v = line.partition(':')
            result[k.strip()] = v.strip()
    return result


def locale_info(device: AdbDevice) -> dict:
    return {
        'locales': device.shell('settings get system system_locales').strip(),
        'language_prop': device.get_prop('persist.sys.locale'),
        'timezone': device.shell('getprop persist.sys.timezone').strip(),
    }
