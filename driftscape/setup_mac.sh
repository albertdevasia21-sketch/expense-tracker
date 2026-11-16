#!/usr/bin/env bash
# One-time setup on macOS (Apple silicon). Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v brew >/dev/null; then
  echo "Install Homebrew first: https://brew.sh" && exit 1
fi
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12
PY="$(brew --prefix)/bin/python3.12"
[[ -d .venv ]] || "$PY" -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt
for arg in "$@"; do
  if [[ "$arg" == "--with-upload" ]]; then .venv/bin/pip install -r requirements-upload.txt; fi
  if [[ "$arg" == "--with-browser" ]]; then .venv/bin/pip install -r requirements-browser.txt; fi
done
./ds doctor
