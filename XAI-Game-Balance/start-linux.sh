#!/usr/bin/env bash
# Start the i-Game Game Balance Tool (Linux): ./start-linux.sh
cd "$(dirname "$0")" || exit 1

find_python() {
    for c in python3 python; do
        if command -v "$c" >/dev/null 2>&1 &&
           "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
            echo "$c"; return 0
        fi
    done
    return 1
}

if [ ! -f ".venv/installed.ok" ]; then
    echo
    echo "First start: setting up the tool. This takes a few minutes and needs an internet connection."
    echo
    PY="$(find_python)" || {
        echo "Python 3.10 or newer was not found. Install it from https://www.python.org/downloads/"
        echo "(Linux: install python3 and python3-venv with your package manager), then start again."
        exit 1
    }
    "$PY" preflight.py || { exit 1; }
    rm -rf .venv
    if ! "$PY" -m venv .venv; then
        echo "Could not create the Python environment."
        echo "On Debian/Ubuntu, install it with: sudo apt install python3-venv"
        rm -rf .venv
        exit 1
    fi
    .venv/bin/python -m pip install --upgrade pip &&
    .venv/bin/python -m pip install -r requirements.txt || {
        echo
        echo "Setup failed. Check your internet connection and the messages above, then try again."
        rm -rf .venv
        exit 1
    }
    echo ok > .venv/installed.ok
    echo
    echo "Setup complete."
fi

.venv/bin/python launcher.py
