"""
ByteADB · communication — phone calls, contacts, call log, calendar

Direct ADB wrappers for making/ending calls, reading contacts, call
history, and calendar events from the device's content providers.

Multiple fallback strategies for Xiaomi / MIUI / Samsung / custom ROMs
that silently truncate or block `content query` results.
"""
from __future__ import annotations

import re

from byteadb.core.adb import AdbDevice


def _parse_content_rows(raw: str) -> list[dict]:
    """Parse `content query` output into a list of dicts.
    Each row looks like: Row: N key1=val1, key2=val2, ...
    Values can contain commas inside — we split only on ', key=' patterns."""
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('No result'):
            continue
        # Strip the "Row: N " prefix if present
        m = re.match(r'^Row:\s*\d+\s+', line)
        if m:
            line = line[m.end():]
        elif not re.search(r'\w+=', line):
            continue
        row = {}
        # Split on ", key=" boundaries — look-ahead for known key pattern
        parts = re.split(r',\s+(?=\w+=)', line)
        for part in parts:
            eq = part.find('=')
            if eq > 0:
                k = part[:eq].strip()
                v = part[eq + 1:].strip()
                if v != 'NULL':
                    row[k] = v
        if row:
            rows.append(row)
    return rows


# ── Phone Calls ──────────────────────────────────────────────────────────

def make_call(device: AdbDevice, number: str) -> str:
    """Initiate a phone call to the given number (actually dials, not just
    opens the dialer). Uses ACTION_CALL intent."""
    clean = re.sub(r'[^0-9+*#]', '', number)
    if not clean:
        return 'Invalid phone number.'
    out = device.shell(f"am start -a android.intent.action.CALL -d 'tel:{clean}'")
    if 'Error' in out:
        return f'Failed: {out.strip()}'
    return f'Calling {clean}...'


def end_call(device: AdbDevice) -> str:
    """End the current phone call."""
    device.shell('input keyevent KEYCODE_ENDCALL')
    return 'Call ended.'


def open_dialer(device: AdbDevice, number: str = '') -> str:
    """Open dialer with a number pre-filled (does NOT auto-dial)."""
    if number:
        clean = re.sub(r'[^0-9+*#]', '', number)
        device.shell(f"am start -a android.intent.action.DIAL -d 'tel:{clean}'")
    else:
        device.shell('am start -a android.intent.action.DIAL')
    return 'Dialer opened.'


# ── Contacts ─────────────────────────────────────────────────────────────

def _contacts_via_data_table(device: AdbDevice) -> list[dict]:
    """Strategy 1: Read contacts from the data table using the name mimetype.
    This bypasses aggregation issues and ROM-specific content provider limits.
    Gets ALL names, then batch-fetches phones/emails separately."""
    out = device.shell(
        "content query --uri content://com.android.contacts/data "
        "--where \"mimetype='vnd.android.cursor.item/name'\" "
        "2>/dev/null",
        timeout=90,
    )
    rows = _parse_content_rows(out)
    contacts = []
    seen_ids: set[str] = set()
    for row in rows:
        # data1 = display_name in name rows
        name = row.get('data1', '') or row.get('display_name', '')
        cid = row.get('contact_id', '') or row.get('raw_contact_id', '')
        if name and cid and cid not in seen_ids:
            seen_ids.add(cid)
            contacts.append({'name': name, 'id': cid, 'phones': [], 'emails': []})
    return contacts


def _contacts_via_contacts_table(device: AdbDevice) -> list[dict]:
    """Strategy 2: Query the contacts table WITHOUT --projection.
    Some ROMs (Xiaomi/MIUI) silently truncate results when --projection is used."""
    out = device.shell(
        'content query --uri content://com.android.contacts/contacts '
        '2>/dev/null',
        timeout=90,
    )
    rows = _parse_content_rows(out)
    contacts = []
    seen_ids: set[str] = set()
    for row in rows:
        name = row.get('display_name', '') or row.get('display_name_alt', '')
        cid = row.get('_id', '')
        if name and cid and cid not in seen_ids:
            seen_ids.add(cid)
            contacts.append({'name': name, 'id': cid, 'phones': [], 'emails': []})
    return contacts


