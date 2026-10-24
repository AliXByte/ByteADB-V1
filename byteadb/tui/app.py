"""
ByteADB · interactive dashboard (Textual)

This is the "no web page, pure terminal" flagship UI: a full-screen,
keyboard- and mouse-driven dashboard over everything core/ exposes.
Launched with `byteadb` (no subcommand) or `byteadb tui`.

Layout: a device picker while nothing is selected, then a tabbed
dashboard — Overview, Files, Apps, Logcat, Shell, Control — once a
device is chosen. Every tab is read-only until you act on it; nothing
destructive runs without an explicit key press or button click.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Static, DataTable, Input, Log, Button, TabbedContent, TabPane, ListView, ListItem, Label,
)
from textual.worker import Worker, WorkerState
from textual import work

from byteadb.core import adb, files as files_core, apps as apps_core, logcat as logcat_core, control as control_core
from byteadb.core.adb import AdbDevice, AdbError

CSS = """
Screen {
    background: $surface;
}
#brand {
    color: cyan;
    text-style: bold;
    padding: 1 2;
}
#device-list {
    height: auto;
    border: round cyan;
    margin: 1 2;
}
.panel {
    border: round grey;
    padding: 1 2;
    margin: 0 1 1 1;
}
#overview-info {
    height: auto;
}
#path-bar {
    margin-bottom: 1;
}
#shell-output {
    height: 1fr;
    border: round grey;
}
#shell-input {
    dock: bottom;
}
Button {
    margin-right: 1;
}
DataTable {
    height: 1fr;
}
"""


class DevicePicker(Vertical):
    """Shown until the user selects a device. Lets them refresh the list
    (useful right after plugging something in or finishing a wireless
    pairing) without restarting the whole app."""

    def compose(self) -> ComposeResult:
        yield Static("No device selected — pick one below (press R to refresh):", id="brand")
        yield ListView(id="device-list")

    def on_mount(self):
        self.refresh_devices()

    def refresh_devices(self):
        list_view = self.query_one("#device-list", ListView)
        list_view.clear()
        try:
            devices = adb.list_devices()
        except Exception as e:  # adb missing, etc.
            list_view.append(ListItem(Label(f"[red]{e}[/red]")))
            return
        if not devices:
            list_view.append(ListItem(Label("[dim]No devices found. Connect one via USB or wireless.[/dim]")))
            return
        for d in devices:
            style = "green" if d.state == "device" else "yellow"
            label = f"[{style}]{d.serial}[/{style}]  {d.model or ''}  ({d.state}, {d.transport})"
            item = ListItem(Label(label))
            item.device_serial = d.serial
            item.device_state = d.state
            list_view.append(item)


class OverviewTab(VerticalScroll):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device

    def compose(self) -> ComposeResult:
        yield Static("Loading device info...", id="overview-info", classes="panel")
        with Horizontal(classes="panel"):
            yield Button("Screenshot", id="btn-screenshot")
            yield Button("Reboot", id="btn-reboot", variant="warning")
            yield Button("Refresh", id="btn-refresh-info")

    def on_mount(self):
        self.load_info()

    @work(thread=True)
    def load_info(self):
        try:
            info = self.device.info()
            text = "\n".join(f"[cyan]{k}:[/cyan] {v}" for k, v in info.items() if v is not None)
        except AdbError as e:
            text = f"[red]{e}[/red]"
        self.app.call_from_thread(self._set_info, text)

    def _set_info(self, text: str):
        self.query_one("#overview-info", Static).update(text or "(no info)")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-refresh-info":
            self.load_info()
        elif event.button.id == "btn-screenshot":
            self.take_screenshot()
        elif event.button.id == "btn-reboot":
            self.device.reboot()
            self.app.notify("Rebooting device...")

    @work(thread=True)
    def take_screenshot(self):
        import time
        path = f"byteadb_screenshot_{int(time.time())}.png"
        try:
            from byteadb.core import screen as screen_core
            screen_core.screenshot(self.device, path)
            self.app.call_from_thread(self.app.notify, f"Saved {path}")
        except AdbError as e:
            self.app.call_from_thread(self.app.notify, str(e), severity="error")


class FilesTab(Vertical):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device
        self.current_path = "/sdcard"

    def compose(self) -> ComposeResult:
        yield Input(value=self.current_path, id="path-bar")
        yield DataTable(id="files-table")

    def on_mount(self):
        table = self.query_one("#files-table", DataTable)
        table.add_columns("Name", "Type", "Size", "Permissions")
        self.load_dir(self.current_path)

    @work(thread=True)
    def load_dir(self, path: str):
        try:
            entries = files_core.list_dir(self.device, path)
            self.app.call_from_thread(self._fill_table, path, entries)
        except (PermissionError, FileNotFoundError) as e:
            self.app.call_from_thread(self.app.notify, str(e), severity="error")

    def _fill_table(self, path: str, entries):
        self.current_path = path
        table = self.query_one("#files-table", DataTable)
        table.clear()
        for e in entries:
            kind = "dir" if e.is_dir else ("link" if e.is_link else "file")
            table.add_row(e.name + ("/" if e.is_dir else ""), kind, files_core.human_size(e.size), e.permissions,
                          key=e.path)

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "path-bar":
            self.load_dir(event.value.strip() or "/sdcard")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        row_key = event.row_key.value
        if row_key:
            table = self.query_one("#files-table", DataTable)
            row = table.get_row(event.row_key)
            if row[1] == "dir":
                self.load_dir(row_key)
                self.query_one("#path-bar", Input).value = row_key


class AppsTab(Vertical):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panel"):
            yield Button("User apps", id="btn-user-apps")
            yield Button("All apps", id="btn-all-apps")
            yield Button("Force-stop selected", id="btn-force-stop", variant="warning")
            yield Button("Clear data (selected)", id="btn-clear-data", variant="error")
        yield DataTable(id="apps-table")

    def on_mount(self):
        table = self.query_one("#apps-table", DataTable)
        table.add_columns("Package")
        table.cursor_type = "row"
        self.load_apps(user_only=True)

    @work(thread=True)
    def load_apps(self, user_only: bool):
        pkgs = apps_core.list_packages(self.device, user_only=user_only)
        self.app.call_from_thread(self._fill, pkgs)

    def _fill(self, pkgs):
        table = self.query_one("#apps-table", DataTable)
        table.clear()
        for p in pkgs:
            table.add_row(p, key=p)

    def _selected_package(self) -> str | None:
        table = self.query_one("#apps-table", DataTable)
        if table.cursor_row is None:
            return None
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return row_key.value

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-user-apps":
            self.load_apps(user_only=True)
        elif event.button.id == "btn-all-apps":
            self.load_apps(user_only=False)
        elif event.button.id == "btn-force-stop":
            pkg = self._selected_package()
            if pkg:
                apps_core.force_stop(self.device, pkg)
                self.app.notify(f"Force-stopped {pkg}")
        elif event.button.id == "btn-clear-data":
            pkg = self._selected_package()
            if pkg and apps_core.clear_data(self.device, pkg):
                self.app.notify(f"Cleared data for {pkg}")


class LogcatTab(Vertical):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device
        self._stop = False

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panel"):
            yield Button("Start", id="btn-logcat-start")
            yield Button("Stop", id="btn-logcat-stop")
            yield Button("Clear", id="btn-logcat-clear")
        yield Log(id="logcat-log", auto_scroll=True)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-logcat-start":
            self._stop = False
            self.stream_logs()
        elif event.button.id == "btn-logcat-stop":
            self._stop = True
        elif event.button.id == "btn-logcat-clear":
            logcat_core.clear(self.device.serial)
            self.query_one("#logcat-log", Log).clear()

    @work(thread=True)
    def stream_logs(self):
        log_widget = self.query_one("#logcat-log", Log)
        try:
            for line in logcat_core.stream(self.device.serial):
                if self._stop:
                    break
                self.app.call_from_thread(log_widget.write_line, line)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, str(e), severity="error")


class ShellTab(Vertical):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device

    def compose(self) -> ComposeResult:
        yield Log(id="shell-output")
        yield Input(placeholder="type a shell command and press enter...", id="shell-input")

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id != "shell-input":
            return
        command = event.value
        event.input.value = ""
        log = self.query_one("#shell-output", Log)
        log.write_line(f"$ {command}")
        self.run_command(command)

    @work(thread=True)
    def run_command(self, command: str):
        log = self.query_one("#shell-output", Log)
        try:
            out = self.device.shell(command, timeout=20)
            for line in out.splitlines() or ['(no output)']:
                self.app.call_from_thread(log.write_line, line)
        except AdbError as e:
            self.app.call_from_thread(log.write_line, f"[error] {e}")


class DeviceDashboard(Vertical):
    def __init__(self, device: AdbDevice):
        super().__init__()
        self.device = device

    def compose(self) -> ComposeResult:
        yield Static(f" ByteADB — connected to {self.device.serial}", id="brand")
        with TabbedContent():
            with TabPane("Overview", id="tab-overview"):
                yield OverviewTab(self.device)
            with TabPane("Files", id="tab-files"):
                yield FilesTab(self.device)
            with TabPane("Apps", id="tab-apps"):
                yield AppsTab(self.device)
            with TabPane("Logcat", id="tab-logcat"):
                yield LogcatTab(self.device)
            with TabPane("Shell", id="tab-shell"):
                yield ShellTab(self.device)


class ByteADBApp(App):
    CSS = CSS
    TITLE = "ByteADB"
    SUB_TITLE = "full-control ADB toolkit · by AliXByte"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_devices", "Refresh devices"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DevicePicker(id="picker")
        yield Footer()

    def action_refresh_devices(self):
        picker = self.query(DevicePicker)
        if picker:
            picker.first().refresh_devices()

    def on_list_view_selected(self, event):
        item = event.item
        serial = getattr(item, "device_serial", None)
        state = getattr(item, "device_state", None)
        if not serial:
            return
        if state != "device":
            self.notify(f"{serial} is '{state}', not ready yet.", severity="warning")
            return
        self.query_one("#picker").remove()
        self.mount(DeviceDashboard(AdbDevice(serial)))


def run_tui():
    ByteADBApp().run()


if __name__ == "__main__":
    run_tui()
