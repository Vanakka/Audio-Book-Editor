#!/usr/bin/env bash
# Idempotent setup for a Linux / headless development environment.
#
# Installs the system libraries PySide6 (Qt) needs, FFmpeg for the chapter
# tools, Xvfb for running the GUI or the Qt tests headlessly, then creates a
# Python 3.12 virtual environment and installs the locked dependencies.
#
# Safe to re-run: apt install and pip install both converge without side effects.
set -euo pipefail

APT_PACKAGES=(
  python3.12-venv
  # Qt / PySide6 runtime libraries
  libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1
  libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
  libfontconfig1 libxrender1 libnss3
  # Chapter tools + headless display for GUI/tests
  ffmpeg xvfb
)

echo "==> Installing system packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${APT_PACKAGES[@]}"

echo "==> Creating Python 3.12 virtual environment (.venv)"
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip

echo "==> Installing locked Python dependencies"
.venv/bin/python -m pip install -r requirements-lock.txt

echo "==> Done. Activate with: source .venv/bin/activate"
