#!/bin/bash
# AI Stock Report - Mac/Linux Launcher

cd "$(dirname "$0")"

# Check Python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "============================================"
    echo "  Python not found!"
    echo "  Please install Python 3.10+"
    echo "  https://www.python.org/downloads/"
    echo "============================================"
    exit 1
fi

echo "Using: $($PY --version)"

# Install dependencies on first run
if [ ! -f .deps_installed ]; then
    echo "[1/2] Installing dependencies..."
    $PY -m pip install -r requirements.txt -q
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please check your network."
        exit 1
    fi
    touch .deps_installed
    echo "[1/2] Done."
fi

# Launch
echo "[2/2] Starting..."
echo ""
$PY app.py "$@"