def _contacts_via_raw_contacts(device: AdbDevice) -> list[dict]:
    """Strategy 3: Query raw_contacts — not aggregated, every account entry
    is its own row. More reliable on some custom ROMs."""
    out = device.shell(
        'content query --uri content://com.android.contacts/raw_contacts '
        '2>/dev/null',
        timeout=90,
    )
    rows = _parse_content_rows(out)
    contacts = []
    seen_ids: set[str] = set()
    for row in rows:
        name = row.get('display_name', '') or row.get('display_name_alt', '')
        cid = row.get('contact_id', '') or row.get('_id', '')
        if name and cid and cid not in seen_ids:
            seen_ids.add(cid)
            contacts.append({'name': name, 'id': cid, 'phones': [], 'emails': []})
    return contacts


def _contacts_via_phone_lookup(device: AdbDevice) -> list[dict]:
    """Strategy 4 (fallback): Read ALL phone_v2 entries from the data table.
    Each row has contact_id + data1 (number) + display_name.
    This always works because it's the simplest content provider query."""
    out = device.shell(
        "content query --uri content://com.android.contacts/data "
        "--where \"mimetype='vnd.android.cursor.item/phone_v2'\" "
        "2>/dev/null",
        timeout=90,
    )
    rows = _parse_content_rows(out)
    contacts_map: dict[str, dict] = {}
    for row in rows:
        cid = row.get('contact_id', '') or row.get('raw_contact_id', '')
        name = row.get('display_name', '') or row.get('data4', '')
        phone = row.get('data1', '')
        if not cid:
            continue
        if cid not in contacts_map:
            contacts_map[cid] = {'name': name or f'Contact #{cid}', 'id': cid,
                                 'phones': [], 'emails': []}
        if phone and phone not in contacts_map[cid]['phones']:
            contacts_map[cid]['phones'].append(phone)
    return list(contacts_map.values())


def list_contacts(device: AdbDevice, full: bool = True) -> list[dict]:
    """Read ALL contacts from the device.
    Tries multiple strategies because Xiaomi/MIUI/Samsung ROMs silently
    truncate content query results — especially with --projection."""

    # Try strategies in order — pick the one that returns the most contacts
    best: list[dict] = []

    for strategy in (_contacts_via_data_table,
                     _contacts_via_contacts_table,
                     _contacts_via_raw_contacts):
        try:
            result = strategy(device)
            if len(result) > len(best):
                best = result
        except Exception:
            continue

    # If still empty or suspiciously low, try the phone_lookup fallback
    # which gets contacts with phones at minimum
    if len(best) < 5:
        try:
            phone_result = _contacts_via_phone_lookup(device)
            if len(phone_result) > len(best):
                best = phone_result
        except Exception:
            pass

    if not full or not best:
        return best

    # Batch-fetch ALL phone numbers (no --projection, no --sort for max compat)
    phone_out = device.shell(
        "content query --uri content://com.android.contacts/data "
        "--where \"mimetype='vnd.android.cursor.item/phone_v2'\" "
        "2>/dev/null",
        timeout=90,
    )
    # Batch-fetch ALL emails
    email_out = device.shell(
        "content query --uri content://com.android.contacts/data "
        "--where \"mimetype='vnd.android.cursor.item/email_v2'\" "
        "2>/dev/null",
        timeout=90,
    )

    # Build lookup maps
    phones: dict[str, list[str]] = {}
    emails: dict[str, list[str]] = {}

    for row in _parse_content_rows(phone_out):
        cid = row.get('contact_id', '') or row.get('raw_contact_id', '')
        val = row.get('data1', '')
        if cid and val:
            phones.setdefault(cid, []).append(val)

    for row in _parse_content_rows(email_out):
        cid = row.get('contact_id', '') or row.get('raw_contact_id', '')
        val = row.get('data1', '')
        if cid and val:
            emails.setdefault(cid, []).append(val)

    # Attach to contacts (deduplicated)
    for c in best:
        cid = c['id']
        # Merge with already-found phones (from phone_lookup strategy)
        existing_phones = c.get('phones', [])
        all_phones = existing_phones + phones.get(cid, [])
        c['phones'] = list(dict.fromkeys(all_phones))

        existing_emails = c.get('emails', [])
        all_emails = existing_emails + emails.get(cid, [])
        c['emails'] = list(dict.fromkeys(all_emails))

    return best


