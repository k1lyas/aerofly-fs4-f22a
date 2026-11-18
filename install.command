#!/bin/bash
# macOS / Linux: double click (macOS: the first time right click > Open) or run in a terminal
cd "$(dirname "$0")"
# macOS has python3 as part of Apple's command line developer tools: without them the first call opens the system
# window that installs them (one click, a few minutes)
if python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
    python3 install.py "$@"
else
    echo "Python 3 is not ready on this computer yet."
    echo "macOS: if a window offered to install the \"command line developer tools\", click Install, wait until it"
    echo "       is done, then open install.command again. No window? Run  xcode-select --install  in Terminal."
    echo "Or install Python 3 from https://www.python.org/downloads/"
fi
echo
read -r -p "Press Enter to close" _
