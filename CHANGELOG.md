# Changelog

## [1.0.0] — 2026-10-24
### Added
- Core ADB layer (`byteadb.core`): devices, files, apps, shell, logcat, screen, control, settings, wireless — each a thin, defensive wrapper over the real `adb` binary.
- Full `byteadb` CLI (Click) covering every core module, with consistent `--serial` device targeting and clear, styled errors (Rich).
- Interactive full-screen terminal dashboard (Textual): device picker, Overview, Files, Apps, Logcat, Shell tabs.
- Interactive numbered main-menu dashboard (`byteadb` / `byteadb menu`) with 19 categories — the default entry point.
- Wireless debugging support: Android 11+ pairing-code flow and classic `adb tcpip` mode.
- Device Connection: list/select devices, stop/restart ADB server, disconnect all, connect directly by IP:port.
- Mirror, Control & Camera Live: screen mirror with mouse/keyboard control, live camera streaming (front/back) via scrcpy.
- Screen Capture: screenshot, screen recording.
- Audio Capture: live mic/device-audio streaming and recording via scrcpy, with optional raw/unprocessed mic mode (Android's `AudioSource.UNPROCESSED`) to bypass noise-suppression filtering.
- File Transfer: push/pull, one-step backup of WhatsApp media, camera photos, and screenshots.
- App Management: install/uninstall, split-APK install, APK extraction, force-stop, clear data, restart, grant/revoke permissions, enable/disable, suspend/unsuspend, battery-optimization whitelist, default home app — 21 sub-options.
- Device Information: full build/security info, accounts, SIM/operator, Bluetooth devices, battery dump, locale.
- Media & Links: open a URL, display a photo, play audio/video on the device, send an SMS (silent send for unattended devices), view/save the connected device's own SMS log.
- Network Tools: Wi-Fi status dump, WLAN IP info, Wi-Fi radio toggle, ping, saved/nearby Wi-Fi networks, local hotspot, TCP port forwarding (forward/reverse/list/remove), LAN scan to find your own ADB-enabled devices.
- Display & Sound: resolution/density/scaling presets, brightness, screen timeout, volume, Do Not Disturb, notification/quick-settings panel, clipboard, wallpaper, developer settings, stay-awake mode.
- Location & App Usage: last-known GPS location, app usage stats (day/week/all-time).
- Radios & Battery Mock: mobile data/Bluetooth/NFC/airplane-mode toggles, mock battery level/plugged state.
- Security Check: read-only root heuristics (su binaries, root-management apps, build tags).
- 33 unit tests covering parsing and error-handling logic in the core layer.

### Notes
- V1 is intentionally CLI/TUI-only. A web panel is planned as a separate V2 product, not a mode of this one.
- Plain `pip install -r requirements.txt` + `python3 byteadb.py` — no venv, no build step needed.