def contact_details(device: AdbDevice, contact_id: str) -> list[dict]:
    """Get ALL data (phone, email, address, org, etc.) for a contact by ID.
    No --projection for maximum compatibility with custom ROMs."""
    results = []
    # Try contact_id first, fallback to raw_contact_id
    out = device.shell(
        f'content query --uri content://com.android.contacts/data '
        f'--where "contact_id={contact_id}" '
        f'2>/dev/null',
        timeout=30,
    )
    rows = _parse_content_rows(out)
    if not rows:
        out = device.shell(
            f'content query --uri content://com.android.contacts/data '
            f'--where "raw_contact_id={contact_id}" '
            f'2>/dev/null',
            timeout=30,
        )
        rows = _parse_content_rows(out)

    mime_labels = {
        'vnd.android.cursor.item/phone_v2': 'Phone',
        'vnd.android.cursor.item/email_v2': 'Email',
        'vnd.android.cursor.item/postal-address_v2': 'Address',
        'vnd.android.cursor.item/organization': 'Organization',
        'vnd.android.cursor.item/website': 'Website',
        'vnd.android.cursor.item/note': 'Note',
        'vnd.android.cursor.item/nickname': 'Nickname',
        'vnd.android.cursor.item/im': 'IM',
        'vnd.android.cursor.item/sip_address': 'SIP',
        'vnd.android.cursor.item/relation': 'Relation',
        'vnd.android.cursor.item/name': 'Name',
    }
    for row in rows:
        mime = row.get('mimetype', '')
        val = row.get('data1', '')
        if not val:
            continue
        label = mime_labels.get(mime, '')
        if not label:
            continue
        # Skip the Name entry since we already show it
        if label == 'Name':
            continue
        extra = row.get('data2', '')
        if extra and label in ('Phone', 'Email'):
            # data2 is the type (1=Home, 2=Mobile, 3=Work, etc.)
            type_labels = {'1': 'Home', '2': 'Mobile', '3': 'Work', '4': 'Fax Work',
                           '5': 'Fax Home', '7': 'Other', '12': 'Main'}
            type_name = type_labels.get(extra, extra)
            label = f'{label} ({type_name})'
        results.append({'type': label, 'value': val})
    return results


def add_contact(device: AdbDevice, name: str, phone: str = '', email: str = '') -> str:
    """Add a new contact using INSERT intent (opens Contacts app for confirmation)."""
    cmd = (f"am start -a android.intent.action.INSERT "
           f"-t vnd.android.cursor.dir/contact "
           f"-e name '{name}'")
    if phone:
        cmd += f" -e phone '{phone}'"
    if email:
        cmd += f" -e email '{email}'"
    device.shell(cmd)
    return f'Contact creation form opened for {name}.'


def delete_contact(device: AdbDevice, contact_id: str) -> str:
    """Delete a contact by ID."""
    out, code = device.shell_with_exit_code(
        f'content delete --uri content://com.android.contacts/contacts/{contact_id}'
    )
    if code == 0:
        return f'Contact {contact_id} deleted.'
    return f'Failed to delete contact: {out.strip()}'


# ── Call Log ─────────────────────────────────────────────────────────────

def _call_log_via_content(device: AdbDevice) -> list[dict]:
    """Strategy 1: content query on call_log — no --projection for max compat."""
    out = device.shell(
        'content query --uri content://call_log/calls '
        '2>/dev/null',
        timeout=60,
    )
    return _parse_content_rows(out)


def _call_log_via_dumpsys(device: AdbDevice) -> list[dict]:
    """Strategy 2: parse dumpsys telecom for recent calls."""
    out = device.shell('dumpsys telecom 2>/dev/null', timeout=30)
    calls = []
    for m in re.finditer(
        r'(?:Call|CallRecord)\s*\[.*?'
        r'(?:handle|number)[=:]\s*(?:tel:)?([+\d*#]+).*?'
        r'(?:type|direction)[=:]\s*(\w+)',
        out, re.IGNORECASE | re.DOTALL
    ):
        calls.append({
            'number': m.group(1),
            'type_name': m.group(2).capitalize(),
        })
    return calls


