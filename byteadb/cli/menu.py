"""
ByteADB · interactive numbered main menu

This is what most people mean by "the ByteADB dashboard": one banner, one
numbered menu, pick a number, do the thing, back to the menu — launched by
running `byteadb` with no arguments (or `byteadb menu` explicitly).

It is built entirely on the same byteadb.core modules the `byteadb <group>
<command>` subcommands use. Nothing here talks to adb directly, and nothing
here does anything adb (or scrcpy, which it discloses) couldn't already do
on an authorized, debugging-enabled device. Pure Python + Click + Rich, so
it runs the same way on Linux, macOS, and Windows.
"""
from __future__ import annotations

from byteadb import __version__
from byteadb.core import (adb, apps, communication, control, display, files,
                           location, logcat, media, network, radios, screen,
                           security, sms, sysinfo, system, usage, wireless)
from byteadb.core import settings as settings_core
from byteadb.core.adb import AdbDevice, AdbError, AdbNotFoundError
from byteadb.cli.console import console, error, new_table, ok, warn
from rich.panel import Panel

BANNER = r"""
██████╗ ██╗   ██╗████████╗███████╗ █████╗ ██████╗ ██████╗
██╔══██╗╚██╗ ██╔╝╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗
██████╔╝ ╚████╔╝    ██║   █████╗  ███████║██║  ██║██████╔╝
██╔══██╗  ╚██╔╝     ██║   ██╔══╝  ██╔══██║██║  ██║██╔══██╗
██████╔╝   ██║      ██║   ███████╗██║  ██║██████╔╝██████╔╝
╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═════╝ ╚═════╝
"""

# (number, label, border color for its submenu panel — purely cosmetic grouping)
MAIN_MENU = [
    ("1", "Device Connection", "bright_cyan"),
    ("2", "ADB & Wireless Debugging", "bright_cyan"),
    ("3", "Mirror, Control & Camera Live", "magenta"),
    ("4", "Screen Capture", "magenta"),
    ("5", "Audio Capture (mic / device)", "magenta"),
    ("6", "File Transfer", "green"),
    ("7", "App Management", "green"),
    ("8", "Device Shell", "bright_cyan"),
    ("9", "Logcat (Live / Save Snippet)", "bright_cyan"),
    ("10", "Input & Keyevents", "green"),
    ("11", "Settings (get / put / list)", "green"),
    ("12", "Power, Reboot & Lock", "red"),
    ("13", "Device Information", "yellow"),
    ("14", "Media & Links", "magenta"),
    ("15", "Network Tools", "blue"),
    ("16", "Display & Sound", "blue"),
    ("17", "Location & App Usage", "yellow"),
    ("18", "Radios & Battery Mock", "blue"),
    ("19", "Security & Lock Screen", "red"),
    ("20", "Communication (Call / Contacts / Calendar)", "yellow"),
    ("21", "System & Debug", "red"),
]


# --------------------------------------------------------------------------
# small input/output helpers shared by every submenu
# --------------------------------------------------------------------------

def ask_choice(label: str) -> str:
    return console.input(f"[bold red]{label}[/] > ").strip()


