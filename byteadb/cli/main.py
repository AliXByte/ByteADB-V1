import click

from byteadb import __version__
from byteadb.cli.console import banner
from byteadb.cli.devices_cmd import devices_group
from byteadb.cli.files_cmd import files_group
from byteadb.cli.apps_cmd import apps_group
from byteadb.cli.shell_cmd import shell_cmd
from byteadb.cli.logcat_cmd import logcat_group
from byteadb.cli.screen_cmd import screen_group
from byteadb.cli.control_cmd import control_group
from byteadb.cli.settings_cmd import settings_group
from byteadb.cli.wireless_cmd import wireless_group


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name='ByteADB')
@click.pass_context
def cli(ctx):
    """ByteADB — full-control ADB toolkit (devices, files, apps, shell,
    logcat, screen, control, settings, wireless), by AliXByte.

    Run with no command to launch the interactive dashboard (TUI)."""
    if ctx.invoked_subcommand is None:
        from byteadb.tui.app import run_tui
        run_tui()


@cli.command('tui')
def tui_cmd():
    """Launch the full-screen interactive dashboard."""
    from byteadb.tui.app import run_tui
    run_tui()


cli.add_command(devices_group)
cli.add_command(files_group)
cli.add_command(apps_group)
cli.add_command(shell_cmd)
cli.add_command(logcat_group)
cli.add_command(screen_group)
cli.add_command(control_group)
cli.add_command(settings_group)
cli.add_command(wireless_group)


def main():
    banner()
    cli()


if __name__ == '__main__':
    main()