def _call_log_via_telephony_db(device: AdbDevice) -> list[dict]:
    """Strategy 3: directly query the telephony database if accessible."""
    # Try common paths for the calls database on different ROMs
    db_paths = [
        '/data/data/com.android.providers.contacts/databases/calllog.db',
        '/data/data/com.android.providers.contacts/databases/contacts2.db',
    ]
    for db in db_paths:
        out = device.shell(
            f'sqlite3 {db} "SELECT number, type, date, duration '
            f'FROM calls ORDER BY date DESC LIMIT 50;" 2>/dev/null',
            timeout=30,
        )
        if out.strip() and 'Error' not in out and 'not found' not in out:
            calls = []
            type_names = {'1': 'Incoming', '2': 'Outgoing', '3': 'Missed',
                          '4': 'Voicemail', '5': 'Rejected', '6': 'Blocked'}
            for line in out.strip().splitlines():
                parts = line.split('|')
                if len(parts) >= 4:
                    try:
                        import datetime
                        ts = int(parts[2]) / 1000
                        date_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                    except (ValueError, OSError, IndexError):
                        date_str = parts[2] if len(parts) > 2 else '—'
                    calls.append({
                        'number': parts[0],
                        'type': parts[1],
                        'type_name': type_names.get(parts[1], 'Unknown'),
                        'date_str': date_str,
                        'duration': parts[3],
                    })
            if calls:
                return calls
    return []


def call_log(device: AdbDevice, limit: int = 30) -> list[dict]:
    """Read recent call history. Tries multiple strategies for ROM compat."""
    type_names = {'1': 'Incoming', '2': 'Outgoing', '3': 'Missed',
                  '4': 'Voicemail', '5': 'Rejected', '6': 'Blocked'}

    # Strategy 1: content query (no --projection)
    rows = _call_log_via_content(device)
    if rows:
        calls = []
        for row in rows:
            if 'number' not in row:
                continue
            row['type_name'] = type_names.get(row.get('type', ''), 'Unknown')
            if 'date' in row:
                try:
                    import datetime
                    ts = int(row['date']) / 1000
                    row['date_str'] = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                except (ValueError, OSError):
                    row['date_str'] = row['date']
            calls.append(row)
            if len(calls) >= limit:
                break
        if calls:
            return calls

    # Strategy 2: dumpsys telecom
    calls = _call_log_via_dumpsys(device)
    if calls:
        return calls[:limit]

    # Strategy 3: direct database query (needs root or permissive shell)
    calls = _call_log_via_telephony_db(device)
    if calls:
        return calls[:limit]

    return []


# ── Calendar ─────────────────────────────────────────────────────────────

def calendar_events(device: AdbDevice, limit: int = 20) -> list[dict]:
    """Read upcoming calendar events."""
    # No --projection for max ROM compatibility
    out = device.shell(
        'content query --uri content://com.android.calendar/events '
        '2>/dev/null',
        timeout=30,
    )
    events = []
    for row in _parse_content_rows(out):
        if 'title' not in row:
            continue
        if 'dtstart' in row:
            try:
                import datetime
                ts = int(row['dtstart']) / 1000
                row['start_str'] = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            except (ValueError, OSError):
                row['start_str'] = row['dtstart']
        events.append(row)
        if len(events) >= limit:
            break
    return events


def add_calendar_event(device: AdbDevice, title: str, begin_time: str = '', end_time: str = '') -> str:
    """Open calendar to add a new event."""
    cmd = f"am start -a android.intent.action.INSERT -t vnd.android.cursor.item/event -e title '{title}'"
    if begin_time:
        cmd += f" -e beginTime '{begin_time}'"
    if end_time:
        cmd += f" -e endTime '{end_time}'"
    device.shell(cmd)
    return 'Calendar event creation opened.'


# ── Notifications ────────────────────────────────────────────────────────

def active_notifications(device: AdbDevice) -> list[dict]:
    """Read currently active notifications from the notification shade."""
    out = device.shell('dumpsys notification --noredact 2>/dev/null || dumpsys notification', timeout=15)
    notifs = []
    current: dict = {}
    for line in out.splitlines():
        line_s = line.strip()
        if line_s.startswith('NotificationRecord'):
            if current and current.get('package'):
                notifs.append(current)
            current = {'package': '', 'title': '', 'text': ''}
            m = re.search(r'pkg=(\S+)', line_s)
            if m:
                current['package'] = m.group(1)
        elif 'android.title=' in line_s:
            m = re.search(r'android\.title=(.+?)(?:\s*android\.|$)', line_s)
            if m:
                current['title'] = m.group(1).strip()
        elif 'android.text=' in line_s:
            m = re.search(r'android\.text=(.+?)(?:\s*android\.|$)', line_s)
            if m:
                current['text'] = m.group(1).strip()
    if current and current.get('package'):
        notifs.append(current)
    return notifs
