# Changelog

## [1.0.0] — 2026-10-24
### Added
- Core ADB layer (`byteadb.core`): devices, files, apps, shell, logcat, screen, control, settings, wireless — each a thin, defensive wrapper over the real `adb` binary.
- Full `byteadb` CLI (Click) covering every core module, with consistent `--serial` device targeting and clear, styled errors (Rich).
- Interactive full-screen terminal dashboard (Textual): device picker, Overview, Files, Apps, Logcat, Shell tabs.
- Wireless debugging support: Android 11+ pairing-code flow and classic `adb tcpip` mode.
- Live screen mirroring via an optional `scrcpy` integration (disclosed, not bundled or reimplemented).
- 33 unit tests covering parsing and error-handling logic in the core layer.

### Notes
- V1 is intentionally CLI/TUI-only. A web panel is planned as a separate V2 product, not a mode of this one.
