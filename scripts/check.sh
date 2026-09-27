#!/usr/bin/env bash
set -euo pipefail
python -m compileall -q main.py src tests
python -m pytest
python main.py --doctor
