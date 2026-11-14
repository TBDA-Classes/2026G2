#!/bin/bash
# =====================================================================================================
#  CeDInt Energy Dashboard (Sprint 4, Task 3) — one-click launcher for macOS / Linux
#
#  Double-click this file (first time: right-click > Open), or run it from any terminal:
#       bash <app folder>/Start_dashboard.command
#  It works without any setup:
#    1. uses the folder that contains the app folder (repository clone or minimal package)
#    2. creates the Python environment .venv if it is missing (Python 3.11+ required)
#    3. installs the packages the first time (and whenever requirements change)
#    4. starts the dashboard and opens http://127.0.0.1:8050 in the browser
#  Close the Terminal window (or press Ctrl+C) to stop the dashboard.
# =====================================================================================================
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$APP_DIR")"
cd "$REPO" || exit 1
URL="http://127.0.0.1:8050"
echo "CeDInt Energy Dashboard — folder: $REPO"

# already running? just open the browser
if curl -s -o /dev/null "$URL"; then
  echo "The dashboard is already running: opening the browser."
  open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null
  exit 0
fi

# 1. Python environment
if [ ! -f ".venv/bin/activate" ]; then
  PY=""
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
      PY="$c"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Python 3.11 or newer is needed: install it from https://www.python.org/downloads/ and run this again."
    read -n 1 -s -r -p "Press any key to close."; exit 1
  fi
  echo "Creating the Python environment (.venv) with $PY ..."
  "$PY" -m venv .venv || { read -n 1 -s -r -p "Could not create .venv. Press any key."; exit 1; }
fi
source .venv/bin/activate

# 2. packages (installed once; reinstalled only if the requirements file changes)
REQ="$APP_DIR/requirements-live.txt"
STAMP=".venv/.cedint_requirements"
if [ ! -f "$STAMP" ] || ! cmp -s "$REQ" "$STAMP"; then
  echo "Installing the packages (first time only, a few minutes) ..."
  python -m pip install --upgrade pip >/dev/null
  if python -m pip install -r "$REQ"; then cp "$REQ" "$STAMP"
  else
    echo "Full install failed; installing the basic packages (dashboard without the live forecast) ..."
    python -m pip install -r "$APP_DIR/requirements.txt" || python -m pip install dash dash-bootstrap-components plotly pandas pyarrow
  fi
fi

# 3. open the browser as soon as the dashboard answers
( for i in $(seq 1 60); do sleep 1; if curl -s -o /dev/null "$URL"; then open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null; break; fi; done ) &

# 4. start
echo "Starting the dashboard ... (close this window or press Ctrl+C to stop it)"
python "$APP_DIR/app.py"
