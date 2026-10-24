#!/usr/bin/env python3
"""
ByteADB — run this file directly.

    pip install -r requirements.txt
    python3 byteadb.py

No venv, no build step, no install required: this just needs the
`byteadb/` package next to it (which it is, in this repo) and the three
packages in requirements.txt.
"""
import sys
import os

# Make sure the `byteadb` package next to this file is importable even if
# this script is invoked from another directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from byteadb.cli.main import main

if __name__ == '__main__':
    main()
