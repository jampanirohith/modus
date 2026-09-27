#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Environment installed. Ensure ffmpeg and ffprobe are installed and available on PATH."
echo "Run: python main.py --doctor"