def ask(label: str, default: str = None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    val = console.input(f"[byteadb.key]{label}{suffix}:[/] ").strip()
    return val if val else (default or "")


def ask_yn(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    val = console.input(f"[byteadb.key]{label}{suffix}:[/] ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


def pause():
    console.input("\n[byteadb.dim]Press Enter to continue...[/]")


def clear_screen():
    console.clear()


def show_banner_and_status(device: AdbDevice | None):
    clear_screen()
    console.print(f"[byteadb.brand]{BANNER}[/]")
    console.print(f"   [byteadb.dim]v{__version__}  ·  by AliXByte  ·  github.com/AliXByte/ByteADB-V1[/]\n")
    if device:
        console.print(f"   [byteadb.ok]● Connected:[/] {device.serial}\n")
    else:
        console.print("   [byteadb.warn]○ No device selected[/]  — pick one from option 1\n")


def print_main_menu():
    mid = (len(MAIN_MENU) + 1) // 2
    left, right = MAIN_MENU[:mid], MAIN_MENU[mid:]
    for i in range(max(len(left), len(right))):
        line = ""
        if i < len(left):
            num, label, _ = left[i]
            line += f"  [byteadb.dim]{num:>2}.[/] [bright_green]{label}[/] [byteadb.dim]›[/]"
        if i < len(right):
            pad = max(2, 54 - len(left[i][1])) if i < len(left) else 0
            num, label, _ = right[i]
            line += " " * pad + f"[byteadb.dim]{num:>2}.[/] [bright_green]{label}[/] [byteadb.dim]›[/]"
        console.print(line)
    console.print("\n  [byteadb.dim]99.[/] Clear     [byteadb.dim] 0.[/] Exit")


def panel(title: str, device: AdbDevice | None = None, color: str = "bright_cyan"):
    text = f"{title} — {device.serial}" if device else title
    console.print(Panel.fit(text, border_style=color))


def ensure_device(device: AdbDevice | None) -> AdbDevice | None:
    """Reuse an already-selected device, or auto-pick the one attached
    device. With zero or several attached, sends the user to Device
    Connection instead of guessing."""
    if device is not None:
        return device
    try:
        devices = adb.list_devices()
    except AdbNotFoundError as e:
        error(str(e))
        return None
    ready = [d for d in devices if d.state == "device"]
    if len(ready) == 1:
        return AdbDevice(ready[0].serial)
    if not ready:
        warn("No ready device. Open 'Device Connection' (option 1) first.")
        return None
    warn("Multiple devices attached. Open 'Device Connection' (option 1) to pick one.")
    return None


def _run(fn, *a, **kw):
    """Call fn(*a, **kw), report ok()/error() uniformly, always pause after."""
    try:
        fn(*a, **kw)
        ok("Done.")
    except Exception as e:
        error(str(e))
    finally:
        pause()


def _print_dict_table(d: dict):
    table = new_table("Field", "Value")
    for k, v in d.items():
        table.add_row(str(k), str(v) if v not in (None, "") else "—")
    console.print(table)


def _print_list(items: list[str], empty_msg: str = "Nothing found."):
    if not items:
        warn(empty_msg)
        return
    for it in items:
        console.print(f"  {it}")
    console.print(f"\n[byteadb.dim]{len(items)} item(s).[/]")


def _wait_proc(proc):
    """Wait for a subprocess, handle Ctrl+C gracefully."""
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


# --------------------------------------------------------------------------
# 1. Device Connection
# --------------------------------------------------------------------------

def handle_device_connection(current: AdbDevice | None) -> AdbDevice | None:
    while True:
        clear_screen()
        panel("Device Connection")
        try:
            devices = adb.list_devices()
        except AdbNotFoundError as e:
            error(str(e))
            pause()
            return current
        if not devices:
            warn("No devices found. Plug one in with USB debugging enabled, "
                 "or pair one wirelessly from the main menu's option 2.")
        else:
            table = new_table("#", "Serial", "State", "Model", "Transport")
            for i, d in enumerate(devices, 1):
                table.add_row(str(i), d.serial, d.state, d.model or "—", d.transport or "—")
            console.print(table)
        console.print("\n  r. Refresh     s. Stop ADB server     x. Restart ADB server")
        console.print("  d. Disconnect all wireless devices     c. Connect by IP:port")
        console.print("  0. Back")
        choice = ask_choice("[Device Connection]")
        if choice == "0":
            return current
        if choice.lower() == "r":
            continue
        if choice.lower() == "s":
            _run(adb.kill_server)
            continue
        if choice.lower() == "x":
            _run(adb.restart_server)
            continue
        if choice.lower() == "d":
            _run(adb.disconnect)
            continue
        if choice.lower() == "c":
            ip = ask("Device IP address")
            port = ask("Port", default="5555")
            try:
                result = adb.connect(f"{ip}:{port}")
                if 'connected' not in result.lower():
                    error(result or "connect failed")
                    pause()
                    continue
                ok(result)
                pause()
                return AdbDevice(f"{ip}:{port}")
            except Exception as e:
                error(str(e))
                pause()
            continue
        try:
            d = devices[int(choice) - 1]
        except (ValueError, IndexError):
            warn("Invalid selection.")
            pause()
            continue
        if d.state != "device":
            error(f"Device '{d.serial}' is '{d.state}', not ready. "
                  f"{'Check the phone screen for an authorization prompt.' if d.state == 'unauthorized' else ''}")
            pause()
            continue
        ok(f"Selected {d.serial} ({d.model or 'unknown model'})")
        pause()
        return AdbDevice(d.serial)


# --------------------------------------------------------------------------
# 2. ADB & Wireless Debugging
# --------------------------------------------------------------------------

def handle_wireless():
    while True:
        clear_screen()
        panel("ADB & Wireless Debugging")
        console.print("  1. Pair device (Android 11+ pairing code)")
        console.print("  2. Connect to ip:port")
        console.print("  3. Disconnect one / all")
        console.print("  4. Enable TCP/IP mode on a USB-connected device")
        console.print("  0. Back")
        choice = ask_choice("[Wireless]")
        if choice == "0":
            return
        try:
            if choice == "1":
                host_port = ask("Pairing ip:port (shown on phone)")
                code = ask("6-digit pairing code")
                connect_hp = ask("Wireless debugging ip:port to connect after pairing")
                ok(wireless.pair_and_connect(host_port, code, connect_hp))
            elif choice == "2":
                ok(adb.connect(ask("ip:port")))
            elif choice == "3":
                hp = ask("ip:port (blank = disconnect all)")
                ok(adb.disconnect(hp or None))
            elif choice == "4":
                dev = ensure_device(None)
                if not dev:
                    pause()
                    continue
                port = ask("Port", default="5555")
                wireless.enable_tcpip_mode(dev, int(port))
                ip = wireless.device_wifi_ip(dev)
                ok(f"TCP/IP mode enabled on port {port}.")
                if ip:
                    console.print(f"  Device Wi-Fi IP: {ip} — now connect with option 2 using {ip}:{port}")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 3. Mirror, Control & Camera Live
# --------------------------------------------------------------------------

def _ask_mirror_quality() -> dict:
    """Ask user to pick a mirror quality preset or custom values."""
    console.print("\n  [bold]Quality preset:[/]")
    console.print("  1. Fast  [byteadb.dim](640px, 2 Mbps, 30 fps — low latency)[/]")
    console.print("  2. Balanced  [byteadb.dim](1024px, 8 Mbps, 60 fps — default)[/]")
    console.print("  3. High Quality  [byteadb.dim](native res, 20 Mbps, 60 fps — best image)[/]")
    console.print("  4. Custom  [byteadb.dim](set your own resolution/bitrate/fps)[/]")
    qc = ask("Quality", default="2")
    if qc == "1":
        return {'preset': 'fast'}
    elif qc == "3":
        return {'preset': 'hq'}
    elif qc == "4":
        ms = ask("Max size in px (0 = native)", default="0")
        br = ask("Video bit rate (e.g. 8M, 20M)", default="8M")
        fps = ask("Max FPS (0 = unlimited)", default="60")
        return {'max_size': int(ms), 'bit_rate': br, 'max_fps': int(fps)}
    return {'preset': 'balanced'}


def _ask_audio_source() -> str:
    """Ask user which audio source to use for mirroring."""
    console.print("\n  [bold]Audio source:[/]")
    console.print("  1. No audio  [byteadb.dim](lowest latency)[/]")
    console.print("  2. Device audio  [byteadb.dim](music, apps, internal playback)[/]")
    console.print("  3. Microphone  [byteadb.dim](ambient/environment sound)[/]")
    console.print("  4. Microphone (raw)  [byteadb.dim](no noise/AGC filtering)[/]")
    ac = ask("Audio", default="1")
    return {"1": "none", "2": "device", "3": "mic", "4": "mic-raw"}.get(ac, "none")


def handle_mirror(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Mirror, Control & Camera Live", device, "magenta")
        console.print("  [bold bright_green]── Screen Mirror ──[/]")
        console.print("  1. Mirror + control  [byteadb.dim](choose audio & quality)[/]")
        console.print("  2. Mirror view-only  [byteadb.dim](watch screen, no mouse/keyboard input)[/]")
        console.print("  3. Mirror + record  [byteadb.dim](mirror and save recording to file)[/]")
        console.print()
        console.print("  [bold bright_green]── Advanced scrcpy ──[/]")
        console.print("  4. OTG mode  [byteadb.dim](forward USB mouse/keyboard without screen mirror)[/]")
        console.print("  5. Virtual display  [byteadb.dim](separate display, doesn't affect phone screen)[/]")
        console.print()
        console.print("  [bold bright_green]── Camera ──[/]")
        console.print("  6. Live camera — back  [byteadb.dim](stream rear camera to your screen)[/]")
        console.print("  7. Live camera — front  [byteadb.dim](stream front/selfie camera)[/]")
        console.print("  8. Record camera — back  [byteadb.dim](record rear camera to file)[/]")
        console.print("  9. Record camera — front  [byteadb.dim](record front camera to file)[/]")
        console.print()
        console.print("  [byteadb.dim]All mirror/camera features use scrcpy (must be installed).[/]")
        console.print("  0. Back")
        choice = ask_choice("[Mirror]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                audio = _ask_audio_source()
                quality = _ask_mirror_quality()
                preset = quality.pop('preset', 'balanced')
                ok("Launching mirror — close window or Ctrl+C to stop.")
                proc = screen.mirror(device.serial, audio=audio, preset=preset, **quality)
                _wait_proc(proc)
            elif choice == "2":
                audio = _ask_audio_source()
                ok("Launching view-only mirror — no mouse/keyboard control.")
                proc = screen.mirror_view_only(device.serial, audio=audio)
                _wait_proc(proc)
            elif choice == "3":
                audio = _ask_audio_source()
                quality = _ask_mirror_quality()
                preset = quality.pop('preset', 'balanced')
                local = ask("Save recording as", default="mirror_record.mp4")
                ok("Mirroring + recording — close window or Ctrl+C to stop.")
                proc = screen.mirror_record(device.serial, local, audio=audio,
                                            preset=preset, **quality)
                _wait_proc(proc)
                ok(f"Recording saved to {local}")
            elif choice == "4":
                ok("Launching OTG mode — your mouse/keyboard controls the phone.")
                proc = screen.otg_mode(device.serial)
                _wait_proc(proc)
            elif choice == "5":
                res = ask("Resolution (WxH)", default="1920x1080")
                dpi = ask("DPI", default="240")
                audio = _ask_audio_source()
                ok("Creating virtual display on device...")
                proc = screen.virtual_display(device.serial, resolution=res,
                                              dpi=int(dpi), audio=audio)
                _wait_proc(proc)
            elif choice == "6":
                ok("Launching back-camera live view...")
                proc = screen.camera_stream(device.serial, facing="back")
                _wait_proc(proc)
            elif choice == "7":
                ok("Launching front-camera live view...")
                proc = screen.camera_stream(device.serial, facing="front")
                _wait_proc(proc)
            elif choice == "8":
                local = ask("Save recording as", default="camera_back.mp4")
                ok("Recording back camera — close window or Ctrl+C to stop.")
                proc = screen.camera_record(device.serial, local, facing="back")
                _wait_proc(proc)
                ok(f"Saved to {local}")
            elif choice == "9":
                local = ask("Save recording as", default="camera_front.mp4")
                ok("Recording front camera — close window or Ctrl+C to stop.")
                proc = screen.camera_record(device.serial, local, facing="front")
                _wait_proc(proc)
                ok(f"Saved to {local}")
            else:
                warn("Invalid option.")
                pause()
                continue
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 4. Screen Capture
# --------------------------------------------------------------------------

def handle_screen(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Screen Capture", device, "magenta")
        console.print("  1. Screenshot  [byteadb.dim](PNG — default, lossless)[/]")
        console.print("  2. Screenshot as JPEG  [byteadb.dim](smaller file, lossy)[/]")
        console.print("  3. Screenshot as WebP  [byteadb.dim](smallest file, modern format)[/]")
        console.print("  4. Screen record  [byteadb.dim](time-limited video recording)[/]")
        console.print("  5. Screen record (custom quality)  [byteadb.dim](choose bitrate & resolution)[/]")
        console.print("  [byteadb.dim]Both remove their temp file from the device after pulling it.[/]")
        console.print("  0. Back")
        choice = ask_choice("[Screen]")
        if choice == "0":
            return device
        try:
            if choice in ("1", "2", "3"):
                fmt_map = {"1": "png", "2": "jpeg", "3": "webp"}
                fmt = fmt_map[choice]
                path = ask("Save screenshot as", default=f"screenshot.{fmt}")
                screen.screenshot(device, path, fmt=fmt)
                ok(f"Saved to {path}")
            elif choice in ("4", "5"):
                seconds = ask("Time limit in seconds (max 180)", default="30")
                local = ask("Save recording as", default="screenrecord.mp4")
                kw = {}
                if choice == "5":
                    console.print("  [bold]Quality:[/]")
                    console.print("  1. Fast (2 Mbps)  2. Balanced (8 Mbps)  3. High (20 Mbps)  4. Custom")
                    qc = ask("Quality", default="2")
                    br_map = {"1": 2, "2": 8, "3": 20}
                    if qc in br_map:
                        kw['bit_rate_mbps'] = br_map[qc]
                    elif qc == "4":
                        kw['bit_rate_mbps'] = int(ask("Bitrate in Mbps", default="8"))
                        kw['size'] = ask("Size WxH (blank = native)", default="")
                proc, remote_path = screen.start_screenrecord(
                    device, time_limit_sec=int(seconds), **kw)
                console.print("[byteadb.dim]Recording... Ctrl+C to stop early.[/]")
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    proc.terminate()
                    proc.wait()
                device.pull(remote_path, local)
                device.shell(f"rm -f '{remote_path}'")
                ok(f"Saved to {local}")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 5. Audio Capture (mic / device audio)
# --------------------------------------------------------------------------

def handle_audio(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Audio Capture", device, "magenta")
        console.print("  [byteadb.dim]Needs scrcpy 2.0+ and Android 11+ on the device (audio forwarding).[/]\n")
        console.print("  1. Stream microphone (live)  [byteadb.dim](hear device mic on your computer)[/]")
        console.print("  2. Stream device/playback audio (live)  [byteadb.dim](internal sound, music, apps)[/]")
        console.print("  3. Record microphone to a file  [byteadb.dim](save ambient audio)[/]")
        console.print("  4. Record device/playback audio to a file  [byteadb.dim](save internal audio)[/]")
        console.print("  [byteadb.dim]Mic options 1 & 3 ask standard vs. unprocessed (raw, no noise/AGC filtering).[/]")
        console.print("  0. Back")
        choice = ask_choice("[Audio]")
        if choice == "0":
            return device
        try:
            proc = None
            if choice == "1":
                mode = "unprocessed" if ask_yn("Use raw mic (no noise/AGC filtering)?",
                                                default=False) else "standard"
                proc = screen.mic_stream(device.serial, mode=mode)
            elif choice == "2":
                proc = screen.device_audio_stream(device.serial)
            elif choice == "3":
                local = ask("Save recording as", default="mic.mp4")
                mode = "unprocessed" if ask_yn("Use raw mic (no noise/AGC filtering)?",
                                                default=False) else "standard"
                proc = screen.mic_record(device.serial, local, mode=mode)
            elif choice == "4":
                local = ask("Save recording as", default="device_audio.mp4")
                proc = screen.device_audio_record(device.serial, local)
            else:
                warn("Invalid option.")
                pause()
                continue
            console.print("[byteadb.dim]Running... Ctrl+C to stop.[/]")
            _wait_proc(proc)
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 6. File Transfer
# --------------------------------------------------------------------------

def handle_files(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    path = "/sdcard"
    entries = []
    while True:
        clear_screen()
        panel("File Transfer", device, "green")
        console.print(f"[byteadb.dim]Path: {path}[/]\n")
        try:
            entries = files.list_dir(device, path)
            table = new_table("#", "Name", "Type", "Size", "Perms")
            for i, e in enumerate(entries, 1):
                table.add_row(str(i), e.name, "dir" if e.is_dir else "file",
                              files.human_size(e.size), e.permissions)
            console.print(table)
        except Exception as e:
            error(str(e))
            entries = []
        console.print("\n  o. Open item #    u. Up one level    g. Go to path")
        console.print("  m. Mkdir          r. Remove item #    v. Move/rename item #")
        console.print("  p. Push local file here    l. Pull item # to local")
        console.print("  w. Copy all WhatsApp media    c. Copy all camera photos    s. Copy all screenshots")
        console.print("  0. Back")
        choice = ask_choice("[Files]")
        if choice == "0":
            return device
        try:
            if choice == "u":
                path = path.rsplit("/", 1)[0] or "/"
            elif choice == "g":
                path = ask("Go to path", default=path)
            elif choice == "m":
                name = ask("New folder name")
                files.mkdir(device, f"{path.rstrip('/')}/{name}")
                ok("Created.")
                pause()
            elif choice == "p":
                local = ask("Local file path to push")
                name = ask("Remote filename", default=local.rsplit("/", 1)[-1])
                files.push_file(device, local, f"{path.rstrip('/')}/{name}")
                ok("Pushed.")
                pause()
            elif choice == "o":
                e = entries[int(ask("Item #")) - 1]
                if e.is_dir:
                    path = e.path
                else:
                    warn("Not a directory.")
                    pause()
            elif choice == "r":
                e = entries[int(ask("Item # to remove")) - 1]
                files.remove(device, e.path, recursive=e.is_dir)
                ok("Removed.")
                pause()
            elif choice == "v":
                e = entries[int(ask("Item # to move/rename")) - 1]
                dst = ask("New path/name", default=e.path)
                files.move(device, e.path, dst)
                ok("Moved.")
                pause()
            elif choice == "l":
                e = entries[int(ask("Item # to pull")) - 1]
                local = ask("Save as", default=e.name)
                files.pull_file(device, e.path, local)
                ok(f"Saved to {local}")
                pause()
            elif choice == "w":
                local_dir = ask("Save WhatsApp media into local folder", default="whatsapp_backup")
                remote = files.WELL_KNOWN_PATHS['whatsapp']
                if not files.exists(device, remote):
                    remote = files.WELL_KNOWN_PATHS['whatsapp_legacy']
                files.pull_dir(device, remote, local_dir)
                ok(f"Copied to {local_dir}")
                pause()
            elif choice == "c":
                local_dir = ask("Save camera photos into local folder", default="camera_backup")
                files.pull_dir(device, files.WELL_KNOWN_PATHS['camera'], local_dir)
                ok(f"Copied to {local_dir}")
                pause()
            elif choice == "s":
                local_dir = ask("Save screenshots into local folder", default="screenshots_backup")
                files.pull_dir(device, files.WELL_KNOWN_PATHS['screenshots'], local_dir)
                ok(f"Copied to {local_dir}")
                pause()
            else:
                warn("Invalid option.")
                pause()
        except (ValueError, IndexError):
            warn("Invalid selection.")
            pause()
        except Exception as e:
            error(str(e))
            pause()


# --------------------------------------------------------------------------
# 7. App Management
# --------------------------------------------------------------------------

def handle_apps(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("App Management", device, "green")
        console.print("  [bold bright_green]── List & Info ──[/]")
        console.print("   1. List user apps           2. List system apps          3. App info")
        console.print("  [bold bright_green]── Install / Uninstall ──[/]")
        console.print("   4. Install APK              5. Install split APKs        6. Extract APK")
        console.print("   7. Uninstall")
        console.print("  [bold bright_green]── Control ──[/]")
        console.print("   8. Clear data               9. Force-stop               10. Restart")
        console.print("  11. Enable                  12. Disable                  13. Suspend")
        console.print("  14. Unsuspend               15. Launch")
        console.print("  [bold bright_green]── Permissions ──[/]")
        console.print("  16. Grant one permission  [byteadb.dim](grant a specific runtime permission)[/]")
        console.print("  17. Revoke one permission  [byteadb.dim](revoke a specific runtime permission)[/]")
        console.print("  18. List all permissions  [byteadb.dim](show granted & denied for a package)[/]")
        console.print("  19. Grant ALL permissions  [byteadb.dim](batch-grant all denied permissions)[/]")
        console.print("  20. Revoke ALL permissions  [byteadb.dim](batch-revoke all granted permissions)[/]")
        console.print("  [bold bright_green]── Intents & Deep Links ──[/]")
        console.print("  21. Send custom intent  [byteadb.dim](activity/broadcast/service with extras)[/]")
        console.print("  22. Open deep link  [byteadb.dim](test a URI/deep link on the device)[/]")
        console.print("  23. Enable/disable component  [byteadb.dim](toggle a specific app component)[/]")
        console.print("  [bold bright_green]── Backup & Misc ──[/]")
        console.print("  24. Backup app + data  [byteadb.dim](save to .ab backup file)[/]")
        console.print("  25. Restore from backup  [byteadb.dim](restore a .ab backup file)[/]")
        console.print("  26. List Downloads  [byteadb.dim](show files in /sdcard/Download/)[/]")
        console.print("  27. Battery optimization  [byteadb.dim](whitelist/un-whitelist an app)[/]")
        console.print("  28. Battery-opt whitelist  [byteadb.dim](show all whitelisted apps)[/]")
        console.print("  29. Set default home app   30. Show current home app")
        console.print("   0. Back")
        choice = ask_choice("[Apps]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                _print_list(apps.list_packages(device, user_only=True))
            elif choice == "2":
                _print_list(apps.list_packages(device, system_only=True))
            elif choice == "3":
                info = apps.app_info(device, ask("Package name"))
                table = new_table("Field", "Value")
                table.add_row("Package", info.package)
                table.add_row("Version", f"{info.version_name or '—'} ({info.version_code or '—'})")
                table.add_row("System app", str(info.is_system))
                table.add_row("APK path", info.apk_path or "—")
                table.add_row("Permissions", str(len(info.permissions)))
                console.print(table)
            elif choice == "4":
                ok(apps.install_apk(device, ask("Local APK path")))
            elif choice == "5":
                paths = ask("Local APK paths, comma-separated").split(",")
                ok(apps.install_split_apks(device, [p.strip() for p in paths if p.strip()]))
            elif choice == "6":
                pkg = ask("Package name")
                out_dir = ask("Save into local folder", default=f"{pkg}_apk")
                saved = apps.extract_apk(device, pkg, out_dir)
                ok(f"Saved {len(saved)} file(s) to {out_dir}")
            elif choice == "7":
                ok(apps.uninstall_package(device, ask("Package name")))
            elif choice == "8":
                pkg = ask("Package name")
                ok("Cleared." if apps.clear_data(device, pkg) else "Failed.")
            elif choice == "9":
                apps.force_stop(device, ask("Package name"))
                ok("Stopped.")
            elif choice == "10":
                apps.restart(device, ask("Package name"))
                ok("Restarted.")
            elif choice == "11":
                apps.set_enabled(device, ask("Package name"), True)
                ok("Enabled.")
            elif choice == "12":
                apps.set_enabled(device, ask("Package name"), False)
                ok("Disabled.")
            elif choice == "13":
                apps.suspend(device, ask("Package name"))
                ok("Suspended.")
            elif choice == "14":
                apps.unsuspend(device, ask("Package name"))
                ok("Unsuspended.")
            elif choice == "15":
                apps.launch(device, ask("Package name"))
                ok("Launched.")
            elif choice == "16":
                pkg = ask("Package name")
                perm = ask("Permission (android.permission.X)")
                apps.grant_permission(device, pkg, perm)
                ok("Granted.")
            elif choice == "17":
                pkg = ask("Package name")
                perm = ask("Permission (android.permission.X)")
                apps.revoke_permission(device, pkg, perm)
                ok("Revoked.")
            elif choice == "18":
                pkg = ask("Package name")
                perms = apps.list_permissions(device, pkg)
                console.print(f"\n  [byteadb.ok]Granted ({len(perms['granted'])}):[/]")
                for p in perms['granted']:
                    console.print(f"    ✓ {p}")
                console.print(f"\n  [byteadb.warn]Denied ({len(perms['denied'])}):[/]")
                for p in perms['denied']:
                    console.print(f"    ✗ {p}")
            elif choice == "19":
                pkg = ask("Package name")
                ok(apps.grant_all_permissions(device, pkg))
            elif choice == "20":
                pkg = ask("Package name")
                ok(apps.revoke_all_permissions(device, pkg))
            elif choice == "21":
                action = ask("Intent action (e.g. android.intent.action.VIEW)")
                data = ask("Data URI (blank = none)")
                pkg = ask("Target package (blank = any)")
                component = ask("Component class (blank = none)")
                itype = ask("Type: activity / broadcast / service", default="activity")
                result = apps.send_intent(device, action, data=data,
                                          package=pkg, component=component,
                                          intent_type=itype)
                ok(result)
            elif choice == "22":
                uri = ask("Deep link URI (e.g. myapp://screen/123)")
                ok(apps.open_deep_link(device, uri))
            elif choice == "23":
                comp = ask("Component (package/class, e.g. com.app/.Receiver)")
                enable = ask_yn("Enable? (no = disable)", default=True)
                ok(apps.set_component_enabled(device, comp, enable))
            elif choice == "24":
                pkg = ask("Package name")
                local = ask("Save backup as", default=f"{pkg}.ab")
                ok(apps.backup_app(device, pkg, local))
            elif choice == "25":
                local = ask("Backup file path (.ab)")
                ok(apps.restore_backup(device, local))
            elif choice == "26":
                console.print(apps.list_downloads(device))
            elif choice == "27":
                pkg = ask("Package name")
                whitelist = ask_yn("Add to whitelist (ignore battery optimization)?", default=True)
                apps.ignore_battery_optimization(device, pkg, whitelist)
                ok("Updated.")
            elif choice == "28":
                _print_list(apps.battery_optimization_whitelist(device))
            elif choice == "29":
                component = ask("Launcher component (e.g. com.android.launcher3/.Launcher)")
                apps.set_default_home(device, component)
                ok("Default home app set.")
            elif choice == "30":
                console.print(apps.current_home(device) or "—")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 8. Device Shell
# --------------------------------------------------------------------------

def handle_shell(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    clear_screen()
    panel("Device Shell  (type 'exit' to return)", device)
    while True:
        cmd = console.input(f"[byteadb.key]{device.serial}:$[/] ")
        if cmd.strip() in ("exit", "quit", "back"):
            return device
        if not cmd.strip():
            continue
        try:
            console.print(device.shell(cmd, timeout=30))
        except AdbError as e:
            error(str(e))


# --------------------------------------------------------------------------
# 9. Logcat
# --------------------------------------------------------------------------

def handle_logcat(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Logcat", device)
        console.print("  1. Tail (live)  [byteadb.dim](stream log output in real time)[/]")
        console.print("  2. Save a snippet to a file (N seconds)  [byteadb.dim](capture log for analysis)[/]")
        console.print("  3. Clear log buffer  [byteadb.dim](wipe all existing log entries)[/]")
        console.print("  0. Back")
        choice = ask_choice("[Logcat]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                level = ask("Level filter (V/D/I/W/E/F, blank = all)")
                tag = ask("Tag filter (blank = none)")
                console.print("[byteadb.dim]Streaming... Ctrl+C to stop.[/]")
                try:
                    for line in logcat.stream(device.serial, level=level or None, tag_filter=tag or None):
                        console.print(line)
                except KeyboardInterrupt:
                    pass
            elif choice == "2":
                import time as _time
                seconds = int(ask("Capture for how many seconds", default="10"))
                local = ask("Save as", default="logcat_snippet.txt")
                level = ask("Level filter (V/D/I/W/E/F, blank = all)")
                lines = []
                start = _time.time()
                for line in logcat.stream(device.serial, level=level or None):
                    lines.append(line)
                    if _time.time() - start >= seconds:
                        break
                with open(local, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                ok(f"Saved {len(lines)} line(s) to {local}")
            elif choice == "3":
                logcat.clear(device.serial)
                ok("Cleared.")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 10. Input & Keyevents
# --------------------------------------------------------------------------

def handle_input(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Input & Keyevents", device, "green")
        console.print("  [bold bright_green]── Basic Input ──[/]")
        console.print("  1. Tap x,y  [byteadb.dim](single touch at coordinates)[/]")
        console.print("  2. Swipe  [byteadb.dim](drag from x1,y1 to x2,y2)[/]")
        console.print("  3. Type text  [byteadb.dim](inject text as if typed on keyboard)[/]")
        console.print("  4. Keyevent  [byteadb.dim](send a named key like home, back, power)[/]")
        console.print("  [bold bright_green]── Advanced Input ──[/]")
        console.print("  5. Long press  [byteadb.dim](hold touch at x,y for N milliseconds)[/]")
        console.print("  6. Pinch (zoom out)  [byteadb.dim](simulate two-finger pinch)[/]")
        console.print("  7. Spread (zoom in)  [byteadb.dim](simulate two-finger spread)[/]")
        console.print("  [bold bright_green]── Shortcuts ──[/]")
        console.print("  8. Open URL  [byteadb.dim](open a link in the device's default browser)[/]")
        console.print("  9. Open settings page  [byteadb.dim](jump to a specific settings section)[/]")
        console.print()
        console.print(f"  [byteadb.dim]Known keyevents: {', '.join(sorted(control.KEYEVENTS))}[/]")
        console.print("  0. Back")
        choice = ask_choice("[Input]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                control.tap(device, int(ask("x")), int(ask("y")))
                ok("Tapped.")
            elif choice == "2":
                control.swipe(device, int(ask("x1")), int(ask("y1")),
                              int(ask("x2")), int(ask("y2")))
                ok("Swiped.")
            elif choice == "3":
                control.text(device, ask("Text to type"))
                ok("Typed.")
            elif choice == "4":
                control.keyevent(device, ask("Keyevent name"))
                ok("Sent.")
            elif choice == "5":
                x, y = int(ask("x")), int(ask("y"))
                dur = int(ask("Duration in ms", default="1000"))
                control.long_press(device, x, y, dur)
                ok("Long pressed.")
            elif choice == "6":
                cx, cy = int(ask("Center x")), int(ask("Center y"))
                control.pinch(device, cx, cy)
                ok("Pinch gesture sent.")
            elif choice == "7":
                cx, cy = int(ask("Center x")), int(ask("Center y"))
                control.spread(device, cx, cy)
                ok("Spread gesture sent.")
            elif choice == "8":
                control.open_url(device, ask("URL"))
                ok("Opened.")
            elif choice == "9":
                console.print("  [byteadb.dim]Sections: wifi, bluetooth, display, sound, battery, "
                              "storage, apps, security, location, accessibility, date, language, "
                              "developer, about, accounts, nfc, hotspot, vpn, data_usage, notifications[/]")
                section = ask("Settings section (blank = main)")
                ok(control.open_settings(device, section))
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 11. Settings
# --------------------------------------------------------------------------

def handle_settings(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Settings", device, "green")
        console.print("  1. Get value    2. Put value    3. Delete value    4. List namespace    0. Back")
        choice = ask_choice("[Settings]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                ns = ask("Namespace (system/secure/global)", default="system")
                console.print(settings_core.get(device, ns, ask("Key")))
            elif choice == "2":
                ns = ask("Namespace (system/secure/global)", default="system")
                key = ask("Key")
                settings_core.put(device, ns, key, ask("Value"))
                ok("Updated.")
            elif choice == "3":
                ns = ask("Namespace (system/secure/global)", default="system")
                settings_core.delete(device, ns, ask("Key"))
                ok("Deleted.")
            elif choice == "4":
                ns = ask("Namespace (system/secure/global)", default="system")
                for k, v in settings_core.list_all(device, ns).items():
                    console.print(f"  {k} = {v}")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 12. Power, Reboot & Lock
# --------------------------------------------------------------------------

def handle_power(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Power, Reboot & Lock", device, "red")
        console.print("  1. Reboot (normal)        2. Reboot to recovery     3. Reboot to bootloader")
        console.print("  4. Reboot to sideload      5. Power off")
        console.print("  6. Lock")
        console.print("  0. Back")
        choice = ask_choice("[Power]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                control.reboot(device)
                ok("Rebooting...")
                pause()
                return device
            elif choice == "2":
                control.reboot(device, "recovery")
                ok("Rebooting to recovery...")
                pause()
                return device
            elif choice == "3":
                control.reboot(device, "bootloader")
                ok("Rebooting to bootloader...")
                pause()
                return device
            elif choice == "4":
                control.reboot(device, "sideload")
                ok("Rebooting to sideload...")
                pause()
                return device
            elif choice == "5":
                control.power_off(device)
                ok("Powering off...")
                pause()
                return device
            elif choice == "6":
                control.lock(device)
                ok("Locked.")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 13. Device Information
# --------------------------------------------------------------------------

def handle_info(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Device Information", device, "yellow")
        console.print("  1. Quick info  [byteadb.dim](model, Android version, battery)[/]")
        console.print("  2. Full device info  [byteadb.dim](chipset, patch level, encryption, IMEI, Android ID)[/]")
        console.print("  3. Accounts on device  [byteadb.dim](Google/Samsung/etc accounts, bypasses OEM censoring)[/]")
        console.print("  4. SIM / operator info  [byteadb.dim](carrier, IMSI, SIM state)[/]")
        console.print("  5. Bluetooth devices  [byteadb.dim](paired Bluetooth devices)[/]")
        console.print("  6. Full battery dump  [byteadb.dim](detailed battery stats)[/]")
        console.print("  7. Locale & timezone  [byteadb.dim](language, region, time zone)[/]")
        console.print("  8. Active notifications  [byteadb.dim](currently showing notifications)[/]")
        console.print("  0. Back")
        choice = ask_choice("[Info]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                _print_dict_table(device.info())
            elif choice == "2":
                _print_dict_table(sysinfo.full_device_info(device))
            elif choice == "3":
                accts = sysinfo.accounts(device)
                if not accts:
                    warn("No accounts found (or not readable from this shell).")
                for a in accts:
                    console.print(f"  {a['name']}  [byteadb.dim]({a['type']})[/]")
            elif choice == "4":
                _print_dict_table(sysinfo.sim_info(device))
            elif choice == "5":
                devs = sysinfo.bluetooth_devices(device)
                if not devs:
                    warn("No Bluetooth devices found.")
                for bt in devs:
                    console.print(f"  {bt['name']}  [byteadb.dim]{bt['address']}[/]")
            elif choice == "6":
                _print_dict_table(sysinfo.battery_full(device))
            elif choice == "7":
                _print_dict_table(sysinfo.locale_info(device))
            elif choice == "8":
                notifs = communication.active_notifications(device)
                if not notifs:
                    warn("No active notifications.")
                else:
                    table = new_table("#", "Package", "Title", "Text")
                    for i, n in enumerate(notifs, 1):
                        table.add_row(str(i), n.get('package', '—'),
                                      n.get('title', '—'), n.get('text', '—')[:60])
                    console.print(table)
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 14. Media & Links
# --------------------------------------------------------------------------

def handle_media(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Media & Links", device, "magenta")
        console.print("  1. Open a URL on the device  [byteadb.dim](opens in default browser)[/]")
        console.print("  2. Display a photo  [byteadb.dim](push & open an image on the device)[/]")
        console.print("  3. Play an audio file  [byteadb.dim](push & play audio on the device)[/]")
        console.print("  4. Play a video file  [byteadb.dim](push & play video on the device)[/]")
        console.print("  5. Send an SMS  [byteadb.dim](silent send, no tap needed — for unattended devices)[/]")
        console.print("  6. View/save SMS log  [byteadb.dim](export sent + received messages to CSV)[/]")
        console.print("  0. Back")
        choice = ask_choice("[Media]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                media.open_url(device, ask("URL"))
                ok("Opened.")
            elif choice == "2":
                media.display_photo(device, ask("Local image path"))
                ok("Opened on device.")
            elif choice == "3":
                media.play_audio(device, ask("Local audio file path"))
                ok("Opened on device.")
            elif choice == "4":
                media.play_video(device, ask("Local video file path"))
                ok("Opened on device.")
            elif choice == "5":
                number = ask("Recipient number")
                text = ask("Message text")
                if sms.send_sms(device, number, text):
                    ok("Sent.")
                else:
                    error("Silent send isn't available on this device/Android version — "
                          "the shell user doesn't have access to the internal send API here.")
            elif choice == "6":
                import os
                from datetime import datetime
                default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))), "data")
                os.makedirs(default_dir, exist_ok=True)
                dev_model = (device.get_prop("ro.product.model") or "device").replace(" ", "_")
                date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                default_name = f"sms_log_{dev_model}_{date_str}.csv"
                default_path = os.path.join(default_dir, default_name)
                local = ask("Save as", default=default_path)
                if os.path.isdir(local):
                    local = os.path.join(local, default_name)
                os.makedirs(os.path.dirname(os.path.abspath(local)), exist_ok=True)
                entries = sms.sms_log(device)
                with open(local, "w", encoding="utf-8") as f:
                    f.write("direction,address,date,body\n")
                    for e in entries:
                        body = (e.body or "").replace('"', "'")
                        f.write(f'"{e.direction}","{e.address}","{e.date}","{body}"\n')
                ok(f"Saved {len(entries)} message(s) to {local}")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 15. Network Tools
# --------------------------------------------------------------------------

def handle_network(device: AdbDevice | None) -> AdbDevice | None:
    while True:
        clear_screen()
        panel("Network Tools", device, "blue")
        console.print("  [bold bright_green]── Wi-Fi ──[/]")
        console.print("   1. Wi-Fi status dump         2. WLAN IP info            3. Wi-Fi radio on/off")
        console.print("   4. Ping a host                5. Saved Wi-Fi networks    6. Nearby Wi-Fi scan")
        console.print("   7. Start local hotspot        8. Stop local hotspot")
        console.print("  15. Connect to a Wi-Fi network  [byteadb.dim](by SSID + password)[/]")
        console.print("  16. Scan & connect to Wi-Fi  [byteadb.dim](pick from scan results)[/]")
        console.print("  [bold bright_green]── Port Forwarding ──[/]")
        console.print("   9. Port forward  [byteadb.dim](PC port → device port)[/]")
        console.print("  10. Port reverse  [byteadb.dim](device port → PC port)[/]")
        console.print("  11. List forwards             12. Remove a forward        13. Remove all forwards")
        console.print("  [bold bright_green]── Proxy / DNS / VPN ──[/]")
        console.print("  17. Set HTTP proxy  [byteadb.dim](route device traffic through a proxy)[/]")
        console.print("  18. Show current proxy        19. Clear proxy")
        console.print("  20. Show DNS settings  [byteadb.dim](DNS servers and private DNS mode)[/]")
        console.print("  21. Set private DNS  [byteadb.dim](e.g. dns.google for DoT)[/]")
        console.print("  22. Auto private DNS          23. Disable private DNS")
        console.print("  24. VPN status  [byteadb.dim](check if a VPN is active)[/]")
        console.print("  [bold bright_green]── LAN ──[/]")
        console.print("  14. Scan my LAN for ADB devices  [byteadb.dim](find your phone's IP fast)[/]")
        console.print("   0. Back")
        choice = ask_choice("[Network]")
        if choice == "0":
            return device
        try:
            # Most options need a device
            if choice not in ("14",):
                device = ensure_device(device)
                if not device:
                    pause()
                    continue
            if choice == "1":
                console.print(network.wifi_dump(device))
            elif choice == "2":
                _print_dict_table(network.wlan_ip_info(device))
            elif choice == "3":
                network.wifi_radio(device, ask_yn("Enable Wi-Fi?", default=True))
                ok("Done.")
            elif choice == "4":
                host = ask("Host/IP to ping", default="8.8.8.8")
                console.print(network.ping(device, host))
            elif choice == "5":
                console.print(network.saved_wifi_networks(device))
            elif choice == "6":
                console.print(network.nearby_wifi_scan(device))
            elif choice == "7":
                network.hotspot(device, True)
                ok("Hotspot started (if supported on this device/Android version).")
            elif choice == "8":
                network.hotspot(device, False)
                ok("Hotspot stopped.")
            elif choice == "9":
                local = ask("Local port", default="8080")
                remote = ask("Remote port on device", default="8080")
                ok(network.port_forward(device, int(local), int(remote)))
            elif choice == "10":
                remote = ask("Remote port on device", default="8080")
                local = ask("Local port", default="8080")
                ok(network.port_reverse(device, int(remote), int(local)))
            elif choice == "11":
                console.print(network.list_forwards(device) or "No active forwards.")
            elif choice == "12":
                local = ask("Local port to remove (e.g. tcp:8080)")
                adb.forward_remove(device.serial, local)
                ok("Removed.")
            elif choice == "13":
                adb.forward_remove_all(device.serial)
                ok("Removed all forwards for this device.")
            elif choice == "14":
                guess = network.local_subnet_guess() or "192.168.1.0/24"
                subnet = ask("Subnet to scan (CIDR)", default=guess)
                console.print("[byteadb.dim]Scanning for devices with wireless-debugging ports open...[/]")
                found = network.discover_adb_hosts(subnet)
                if not found:
                    warn("Nothing found. If your phone's wireless debugging isn't on yet, "
                         "enable it from option 2 on the main menu first.")
                else:
                    for r in found:
                        console.print(f"  {r['ip']}:{r['port']}")
                    console.print(f"\n[byteadb.dim]{len(found)} open port(s) found. "
                                  f"Connect to one with main menu option 2.[/]")
            elif choice == "15":
                ssid = ask("Wi-Fi SSID (network name)")
                pw = ask("Password (leave blank for open network)", default="")
                result = network.wifi_connect(device, ssid, pw if pw else None)
                ok(result)
            elif choice == "16":
                console.print("[byteadb.dim]Scanning nearby Wi-Fi networks...[/]")
                nets = network.nearby_wifi_scan_parsed(device)
                if not nets:
                    warn("No Wi-Fi networks found (scan may need a moment, or Wi-Fi is off).")
                else:
                    table = new_table("#", "SSID", "Signal", "Security", "Freq")
                    for i, n in enumerate(nets, 1):
                        rssi = n['rssi']
                        if rssi >= -50:
                            sig = "████ Excellent"
                        elif rssi >= -60:
                            sig = "███░ Good"
                        elif rssi >= -70:
                            sig = "██░░ Fair"
                        else:
                            sig = "█░░░ Weak"
                        table.add_row(str(i), n['ssid'], f"{sig} ({rssi}dBm)",
                                      n['security'], n['freq'])
                    console.print(table)
                    pick = ask("Enter number to connect (0 = cancel)", default="0")
                    if pick != "0":
                        try:
                            idx = int(pick) - 1
                            if 0 <= idx < len(nets):
                                chosen = nets[idx]
                                pw = ""
                                if chosen['security'].upper() not in ('OPEN', '[ESS]', 'NONE', ''):
                                    pw = ask(f"Password for '{chosen['ssid']}'")
                                result = network.wifi_connect(device, chosen['ssid'],
                                                              pw if pw else None)
                                ok(result)
                            else:
                                warn("Invalid number.")
                        except ValueError:
                            warn("Invalid input.")
            elif choice == "17":
                host = ask("Proxy host (e.g. 192.168.1.100)")
                port = ask("Proxy port (e.g. 8888)")
                ok(network.set_proxy(device, host, int(port)))
            elif choice == "18":
                console.print(f"  Proxy: {network.get_proxy(device)}")
            elif choice == "19":
                ok(network.clear_proxy(device))
            elif choice == "20":
                _print_dict_table(network.get_dns(device))
            elif choice == "21":
                hostname = ask("Private DNS hostname (e.g. dns.google)")
                ok(network.set_private_dns(device, hostname))
            elif choice == "22":
                ok(network.auto_private_dns(device))
            elif choice == "23":
                ok(network.disable_private_dns(device))
            elif choice == "24":
                console.print(network.vpn_status(device))
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()
    return device


# --------------------------------------------------------------------------
# 16. Display & Sound
# --------------------------------------------------------------------------

def handle_display(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Display & Sound", device, "blue")
        console.print("  [bold bright_green]── Display ──[/]")
        console.print("   1. Show current display settings     2. Set resolution (preset or custom)")
        console.print("   3. Reset resolution                   4. Set density (preset or custom)")
        console.print("   5. Reset density                      6. Toggle display scaling")
        console.print("   7. Set brightness (0-255)              8. Set screen timeout (ms)")
        console.print("  [bold bright_green]── Sound ──[/]")
        console.print("   9. Set volume                         10. Set Do Not Disturb mode")
        console.print("  [bold bright_green]── Status Bar ──[/]")
        console.print("  11. Expand notifications                12. Collapse notifications")
        console.print("  13. Expand quick settings")
        console.print("  [bold bright_green]── Clipboard & Wallpaper ──[/]")
        console.print("  14. Clipboard: set text                 15. Clipboard: clear")
        console.print("  16. Set wallpaper")
        console.print("  [bold bright_green]── Audio Routing ──[/]")
        console.print("  17. Audio output routing  [byteadb.dim](speaker/AUX/Bluetooth)[/]")
        console.print("  18. Microphone input routing  [byteadb.dim](built-in/AUX/Bluetooth)[/]")
        console.print("  19. Reset audio routing  [byteadb.dim](back to automatic)[/]")
        console.print("  [bold bright_green]── UI Tweaks ──[/]")
        console.print("  20. Font size  [byteadb.dim](small/default/large/largest or custom scale)[/]")
        console.print("  21. Animation speed  [byteadb.dim](off/fast/normal/slow — affects all animations)[/]")
        console.print("  22. Force RTL layout  [byteadb.dim](right-to-left for testing localization)[/]")
        console.print("  23. Dark mode  [byteadb.dim](on/off/auto — system-wide dark theme)[/]")
        console.print("  24. Immersive mode  [byteadb.dim](hide nav bar, status bar, or both)[/]")
        console.print("  25. Color inversion  [byteadb.dim](invert all colors on screen)[/]")
        console.print("  26. Color correction  [byteadb.dim](for color blindness: deuteranomaly/protanomaly/tritanomaly)[/]")
        console.print("  27. Always-on display  [byteadb.dim](show clock/notifications on lock screen)[/]")
        console.print("  [bold bright_green]── Developer ──[/]")
        console.print("  28. Open developer settings             29. Screen stay-on mode")
        console.print("   0. Back")
        choice = ask_choice("[Display]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                _print_dict_table(display.get_display_settings(device))
            elif choice == "2":
                preset = ask("Preset (720p/1080p/2k/4k) or blank for custom WxH")
                if preset in display.RESOLUTION_PRESETS:
                    w, h = display.RESOLUTION_PRESETS[preset]
                else:
                    w = int(ask("Width")); h = int(ask("Height"))
                if ask_yn("Landscape (swap width/height)?", default=False):
                    w, h = h, w
                display.set_resolution(device, w, h)
                ok(f"Resolution set to {w}x{h}.")
            elif choice == "3":
                display.reset_resolution(device)
                ok("Resolution reset.")
            elif choice == "4":
                preset = ask(f"Preset ({'/'.join(display.DENSITY_PRESETS)}) or blank for custom DPI")
                dpi = display.DENSITY_PRESETS.get(preset) or int(ask("DPI"))
                display.set_density(device, dpi)
                ok(f"Density set to {dpi}.")
            elif choice == "5":
                display.reset_density(device)
                ok("Density reset.")
            elif choice == "6":
                display.set_scaling(device, ask_yn("Enable auto scaling?", default=True))
                ok("Done.")
            elif choice == "7":
                display.set_brightness(device, int(ask("Brightness (0-255)", default="128")))
                ok("Done.")
            elif choice == "8":
                display.set_screen_timeout(device, int(ask("Timeout in milliseconds", default="30000")))
                ok("Done.")
            elif choice == "9":
                stream = ask("Stream (music/ring/alarm/notification/call/system)", default="music")
                level = int(ask("Level"))
                display.set_volume(device, stream, level)
                ok("Done.")
            elif choice == "10":
                mode = ask("Mode (off/priority/none/alarms)", default="off")
                display.set_dnd(device, mode)
                ok("Done.")
            elif choice == "11":
                display.expand_notifications(device)
                ok("Done.")
            elif choice == "12":
                display.collapse_notifications(device)
                ok("Done.")
            elif choice == "13":
                display.expand_quick_settings(device)
                ok("Done.")
            elif choice == "14":
                display.clipboard_set(device, ask("Text to set (best-effort, varies by OEM)"))
                ok("Attempted.")
            elif choice == "15":
                display.clipboard_clear(device)
                ok("Attempted.")
            elif choice == "16":
                display.set_wallpaper(device, ask("Local image path"))
                ok("Wallpaper chooser opened on device.")
            elif choice == "17":
                console.print("[byteadb.dim]Detecting audio output devices...[/]")
                info = display.get_audio_devices(device)
                outputs = info['outputs']
                table = new_table("#", "Output Device")
                for i, d in enumerate(outputs, 1):
                    table.add_row(str(i), d['label'])
                console.print(table)
                pick = ask("Select output device (0 = cancel)", default="0")
                if pick != "0":
                    try:
                        idx = int(pick) - 1
                        if 0 <= idx < len(outputs):
                            result = display.set_audio_output(device, outputs[idx]['type'])
                            ok(result)
                        else:
                            warn("Invalid number.")
                    except ValueError:
                        warn("Invalid input.")
            elif choice == "18":
                console.print("[byteadb.dim]Detecting audio input devices...[/]")
                info = display.get_audio_devices(device)
                inputs = info['inputs']
                table = new_table("#", "Input Device (Microphone)")
                for i, d in enumerate(inputs, 1):
                    table.add_row(str(i), d['label'])
                console.print(table)
                pick = ask("Select input device (0 = cancel)", default="0")
                if pick != "0":
                    try:
                        idx = int(pick) - 1
                        if 0 <= idx < len(inputs):
                            result = display.set_audio_input(device, inputs[idx]['type'])
                            ok(result)
                        else:
                            warn("Invalid number.")
                    except ValueError:
                        warn("Invalid input.")
            elif choice == "19":
                result = display.reset_audio_routing(device)
                ok(result)
            elif choice == "20":
                console.print(f"  Current font scale: {display.get_font_scale(device)}")
                console.print(f"  [byteadb.dim]Presets: {', '.join(f'{k}={v}' for k, v in display.FONT_SCALES.items())}[/]")
                preset = ask("Preset (small/default/large/largest) or custom scale (e.g. 1.2)")
                if preset in display.FONT_SCALES:
                    ok(display.set_font_scale(device, display.FONT_SCALES[preset]))
                else:
                    ok(display.set_font_scale(device, float(preset)))
            elif choice == "21":
                current = display.get_animation_scales(device)
                console.print(f"  Current: window={current['window']}  transition={current['transition']}  animator={current['animator']}")
                console.print(f"  [byteadb.dim]Presets: {', '.join(f'{k}={v}x' for k, v in display.ANIMATION_PRESETS.items())}[/]")
                preset = ask("Preset (off/fast/normal/slow/very_slow) or custom multiplier")
                if preset in display.ANIMATION_PRESETS:
                    ok(display.set_all_animation_scales(device, display.ANIMATION_PRESETS[preset]))
                else:
                    ok(display.set_all_animation_scales(device, float(preset)))
            elif choice == "22":
                enable = ask_yn("Enable force-RTL layout?", default=False)
                ok(display.set_rtl(device, enable))
            elif choice == "23":
                mode = ask("Dark mode (yes/no/auto)", default="yes")
                ok(display.set_dark_mode(device, mode))
            elif choice == "24":
                console.print("  [byteadb.dim]Modes: nav (hide navigation bar), status (hide status bar), "
                              "full (hide both), off (show all)[/]")
                mode = ask("Immersive mode", default="full")
                ok(display.set_immersive(device, mode))
            elif choice == "25":
                enable = ask_yn("Enable color inversion?", default=False)
                ok(display.set_color_inversion(device, enable))
            elif choice == "26":
                enable = ask_yn("Enable color correction?", default=False)
                if enable:
                    console.print("  0. Deuteranomaly (red-green)  1. Protanomaly  2. Tritanomaly (blue-yellow)")
                    mode = int(ask("Mode", default="0"))
                else:
                    mode = 0
                ok(display.set_color_correction(device, enable, mode))
            elif choice == "27":
                enable = ask_yn("Enable always-on display?", default=True)
                ok(display.set_always_on_display(device, enable))
            elif choice == "28":
                display.open_developer_settings(device)
                ok("Opened.")
            elif choice == "29":
                mode = ask("Mode (off/usb/always)", default="off")
                display.stay_awake(device, mode)
                ok("Done.")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 17. Location & App Usage
# --------------------------------------------------------------------------

def handle_location_usage(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Location & App Usage", device, "yellow")
        console.print("  1. Last-known GPS location  [byteadb.dim](most recent cached GPS fix)[/]")
        console.print("  2. App usage stats — today  [byteadb.dim](screen time per app)[/]")
        console.print("  3. App usage stats — this week")
        console.print("  4. App usage stats — all time")
        console.print("  0. Back")
        choice = ask_choice("[Location/Usage]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                loc = location.last_known_location(device)
                if loc:
                    _print_dict_table(loc)
                else:
                    warn("No last-known location available.")
            elif choice in ("2", "3", "4"):
                period = {"2": "day", "3": "week", "4": "all"}[choice]
                stats = usage.app_usage_stats(device, period)
                for s in stats[:30]:
                    console.print(f"  {s['package']}  [byteadb.dim]{s['total_time_ms'] / 60000:.1f} min[/]")
                if not stats:
                    warn("No usage stats found (or not readable from this shell).")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 18. Radios & Battery Mock
# --------------------------------------------------------------------------

def handle_radios(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Radios & Battery Mock", device, "blue")
        console.print("  1. Mobile data on/off     2. Bluetooth on/off     3. NFC on/off")
        console.print("  4. Airplane mode on/off   8. Connect to a Bluetooth device (by MAC)")
        console.print("  5. Mock battery level     6. Mock plugged state   7. Reset battery mock")
        console.print("  9. Scan & connect to a nearby Bluetooth device")
        console.print("  0. Back")
        choice = ask_choice("[Radios]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                radios.mobile_data(device, ask_yn("Enable mobile data?", default=True))
                ok("Done.")
            elif choice == "2":
                radios.bluetooth_radio(device, ask_yn("Enable Bluetooth?", default=True))
                ok("Done.")
            elif choice == "3":
                radios.nfc_radio(device, ask_yn("Enable NFC?", default=True))
                ok("Done.")
            elif choice == "4":
                radios.airplane_mode(device, ask_yn("Enable airplane mode?", default=False))
                ok("Done.")
            elif choice == "5":
                radios.mock_battery_level(device, int(ask("Level (0-100)", default="50")))
                ok("Done.")
            elif choice == "6":
                radios.mock_battery_plugged(device, ask_yn("Plugged in?", default=True))
                ok("Done.")
            elif choice == "7":
                radios.reset_battery_mock(device)
                ok("Reset.")
            elif choice == "8":
                mac = ask("Bluetooth MAC address (e.g. AA:BB:CC:DD:EE:FF)")
                result = radios.bluetooth_connect(device, mac)
                ok(result)
            elif choice == "9":
                console.print("[byteadb.dim]Scanning for nearby Bluetooth devices (5s)...[/]")
                devs = radios.bluetooth_scan_nearby(device)
                if not devs:
                    warn("No Bluetooth devices found. Make sure Bluetooth is on and "
                         "the target device is discoverable.")
                else:
                    table = new_table("#", "Name", "MAC Address", "Signal")
                    for i, d in enumerate(devs, 1):
                        rssi = d['rssi']
                        if rssi >= -50:
                            sig = "Strong"
                        elif rssi >= -70:
                            sig = "Medium"
                        elif rssi > -100:
                            sig = "Weak"
                        else:
                            sig = "—"
                        sig_str = f"{sig} ({rssi}dBm)" if rssi > -100 else sig
                        table.add_row(str(i), d['name'], d['address'], sig_str)
                    console.print(table)
                    pick = ask("Enter number to connect (0 = cancel)", default="0")
                    if pick != "0":
                        try:
                            idx = int(pick) - 1
                            if 0 <= idx < len(devs):
                                chosen = devs[idx]
                                console.print(f"[byteadb.dim]Connecting to {chosen['name']} "
                                              f"({chosen['address']})...[/]")
                                result = radios.bluetooth_connect(device, chosen['address'])
                                ok(result)
                            else:
                                warn("Invalid number.")
                        except ValueError:
                            warn("Invalid input.")
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 19. Security & Lock Screen
# --------------------------------------------------------------------------

def handle_security(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Security & Lock Screen", device, "red")
        console.print("  [bold bright_green]── Root Detection ──[/]")
        console.print("  1. Root heuristics  [byteadb.dim](check for su, Magisk, test-keys, ro.secure)[/]")
        console.print("  [bold bright_green]── Certificates & Keystore ──[/]")
        console.print("  2. List CA certificates  [byteadb.dim](system + user-added root CAs)[/]")
        console.print("  3. Keystore info  [byteadb.dim](Android keystore status)[/]")
        console.print("  [bold bright_green]── USB Debugging ──[/]")
        console.print("  4. Revoke USB debug authorizations  [byteadb.dim](remove trusted PC fingerprints)[/]")
        console.print("  [bold bright_green]── Lock Screen ──[/]")
        console.print("  5. Set lock PIN  [byteadb.dim](set a numeric PIN on the lock screen)[/]")
        console.print("  6. Set lock password  [byteadb.dim](set an alphanumeric password)[/]")
        console.print("  7. Clear lock  [byteadb.dim](remove PIN/password, needs current one if set)[/]")
        console.print("  0. Back")
        choice = ask_choice("[Security]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                findings = security.root_heuristics(device)
                table = new_table("Check", "Result")
                table.add_row("Likely rooted", str(findings['likely_rooted']))
                table.add_row("su binaries found", ', '.join(findings['su_binary_paths_found']) or "none")
                table.add_row("Root-management apps found", ', '.join(findings['root_management_apps_found']) or "none")
                table.add_row("su on PATH", findings['su_on_path'] or "no")
                table.add_row("ro.secure", findings['ro_secure'] or "—")
                table.add_row("ro.debuggable", findings['ro_debuggable'] or "—")
                table.add_row("Build tags", findings['build_tags'] or "—")
                console.print(table)
            elif choice == "2":
                console.print(security.list_certificates(device))
            elif choice == "3":
                console.print(security.keystore_list(device))
            elif choice == "4":
                ok(security.revoke_usb_auth(device))
            elif choice == "5":
                pin = ask("New PIN (4+ digits)")
                ok(security.set_lock_pin(device, pin))
            elif choice == "6":
                pw = ask("New password")
                ok(security.set_lock_password(device, pw))
            elif choice == "7":
                old = ask("Current PIN/password (blank if none set)")
                ok(security.clear_lock(device, old))
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 20. Communication (Call / Contacts / Calendar)
# --------------------------------------------------------------------------

def handle_communication(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("Communication", device, "yellow")
        console.print("  [bold bright_green]── Phone Calls ──[/]")
        console.print("  1. Make a call  [byteadb.dim](dial a number directly, no dialer UI needed)[/]")
        console.print("  2. End current call  [byteadb.dim](hang up the active call)[/]")
        console.print("  3. Open dialer  [byteadb.dim](open dialer with number pre-filled, doesn't auto-dial)[/]")
        console.print("  [bold bright_green]── Contacts ──[/]")
        console.print("  4. List contacts  [byteadb.dim](read contacts from device)[/]")
        console.print("  5. Contact details  [byteadb.dim](phone numbers & emails for one contact)[/]")
        console.print("  6. Add contact  [byteadb.dim](opens contact creation form on device)[/]")
        console.print("  7. Delete contact  [byteadb.dim](remove a contact by ID)[/]")
        console.print("  [bold bright_green]── Call Log ──[/]")
        console.print("  8. Recent call log  [byteadb.dim](incoming/outgoing/missed calls history)[/]")
        console.print("  [bold bright_green]── Calendar ──[/]")
        console.print("  9. Calendar events  [byteadb.dim](list upcoming events from device calendar)[/]")
        console.print(" 10. Add calendar event  [byteadb.dim](opens calendar creation form)[/]")
        console.print("  [bold bright_green]── Notifications ──[/]")
        console.print(" 11. Active notifications  [byteadb.dim](currently showing in notification shade)[/]")
        console.print("  0. Back")
        choice = ask_choice("[Communication]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                number = ask("Phone number")
                ok(communication.make_call(device, number))
            elif choice == "2":
                ok(communication.end_call(device))
            elif choice == "3":
                number = ask("Phone number (blank = open empty dialer)", default="")
                ok(communication.open_dialer(device, number))
            elif choice == "4":
                contacts = communication.list_contacts(device, full=True)
                if not contacts:
                    warn("No contacts found (or not readable from this shell).")
                else:
                    table = new_table("#", "Name", "Phone(s)", "Email(s)", "ID")
                    for i, c in enumerate(contacts, 1):
                        phones = ', '.join(c.get('phones', [])) or '—'
                        em = ', '.join(c.get('emails', [])) or '—'
                        table.add_row(str(i), c['name'], phones, em, c.get('id', '—'))
                    console.print(table)
                    console.print(f"\n[byteadb.dim]{len(contacts)} contact(s).[/]")
            elif choice == "5":
                cid = ask("Contact ID (from contact list)")
                details = communication.contact_details(device, cid)
                if not details:
                    warn("No details found for this contact.")
                else:
                    table = new_table("Type", "Value")
                    for d in details:
                        table.add_row(d['type'], d['value'])
                    console.print(table)
            elif choice == "6":
                name = ask("Contact name")
                phone = ask("Phone number (blank = skip)", default="")
                email = ask("Email (blank = skip)", default="")
                ok(communication.add_contact(device, name, phone, email))
            elif choice == "7":
                cid = ask("Contact ID to delete")
                if ask_yn(f"Really delete contact #{cid}?"):
                    ok(communication.delete_contact(device, cid))
                else:
                    warn("Cancelled.")
            elif choice == "8":
                limit = int(ask("Number of recent calls to show", default="30"))
                calls = communication.call_log(device, limit)
                if not calls:
                    warn("No call log entries found.")
                else:
                    table = new_table("#", "Number", "Type", "Date", "Duration")
                    for i, c in enumerate(calls, 1):
                        table.add_row(str(i),
                                      c.get('number', '—'),
                                      c.get('type_name', '—'),
                                      c.get('date_str', c.get('date', '—')),
                                      f"{c.get('duration', '—')}s")
                    console.print(table)
            elif choice == "9":
                limit = int(ask("Number of events to show", default="20"))
                events = communication.calendar_events(device, limit)
                if not events:
                    warn("No calendar events found.")
                else:
                    table = new_table("#", "Title", "Start", "Location")
                    for i, e in enumerate(events, 1):
                        table.add_row(str(i),
                                      e.get('title', '—'),
                                      e.get('start_str', e.get('dtstart', '—')),
                                      e.get('eventLocation', '—'))
                    console.print(table)
            elif choice == "10":
                title = ask("Event title")
                ok(communication.add_calendar_event(device, title))
            elif choice == "11":
                notifs = communication.active_notifications(device)
                if not notifs:
                    warn("No active notifications.")
                else:
                    table = new_table("#", "Package", "Title", "Text")
                    for i, n in enumerate(notifs, 1):
                        table.add_row(str(i), n.get('package', '—'),
                                      n.get('title', '—'), n.get('text', '—')[:60])
                    console.print(table)
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# 21. System & Debug
# --------------------------------------------------------------------------

def handle_system_debug(device: AdbDevice | None) -> AdbDevice | None:
    device = ensure_device(device)
    if not device:
        pause()
        return device
    while True:
        clear_screen()
        panel("System & Debug", device, "red")
        console.print("  [bold bright_green]── Processes ──[/]")
        console.print("   1. List running processes  [byteadb.dim](user, PID, CPU%, MEM%, name)[/]")
        console.print("   2. Kill process by PID  [byteadb.dim](send SIGKILL to a process)[/]")
        console.print("   3. Kill by name  [byteadb.dim](force-stop + pkill by package/process name)[/]")
        console.print("  [bold bright_green]── Services ──[/]")
        console.print("   4. List system services  [byteadb.dim](all registered Android services)[/]")
        console.print("   5. Service info  [byteadb.dim](dumpsys output for a specific service)[/]")
        console.print("  [bold bright_green]── Debug & Crash ──[/]")
        console.print("   6. Full bug report  [byteadb.dim](capture comprehensive bugreport .zip — takes 1+ min)[/]")
        console.print("   7. ANR traces  [byteadb.dim](Application Not Responding logs)[/]")
        console.print("   8. Crash dumps  [byteadb.dim](recent crash events from dropbox)[/]")
        console.print("  [bold bright_green]── Performance ──[/]")
        console.print("   9. CPU info  [byteadb.dim](top processes + /proc/cpuinfo)[/]")
        console.print("  10. Memory info  [byteadb.dim](RAM usage summary)[/]")
        console.print("  11. Storage info  [byteadb.dim](disk usage per partition)[/]")
        console.print("  12. App memory usage  [byteadb.dim](RAM used by a specific app)[/]")
        console.print("  [bold bright_green]── System Status ──[/]")
        console.print("  13. Thermal status  [byteadb.dim](CPU/GPU temperature and throttling)[/]")
        console.print("  14. SELinux status  [byteadb.dim](enforcing/permissive mode)[/]")
        console.print("  15. Set SELinux  [byteadb.dim](change enforcing mode — needs root)[/]")
        console.print("  [bold bright_green]── System Properties ──[/]")
        console.print("  16. List properties  [byteadb.dim](getprop — all or filtered by keyword)[/]")
        console.print("  17. Set property  [byteadb.dim](setprop — many are read-only without root)[/]")
        console.print("  [bold bright_green]── Network Stats ──[/]")
        console.print("  18. Network stats  [byteadb.dim](traffic per app UID)[/]")
        console.print("  19. TCP connections  [byteadb.dim](active TCP sockets on device)[/]")
        console.print("   0. Back")
        choice = ask_choice("[System]")
        if choice == "0":
            return device
        try:
            if choice == "1":
                procs = system.list_processes(device)
                if not procs:
                    warn("No process info available.")
                else:
                    table = new_table("PID", "User", "CPU%", "MEM%", "Name")
                    for p in procs[:50]:
                        table.add_row(p['pid'], p['user'], p['cpu'], p['mem'], p['name'][:60])
                    console.print(table)
                    console.print(f"\n[byteadb.dim]{len(procs)} total processes (showing top 50).[/]")
            elif choice == "2":
                pid = ask("PID to kill")
                ok(system.kill_process(device, pid))
            elif choice == "3":
                name = ask("Process/package name")
                ok(system.kill_by_name(device, name))
            elif choice == "4":
                services = system.list_services(device)
                _print_list(services)
            elif choice == "5":
                svc = ask("Service name (from service list)")
                console.print(system.service_info(device, svc))
            elif choice == "6":
                local = ask("Save bugreport as", default="bugreport.zip")
                console.print("[byteadb.dim]Generating bug report (this can take a minute+)...[/]")
                ok(system.bugreport(device, local))
            elif choice == "7":
                console.print(system.anr_traces(device))
            elif choice == "8":
                console.print(system.crash_dumps(device))
            elif choice == "9":
                info = system.cpu_info(device)
                console.print("[bold]Top processes:[/]")
                console.print(info['top'])
                console.print("\n[bold]CPU info:[/]")
                console.print(info['cpuinfo'])
            elif choice == "10":
                info = system.memory_info(device)
                console.print("[bold]/proc/meminfo:[/]")
                console.print(info['meminfo'])
                console.print("\n[bold]dumpsys meminfo:[/]")
                console.print(info['dumpsys'])
            elif choice == "11":
                console.print(system.storage_info(device))
            elif choice == "12":
                pkg = ask("Package name")
                console.print(system.app_memory_usage(device, pkg))
            elif choice == "13":
                console.print(system.thermal_status(device))
            elif choice == "14":
                console.print(f"  SELinux mode: {system.selinux_status(device)}")
            elif choice == "15":
                enforcing = ask_yn("Set to enforcing? (no = permissive)", default=True)
                ok(system.set_selinux(device, enforcing))
            elif choice == "16":
                filt = ask("Filter keyword (blank = show all)")
                props = system.list_properties(device, filt)
                if not props:
                    warn("No properties found.")
                else:
                    table = new_table("Key", "Value")
                    for k, v in props[:100]:
                        table.add_row(k, v[:80])
                    console.print(table)
                    console.print(f"\n[byteadb.dim]{len(props)} property(ies) (showing up to 100).[/]")
            elif choice == "17":
                key = ask("Property key (e.g. persist.sys.timezone)")
                value = ask("Value")
                ok(system.set_property(device, key, value))
            elif choice == "18":
                uid = ask("App UID (blank = summary for all)", default="")
                console.print(system.network_stats_per_app(device, uid))
            elif choice == "19":
                console.print(system.tcp_connections(device))
            else:
                warn("Invalid option.")
        except Exception as e:
            error(str(e))
        pause()


# --------------------------------------------------------------------------
# main loop
# --------------------------------------------------------------------------

def run_menu():
    try:
        adb.adb_binary()
    except AdbNotFoundError as e:
        error(str(e))
        import sys
        sys.exit(1)

    device: AdbDevice | None = None
    handlers = {
        "1": handle_device_connection,
        "3": handle_mirror,
        "4": handle_screen,
        "5": handle_audio,
        "6": handle_files,
        "7": handle_apps,
        "8": handle_shell,
        "9": handle_logcat,
        "10": handle_input,
        "11": handle_settings,
        "12": handle_power,
        "13": handle_info,
        "14": handle_media,
        "15": handle_network,
        "16": handle_display,
        "17": handle_location_usage,
        "18": handle_radios,
        "19": handle_security,
        "20": handle_communication,
        "21": handle_system_debug,
    }
    while True:
        show_banner_and_status(device)
        print_main_menu()
        choice = ask_choice("[Main Menu]")
        if choice == "0":
            console.print("\n[byteadb.dim]Goodbye.[/]\n")
            return
        if choice == "99":
            continue
        if choice == "2":
            handle_wireless()
        elif choice in handlers:
            device = handlers[choice](device)
        else:
            warn("Unknown option.")
            pause()
