"""
ByteADB · device settings — `adb shell settings {get,put,list,delete}`
"""
from __future__ import annotations

from byteadb.core.adb import AdbDevice

NAMESPACES = ('system', 'secure', 'global')


def _check_ns(namespace: str):
    if namespace not in NAMESPACES:
        raise ValueError(f"namespace must be one of {NAMESPACES}, got '{namespace}'")


def get(device: AdbDevice, namespace: str, key: str) -> str:
    _check_ns(namespace)
    return device.shell(f'settings get {namespace} {key}').strip()


def put(device: AdbDevice, namespace: str, key: str, value: str):
    _check_ns(namespace)
    device.shell(f"settings put {namespace} {key} '{value}'")


def delete(device: AdbDevice, namespace: str, key: str):
    _check_ns(namespace)
    device.shell(f'settings delete {namespace} {key}')


def list_all(device: AdbDevice, namespace: str) -> dict:
    _check_ns(namespace)
    out = device.shell(f'settings list {namespace}', timeout=15)
    result = {}
    for line in out.splitlines():
        if '=' in line:
            k, _, v = line.partition('=')
            result[k.strip()] = v.strip()
    return result
