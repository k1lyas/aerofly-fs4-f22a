#!/bin/bash
# macOS / Linux: double click (macOS: the first time right click > Open) or run in a terminal
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is needed. macOS: run 'xcode-select --install' or get it from https://www.python.org/downloads/"
else
    python3 install.py "$@"
fi
echo
read -r -p "Press Enter to close" _
