import click

from byteadb.core import wireless as wireless_core
from byteadb.core import adb
from byteadb.cli.console import console, ok, error
from byteadb.cli.resolve import resolve_device


@click.group('wireless')
def wireless_group():
    """Connect to a device over Wi-Fi, two ways."""


@wireless_group.command('pair')
@click.argument('pairing_host_port')
@click.argument('pairing_code')
@click.argument('connect_host_port')
def wireless_pair(pairing_host_port, pairing_code, connect_host_port):
    """Android 11+ pairing flow.

    On the phone: Settings > Developer options > Wireless debugging >
    Pair device with pairing code. It shows an IP:PORT and a 6-digit code
    (that's PAIRING_HOST_PORT and PAIRING_CODE) and, on the main Wireless
    debugging screen, a second IP:PORT to connect to (CONNECT_HOST_PORT).
    """
    try:
        result = wireless_core.pair_and_connect(pairing_host_port, pairing_code, connect_host_port)
        ok(result)
    except RuntimeError as e:
        error(str(e))


@wireless_group.command('connect')
@click.argument('host_port')
def wireless_connect(host_port):
    """Connect to a device already listening on Wi-Fi (ip:port)."""
    result = adb.connect(host_port)
    if 'connected' in result.lower():
        ok(result)
    else:
        error(result)


@wireless_group.command('disconnect')
@click.argument('host_port', required=False, default=None)
def wireless_disconnect(host_port):
    """Disconnect one wireless device, or all of them if none is given."""
    result = adb.disconnect(host_port)
    console.print(result)


@wireless_group.command('enable-tcpip')
@click.option('--port', default=5555)
@click.option('--serial', '-s', default=None, help='Must be a USB-connected device.')
def wireless_enable_tcpip(port, serial):
    """Switch a USB-connected device into Wi-Fi listening mode, print its IP:port to connect to next."""
    device = resolve_device(serial)
    ip = wireless_core.device_wifi_ip(device)
    wireless_core.enable_tcpip_mode(device, port)
    if ip:
        ok(f"adbd listening on Wi-Fi. Now run: byteadb wireless connect {ip}:{port}")
    else:
        ok(f"adbd listening on port {port}. Couldn't detect the phone's Wi-Fi IP automatically — "
           f"check Settings > About phone > Status, then run `byteadb wireless connect <ip>:{port}`.")
