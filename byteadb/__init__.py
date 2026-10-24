"""
ByteADB — a professional, all-in-one ADB control toolkit.

V1 is CLI/TUI only (no web panel — that's planned for V2, kept as a
separate product on purpose). Everything here is a thin, well-tested layer
over the real `adb` binary: ByteADB never re-implements the protocol,
it orchestrates it.
"""
__version__ = '1.0.0'
__author__ = 'AliXByte'
