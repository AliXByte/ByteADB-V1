<h1 align="center">ByteADB</h1>

<p align="center">A professional, all-in-one ADB control toolkit — a real terminal dashboard, not another thin wrapper script.</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-4fd1ff?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-4fd1ff?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-4fd1ff?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-4fd1ff?style=flat-square">
</p>

Most ADB "helper" tools are either a single Python script with a handful of hardcoded commands, or a GUI app that hides what it's actually running. ByteADB is neither: it's a proper CLI for scripting, **and** a full-screen terminal dashboard for everything else — files, apps, logcat, shell, screen, input, settings, wireless — all built on the real `adb` binary, never a reimplementation of the protocol.

**V1 is CLI/TUI only, on purpose.** A web panel is planned as a separate V2 product rather than bolted onto this one — a terminal tool and a web app want different security models and different UX, so they're staying apart.

## Why not just use `adb` directly?

You still can — ByteADB never hides what it runs. What it adds:

- **One consistent interface** instead of memorizing `pm`, `am`, `settings`, `dumpsys` flags for every task.
- **A real dashboard** (Textual) to browse files, manage apps and tail logs without juggling five terminal tabs.
- **Safe multi-device handling** — every command is pinned to one serial, so a second phone plugged in mid-session can't make you run something on the wrong device.
- **Honest errors** — a failed command shows you the exact `adb` invocation and its real stderr, not a swallowed exception.

## Install

```bash
git clone https://github.com/AliXByte/ByteADB.git
cd ByteADB
pip install -e .
```

Or just run the launcher, which sets up a virtualenv for you:

```bash
./run.sh      # Linux/macOS
run.bat       # Windows
```

You'll also need the real [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (`adb`) on your PATH — ByteADB drives it, it doesn't bundle it.

## Quick start

```bash
byteadb devices list          # see what's attached
byteadb devices info          # model, Android version, battery — auto-picks the only device
byteadb files ls /sdcard
byteadb apps list --user-only
byteadb logcat tail --level W
byteadb screen shot photo.png
byteadb                       # no subcommand -> launches the full dashboard
```

## The dashboard (TUI)

Running `byteadb` with no arguments (or `byteadb tui`) opens a full-screen terminal dashboard:

- **Device picker** — lists every attached/paired device with its state, refresh with `r`.
- **Overview** — model, Android version, battery, one-click screenshot and reboot.
- **Files** — browse any path the shell can reach, drill into directories, see size/permissions.
- **Apps** — list user or system packages, force-stop or clear data on the selected one.
- **Logcat** — live-tailing log view, start/stop/clear.
- **Shell** — a command box with scrolling output, for anything not covered by a dedicated tab.

## Wireless debugging

Two supported paths, both real Android features:

```bash
# Android 11+: Settings > Developer options > Wireless debugging > Pair device with pairing code
byteadb wireless pair 192.168.1.20:41234 123456 192.168.1.20:37015

# Classic: phone connected by USB once, then switched to Wi-Fi
byteadb wireless enable-tcpip
byteadb wireless connect 192.168.1.20:5555
```

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

## Live mirroring

Full mouse/keyboard screen control needs real-time video decode, which ByteADB deliberately doesn't reimplement. `byteadb screen mirror` shells out to [scrcpy](https://github.com/Genymobile/scrcpy) if it's installed — the same honest-integration approach as everything else here, with a clear error (and the install link) if it isn't.

## Project structure

```
ByteADB/
├── byteadb/
│   ├── core/              # pure logic — talks to the real `adb` binary, nothing else
│   │   ├── adb.py           # process wrapper, device listing, AdbDevice (serial-pinned commands)
│   │   ├── files.py         # ls/mkdir/rm/mv/push/pull
│   │   ├── apps.py          # pm/am wrappers: install, uninstall, permissions, launch...
│   │   ├── logcat.py        # streaming logcat with level/tag filters
│   │   ├── screen.py        # screenshot, screenrecord, scrcpy mirroring
│   │   ├── control.py       # input tap/swipe/text/keyevent, reboot modes
│   │   ├── settings.py      # settings get/put/list across namespaces
│   │   └── wireless.py      # pairing-code flow, tcpip mode
│   ├── cli/                # Click-based CLI, one file per command group
│   └── tui/
│       └── app.py           # the Textual dashboard
├── tests/                  # 33 unit tests over the core layer (parsing, error handling)
├── pyproject.toml
├── requirements.txt
├── run.sh / run.bat
└── LICENSE
```

## Security notes

ByteADB only does what `adb` itself can already do on an authorized, debugging-enabled device — it doesn't exploit anything, bypass Android's permission model, or talk to a phone that hasn't explicitly authorized this computer's RSA key. Every destructive action (`rm`, `uninstall`, `clear`, `force-stop`, reboot into another mode) runs exactly when you ask for it, with the real command shown on failure.

## License

Released under the [MIT License](LICENSE).

## Credits

ByteADB is designed and built by **[AliXByte](https://github.com/AliXByte)**.
