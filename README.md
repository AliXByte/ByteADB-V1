<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00d4ff,100:7b61ff&height=220&section=header&text=ByteADB&fontSize=80&fontColor=e6edf3&fontAlignY=35&desc=Professional%20ADB%20Control%20Toolkit&descSize=20&descColor=8b949e&descAlignY=55&animation=fadeIn" width="100%"/>
</p>

<p align="center">
  <a href="#">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&pause=1000&color=00D4FF&center=true&vCenter=true&multiline=true&repeat=true&width=700&height=100&lines=Full-control+ADB+toolkit+%E2%80%94+not+another+wrapper+script;20+core+modules+%C2%B7+21+menu+sections+%C2%B7+150%2B+commands;ROM+compatible+%E2%80%94+Xiaomi%2C+Samsung%2C+Pixel%2C+Huawei;Code.+Control.+Manage.+Repeat." alt="Typing SVG"/>
  </a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.0-00d4ff?style=for-the-badge&logo=semver&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/python-3.9+-3fb950?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-bb9af7?style=for-the-badge&logo=windowsterminal&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-e0af68?style=for-the-badge&logo=opensourceinitiative&logoColor=white">
</p>

<p align="center">
  <img alt="Modules" src="https://img.shields.io/badge/core_modules-20-00d4ff?style=flat-square">
  <img alt="Menu" src="https://img.shields.io/badge/menu_sections-21-3fb950?style=flat-square">
  <img alt="Commands" src="https://img.shields.io/badge/commands-150+-bb9af7?style=flat-square">
  <img alt="ROM" src="https://img.shields.io/badge/ROM-compatible-e0af68?style=flat-square">
</p>

---

<br>

> *Most ADB "helper" tools are either a single Python script with a handful of hardcoded commands, or a GUI app that hides what it's actually running. ByteADB is neither.*

ByteADB is a proper CLI for scripting **and** a full-screen terminal dashboard for everything else — files, apps, logcat, shell, screen, input, settings, wireless — all built on the real `adb` binary, never a reimplementation of the protocol.

**V1 is CLI/TUI only, on purpose.** A web panel is planned as a separate V2 product.

<br>

## 🖥️ Preview

<p align="center">
  <img src="assets/menu-screenshot.svg" alt="ByteADB Main Menu" width="100%">
</p>

<br>

## ⚡ Quick Install

```bash
git clone https://github.com/AliXByte/ByteADB-V1.git
cd ByteADB-V1
pip install -r requirements.txt
python3 byteadb.py
```

> You'll also need [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) (`adb`) on your PATH.

<br>

## 🧠 Why ByteADB?

<table>
<tr>
<td width="50%">

### 🔧 One Interface
Stop memorizing `pm`, `am`, `settings`, `dumpsys` flags — ByteADB wraps them all in a clean numbered menu.

### 🛡️ Safe Multi-Device
Every command is pinned to one serial. A second phone plugged in mid-session can't make you run something on the wrong device.

</td>
<td width="50%">

### 💀 Honest Errors
A failed command shows the exact `adb` invocation and its real stderr — not a swallowed exception.

### 📱 ROM Compatible
Multi-fallback strategies that work on Xiaomi/MIUI, Samsung OneUI, Huawei EMUI, and stock Android alike.

</td>
</tr>
</table>

<br>

## ⚔️ Features

<p align="center">
  <img src="assets/features.svg" alt="ByteADB Features" width="100%">
</p>

<br>

## 📋 The Dashboard

Running `byteadb` with no arguments opens the interactive numbered dashboard:

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
```

<br>

## 🚀 Usage

```bash
python3 byteadb.py                       # interactive menu
python3 byteadb.py devices list          # list attached devices
python3 byteadb.py devices info          # model, Android version, battery
python3 byteadb.py files ls /sdcard      # browse device files
python3 byteadb.py apps list --user-only # list installed apps
python3 byteadb.py logcat tail --level W # live logcat with filter
python3 byteadb.py screen shot photo.png # take screenshot
```

> Install as a command: `pip install -e .` → then use `byteadb` directly.

<br>

## 📦 Command Reference

| Group | Commands |
|:---|:---|
| `devices` | `list`, `info`, `reboot` |
| `files` | `ls`, `mkdir`, `rm`, `mv`, `push`, `pull` |
| `apps` | `list`, `info`, `install`, `uninstall`, `clear`, `force-stop`, `enable`, `disable`, `launch`, `grant`, `revoke` |
| `shell` | run one command, or drop into interactive shell |
| `logcat` | `tail` (with `--level`/`--tag` filters), `clear` |
| `screen` | `shot`, `record`, `mirror` (via scrcpy) |
| `control` | `tap`, `swipe`, `text`, `key`, `reboot` |
| `settings` | `get`, `put`, `list` (system/secure/global) |
| `wireless` | `pair`, `connect`, `disconnect`, `enable-tcpip` |

> Every device-scoped command accepts `--serial/-s` to target a specific phone.

<br>

## 🏗️ Project Structure

```
ByteADB/
├── byteadb.py              # entry point
├── byteadb/
│   ├── core/               # 20 modules — pure logic, talks to adb
│   │   ├── adb.py            # process wrapper, device listing
│   │   ├── apps.py           # install, uninstall, permissions, launch
│   │   ├── communication.py  # contacts, call log, calendar, notifications
│   │   ├── control.py        # tap, swipe, text, keyevent, reboot
│   │   ├── display.py        # brightness, resolution, density
│   │   ├── files.py          # ls, mkdir, rm, mv, push, pull
│   │   ├── location.py       # GPS mock, geolocation
│   │   ├── logcat.py         # streaming logcat with filters
│   │   ├── media.py          # media files, URLs
│   │   ├── network.py        # wifi, IP, LAN scan, port forwarding
│   │   ├── radios.py         # airplane, wifi/bt/nfc, battery mock
│   │   ├── screen.py         # screenshot, record, scrcpy mirror
│   │   ├── security.py       # security audit, SELinux
│   │   ├── settings.py       # get/put/list across namespaces
│   │   ├── sms.py            # SMS operations
│   │   ├── sysinfo.py        # cpu, memory, storage, thermal
│   │   ├── system.py         # processes, services, bugreport
│   │   ├── usage.py          # app usage, battery stats
│   │   └── wireless.py       # pairing, tcpip mode
│   ├── cli/
│   │   ├── main.py           # Click CLI entry
│   │   └── menu.py           # interactive menu (2000+ lines)
│   └── tui/
│       └── app.py            # Textual dashboard
├── tests/
├── pyproject.toml
├── requirements.txt
└── LICENSE
```

<br>

## 🔒 Security

ByteADB only does what `adb` itself can already do on an authorized, debugging-enabled device — it doesn't exploit anything, bypass Android's permission model, or talk to a phone that hasn't explicitly authorized this computer's RSA key.

<br>

## 📜 License

Released under the [MIT License](LICENSE).

<br>

---

<p align="center">
  <strong>Designed and built by <a href="https://github.com/AliXByte">AliXByte</a></strong>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:00d4ff,100:7b61ff&height=120&section=footer&animation=fadeIn" width="100%"/>
</p>
