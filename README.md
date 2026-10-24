<p align="center">
  <img src="assets/banner.svg" alt="ByteADB Banner" width="100%">
</p>

<p align="center">
  <strong>Professional ADB Control Toolkit — a real terminal dashboard, not another thin wrapper script.</strong>
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-4fd1ff?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-4fd1ff?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-4fd1ff?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-4fd1ff?style=flat-square">
  <img alt="Modules" src="https://img.shields.io/badge/modules-20-9ece6a?style=flat-square">
</p>

---

Most ADB "helper" tools are either a single Python script with a handful of hardcoded commands, or a GUI app that hides what it's actually running. ByteADB is neither: it's a proper CLI for scripting, **and** a full-screen terminal dashboard for everything else — files, apps, logcat, shell, screen, input, settings, wireless — all built on the real `adb` binary, never a reimplementation of the protocol.

**V1 is CLI/TUI only, on purpose.** A web panel is planned as a separate V2 product rather than bolted onto this one — a terminal tool and a web app want different security models and different UX, so they're staying apart.

<p align="center">
  <img src="assets/menu-screenshot.svg" alt="ByteADB Main Menu" width="100%">
</p>

## Why not just use `adb` directly?

You still can — ByteADB never hides what it runs. What it adds:

- **One consistent interface** instead of memorizing `pm`, `am`, `settings`, `dumpsys` flags for every task.
- **A real dashboard** with a numbered interactive menu to browse files, manage apps, tail logs, and control your device without juggling five terminal tabs.
- **Safe multi-device handling** — every command is pinned to one serial, so a second phone plugged in mid-session can't make you run something on the wrong device.
- **Honest errors** — a failed command shows you the exact `adb` invocation and its real stderr, not a swallowed exception.
- **ROM-compatible** — multi-fallback strategies for content providers that work on Xiaomi/MIUI, Samsung OneUI, Huawei EMUI, and stock Android alike.

## Install

No venv, no build step — clone it, install the three dependencies, run the file:

```bash
git clone https://github.com/AliXByte/ByteADB-V1.git
cd ByteADB-V1
pip install -r requirements.txt
python3 byteadb.py
```

You'll also need the real [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (`adb`) on your PATH — ByteADB drives it, it doesn't bundle it.

## Quick start

```bash
python3 byteadb.py                       # no arguments -> launches the numbered menu
python3 byteadb.py devices list          # see what's attached
python3 byteadb.py devices info          # model, Android version, battery — auto-picks the only device
python3 byteadb.py files ls /sdcard
python3 byteadb.py apps list --user-only
python3 byteadb.py logcat tail --level W
python3 byteadb.py screen shot photo.png
```

(If you'd rather install it as a real `byteadb` command on your PATH, `pip install -e .` still works and every example above drops the `python3 byteadb.py` prefix in favor of just `byteadb`.)

## Features

<p align="center">
  <img src="assets/features.svg" alt="ByteADB Features" width="100%">
</p>

## The dashboard

Running `byteadb` with no arguments (or `byteadb menu`) opens the interactive numbered dashboard — a banner, a numbered menu, pick a number, do the thing, back to the menu:

```
 1. Device Connection ›               12. Power, Reboot & Lock ›
 2. ADB & Wireless Debugging ›        13. Device Information ›
 3. Mirror, Control & Camera Live ›   14. Media & Links ›
 4. Screen Capture ›                  15. Network Tools ›
 5. Audio Capture (mic / device) ›    16. Display & Sound ›
 6. File Transfer ›                   17. Location & App Usage ›
 7. App Management ›                  18. Radios & Battery Mock ›
 8. Device Shell ›                    19. Security Check ›
 9. Logcat (Live / Save Snippet) ›    20. Communication ›
10. Input & Keyevents ›               21. System & Process Manager ›
11. Settings (get / put / list) ›

99. Clear     0. Exit
[Main Menu] >
```

Every option is backed by a `byteadb.core` module — the menu is just a friendlier front door to the same logic the scriptable subcommands use.

## Command reference

| Group | Commands |
|---|---|
| `devices` | `list`, `info`, `reboot` |
| `files` | `ls`, `mkdir`, `rm`, `mv`, `push`, `pull` |
| `apps` | `list`, `info`, `install`, `uninstall`, `clear`, `force-stop`, `enable`, `disable`, `launch`, `grant`, `revoke` |
| `shell` | run one command, or drop into an interactive shell with none |
| `logcat` | `tail` (with `--level`/`--tag` filters), `clear` |
| `screen` | `shot`, `record`, `mirror` (via scrcpy) |
| `control` | `tap`, `swipe`, `text`, `key`, `reboot` |
| `settings` | `get`, `put`, `list` (system/secure/global) |
| `wireless` | `pair`, `connect`, `disconnect`, `enable-tcpip` |

Every device-scoped command accepts `--serial/-s` to target a specific phone when more than one is attached; with exactly one attached, ByteADB picks it automatically.

## Project structure

```
ByteADB/
├── byteadb.py              # entry point
├── byteadb/
│   ├── core/               # pure logic — 20 modules, talks to `adb`, nothing else
│   │   ├── adb.py            # process wrapper, device listing, AdbDevice
│   │   ├── files.py          # ls/mkdir/rm/mv/push/pull
│   │   ├── apps.py           # pm/am wrappers: install, uninstall, permissions, launch
│   │   ├── logcat.py         # streaming logcat with level/tag filters
│   │   ├── screen.py         # screenshot, screenrecord, scrcpy mirroring
│   │   ├── control.py        # input tap/swipe/text/keyevent, reboot modes
│   │   ├── settings.py       # settings get/put/list across namespaces
│   │   ├── wireless.py       # pairing-code flow, tcpip mode
│   │   ├── communication.py  # contacts, call log, calendar, notifications
│   │   ├── system.py         # processes, services, bugreport, properties
│   │   ├── sysinfo.py        # cpu, memory, storage, thermal status
│   │   ├── network.py        # wifi, IP, LAN scan, port forwarding
│   │   ├── display.py        # brightness, resolution, density, rotation
│   │   ├── media.py          # media files, open URLs
│   │   ├── location.py       # GPS mock, geolocation
│   │   ├── usage.py          # app usage stats, battery stats
│   │   ├── radios.py         # airplane mode, wifi/bt/nfc toggle, battery mock
│   │   ├── security.py       # security audit, SELinux, encryption status
│   │   ├── sms.py            # SMS operations
│   │   └── __init__.py
│   ├── cli/
│   │   ├── main.py           # Click CLI entry
│   │   └── menu.py           # interactive numbered menu (2000+ lines)
│   └── tui/
│       └── app.py            # Textual dashboard
├── tests/                    # unit tests
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

## Live mirroring

Full mouse/keyboard screen control needs real-time video decode, which ByteADB deliberately doesn't reimplement. `byteadb screen mirror` shells out to [scrcpy](https://github.com/Genymobile/scrcpy) if it's installed — the same honest-integration approach as everything else here, with a clear error (and the install link) if it isn't.

## Security notes

ByteADB only does what `adb` itself can already do on an authorized, debugging-enabled device — it doesn't exploit anything, bypass Android's permission model, or talk to a phone that hasn't explicitly authorized this computer's RSA key. Every destructive action (`rm`, `uninstall`, `clear`, `force-stop`, reboot into another mode) runs exactly when you ask for it, with the real command shown on failure.

## License

Released under the [MIT License](LICENSE).

## Credits

ByteADB is designed and built by **[AliXByte](https://github.com/AliXByte)**.
