#!/usr/bin/env bash
# ==============================================================================
# shrtnotes - 1-Click Studio Launcher (Linux / macOS)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install flask markdown pyyaml
fi

echo "Launching shrtnotes Studio..."
./venv/bin/python app.py
