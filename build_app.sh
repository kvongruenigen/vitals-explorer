#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
# This script wraps a Python application into a standalone executable using PyInstaller.
# Version info is only used for Windows builds.
# Usage: ./build_app.sh
python -m PyInstaller --noconfirm --onedir --windowed --clean \
    --icon "res/app-icon.ico" \
    --name "VitalsExplorer" \
    --add-data "res/app-icon.ico:res" \
    --add-data "res/app-icon.png:res" \
    --hidden-import sip \
    --hidden-import pytz \
    --hidden-import tzlocal \
    --hidden-import pandas \
    --hidden-import plotly \
    --hidden-import PyQt5.sip \
    --additional-hooks-dir=. \
    main.py
