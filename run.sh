#!/usr/bin/env bash
# ByteADB — Linux/macOS launcher: sets up a venv, installs deps, runs the TUI.
set -e
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -e .
byteadb "$@"
