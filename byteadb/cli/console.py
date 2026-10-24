"""
ByteADB · shared console/output helpers

Centralizes the "premium CLI" look: one Rich console, one error style, one
table style, reused by every subcommand so the whole tool feels like one
coherent product instead of a pile of separate scripts.
"""
from rich.console import Console
from rich.table import Table
from rich.theme import Theme
from rich.panel import Panel

THEME = Theme({
    'byteadb.brand': 'bold bright_cyan',
    'byteadb.ok': 'bold green',
    'byteadb.warn': 'bold yellow',
    'byteadb.err': 'bold red',
    'byteadb.dim': 'grey62',
    'byteadb.key': 'bright_cyan',
})

console = Console(theme=THEME)
err_console = Console(theme=THEME, stderr=True)


def banner():
    console.print(
        Panel.fit(
            "[byteadb.brand]ByteADB[/] [byteadb.dim]— full-control ADB toolkit · by AliXByte[/]",
            border_style="bright_cyan",
        )
    )


def ok(message: str):
    console.print(f"[byteadb.ok]✓[/] {message}")


def warn(message: str):
    console.print(f"[byteadb.warn]![/] {message}")


def error(message: str):
    err_console.print(f"[byteadb.err]✗ {message}[/]")


def new_table(*columns: str, title: str = None) -> Table:
    table = Table(title=title, header_style="bold bright_cyan", border_style="grey42")
    for col in columns:
        table.add_column(col)
    return table
